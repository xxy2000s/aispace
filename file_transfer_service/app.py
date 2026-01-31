from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
import os
import json
import uuid
from werkzeug.utils import secure_filename
import zipfile
import shutil
from datetime import datetime
import threading
import time
import argparse
import socket

def find_free_port(start_port=8080, max_attempts=100):
    """寻找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result != 0:  # 端口可用
                return port
        except:
            continue
    return None

def get_config():
    """获取配置信息"""
    config = {
        'port': 8080,
        'host': '0.0.0.0'
    }
    
    # 检查环境变量
    if 'PORT' in os.environ:
        try:
            config['port'] = int(os.environ['PORT'])
        except ValueError:
            pass
    
    # 检查命令行参数
    parser = argparse.ArgumentParser(description='文件传输服务')
    parser.add_argument('--port', '-p', type=int, help='服务端口')
    parser.add_argument('--host', type=str, help='监听地址')
    args = parser.parse_args()
    
    if args.port:
        config['port'] = args.port
    if args.host:
        config['host'] = args.host
        
    return config

# 获取配置
config = get_config()

# 检查端口是否可用
free_port = find_free_port(config['port'])
if free_port != config['port']:
    print(f"⚠️  端口 {config['port']} 已被占用，使用端口 {free_port}")
    config['port'] = free_port

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB limit
app.config['SERVER_PORT'] = config['port']
app.config['SERVER_HOST'] = config['host']

# 创建必要的目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('temp', exist_ok=True)

# 存储上传进度
upload_progress = {}

class FileManager:
    @staticmethod
    def get_file_tree(search_query=None, sort_by='name', sort_order='asc'):
        """获取文件夹树结构，支持搜索和排序"""
        def build_tree(path, root_path):
            tree = []
            try:
                items = os.listdir(path)
                
                # 应用搜索过滤（忽略大小写）
                if search_query:
                    search_lower = search_query.lower()
                    items = [item for item in items if search_lower in item.lower()]
                
                for item in items:
                    item_path = os.path.join(path, item)
                    relative_path = os.path.relpath(item_path, root_path)
                    
                    if os.path.isdir(item_path):
                        children = build_tree(item_path, root_path)
                        tree.append({
                            'name': item,
                            'path': relative_path,
                            'type': 'folder',
                            'children': children,
                            'size': FileManager.get_folder_size(item_path),
                            'collapsed': False  # 默认展开
                        })
                    else:
                        tree.append({
                            'name': item,
                            'path': relative_path,
                            'type': 'file',
                            'size': os.path.getsize(item_path)
                        })
            except PermissionError:
                pass
            
            # 应用排序
            if sort_by == 'name':
                tree.sort(key=lambda x: x['name'].lower(), reverse=(sort_order == 'desc'))
            elif sort_by == 'size':
                tree.sort(key=lambda x: x.get('size', 0), reverse=(sort_order == 'desc'))
            elif sort_by == 'type':
                # 文件夹优先，然后按名称排序
                tree.sort(key=lambda x: (x['type'] != 'folder', x['name'].lower()), 
                         reverse=(sort_order == 'desc'))
            
            return tree
        
        return build_tree(app.config['UPLOAD_FOLDER'], app.config['UPLOAD_FOLDER'])
    
    @staticmethod
    def get_folder_size(folder_path):
        """计算文件夹大小"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass
        return total_size

    @staticmethod
    def flatten_file_tree(tree, parent_path=''):
        """将树形结构扁平化，便于搜索"""
        flat_list = []
        for item in tree:
            current_path = os.path.join(parent_path, item['name']) if parent_path else item['name']
            flat_list.append({
                'name': item['name'],
                'path': item['path'],
                'type': item['type'],
                'size': item.get('size', 0),
                'full_path': current_path
            })
            
            if item['type'] == 'folder' and 'children' in item:
                flat_list.extend(FileManager.flatten_file_tree(item['children'], current_path))
        
        return flat_list

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/files')
def get_files():
    """获取文件列表API，支持搜索和排序"""
    try:
        # 获取查询参数
        search_query = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'name')  # name, size, type
        sort_order = request.args.get('order', 'asc')  # asc, desc
        
        file_tree = FileManager.get_file_tree(search_query, sort_by, sort_order)
        return jsonify({
            'success': True,
            'data': file_tree,
            'search': search_query,
            'sort': sort_by,
            'order': sort_order
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """文件上传API"""
    try:
        upload_id = str(uuid.uuid4())
        upload_progress[upload_id] = {
            'progress': 0,
            'status': 'starting',
            'filename': '',
            'total_size': 0,
            'uploaded_size': 0
        }
        
        # 处理单个文件或多文件上传
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有文件被上传'}), 400
            
        files = request.files.getlist('file')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        # 处理文件夹上传
        if 'folder_structure' in request.form:
            folder_data = json.loads(request.form['folder_structure'])
            return handle_folder_upload(files, folder_data, upload_id)
        else:
            return handle_file_upload(files, upload_id)
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def handle_file_upload(files, upload_id):
    """处理普通文件上传"""
    try:
        saved_files = []
        total_files = len(files)
        
        for i, file in enumerate(files):
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # 如果文件已存在，添加时间戳
                if os.path.exists(filepath):
                    name, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{name}_{timestamp}{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                file.save(filepath)
                saved_files.append({
                    'name': filename,
                    'path': filename,
                    'size': os.path.getsize(filepath)
                })
                
                # 更新进度
                upload_progress[upload_id]['progress'] = int(((i + 1) / total_files) * 100)
                upload_progress[upload_id]['status'] = f'已上传 {i + 1}/{total_files} 个文件'
        
        upload_progress[upload_id]['status'] = '完成'
        upload_progress[upload_id]['progress'] = 100
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'files': saved_files
        })
        
    except Exception as e:
        upload_progress[upload_id]['status'] = f'错误: {str(e)}'
        return jsonify({'success': False, 'error': str(e)}), 500

def handle_folder_upload(files, folder_data, upload_id):
    """处理文件夹上传 - 彻底修复路径嵌套问题"""
    try:
        # 创建临时工作目录
        work_dir = os.path.join('temp', f'work_{upload_id}')
        os.makedirs(work_dir, exist_ok=True)
        
        # 确定根文件夹名称（从上传数据或第一个文件推断）
        if folder_data and 'name' in folder_data and folder_data['name']:
            root_folder_name = folder_data['name']
        else:
            # 从第一个文件路径推断根文件夹名
            sample_path = files[0].filename
            if '/' in sample_path:
                root_folder_name = sample_path.split('/')[0]
            else:
                root_folder_name = f'folder_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
        print(f"DEBUG: Root folder name determined as: {root_folder_name}")
        
        # 在工作目录中创建目标根文件夹
        target_root = os.path.join(work_dir, root_folder_name)
        os.makedirs(target_root, exist_ok=True)
        
        # 处理每个文件，正确重建目录结构
        for file in files:
            if file and file.filename:
                original_path = file.filename  # 例如: "exp/a.pdf" 或 "exp/sub/b.pdf"
                print(f"DEBUG: Processing file: {original_path}")
                
                if '/' in original_path:
                    # 分离根文件夹和相对路径
                    parts = original_path.split('/')
                    file_relative_path = '/'.join(parts[1:])  # "a.pdf" 或 "sub/b.pdf"
                else:
                    # 根目录下的文件
                    file_relative_path = original_path
                
                print(f"DEBUG: Relative path: {file_relative_path}")
                
                # 构建完整的目标路径
                if file_relative_path:
                    final_target_path = os.path.join(target_root, file_relative_path)
                else:
                    final_target_path = os.path.join(target_root, original_path)
                
                print(f"DEBUG: Target path: {final_target_path}")
                
                # 创建必要的子目录
                target_dir = os.path.dirname(final_target_path)
                if target_dir and not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                    print(f"DEBUG: Created directory: {target_dir}")
                
                # 保存文件
                file.save(final_target_path)
                print(f"DEBUG: Saved file to: {final_target_path}")
        
        # 确定最终存储位置
        final_destination = os.path.join(app.config['UPLOAD_FOLDER'], root_folder_name)
        
        # 处理重名情况
        counter = 1
        original_destination = final_destination
        while os.path.exists(final_destination):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_destination = f"{original_destination}_{timestamp}"
            counter += 1
        
        print(f"DEBUG: Moving from {target_root} to {final_destination}")
        
        # 移动整个文件夹结构到最终位置
        shutil.move(target_root, final_destination)
        
        upload_progress[upload_id]['status'] = '完成'
        upload_progress[upload_id]['progress'] = 100
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'folder': {
                'name': os.path.basename(final_destination),
                'path': os.path.basename(final_destination),
                'size': FileManager.get_folder_size(final_destination)
            }
        })
        
    except Exception as e:
        upload_progress[upload_id]['status'] = f'错误: {str(e)}'
        # 清理临时文件
        if 'work_dir' in locals() and os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        print(f"ERROR in folder upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/progress/<upload_id>')
def get_upload_progress(upload_id):
    """获取上传进度"""
    if upload_id in upload_progress:
        return jsonify(upload_progress[upload_id])
    return jsonify({'error': '上传ID不存在'}), 404

@app.route('/download/<path:filename>')
def download_file(filename):
    """文件下载"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 如果是文件夹，打包成zip下载
        if os.path.isdir(filepath):
            return download_folder_as_zip(filename)
        else:
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

def download_folder_as_zip(folder_name):
    """将文件夹打包成zip文件下载"""
    try:
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
        if not os.path.exists(folder_path):
            return jsonify({'error': '文件夹不存在'}), 404
            
        # 创建临时zip文件
        zip_filename = f"{folder_name}.zip"
        zip_path = os.path.join('temp', zip_filename)
        
        # 确保temp目录存在
        os.makedirs('temp', exist_ok=True)
        
        # 创建zip文件
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 计算相对路径
                    arcname = os.path.relpath(file_path, app.config['UPLOAD_FOLDER'])
                    zipf.write(file_path, arcname)
        
        # 发送zip文件
        return send_from_directory('temp', zip_filename, as_attachment=True, download_name=zip_filename)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500











@app.route('/auto-redirect')
def auto_redirect():
    """自动跳转页面，用于二维码扫描后的自动跳转"""
    target_url = request.args.get('url', '/')
    if not target_url.startswith(('http://', 'https://', '/', './', '../')):
        # 防止开放重定向攻击，只允许本地路径
        target_url = '/'
    
    # 检查是否是外部URL，如果是则限制为内部路径
    if target_url.startswith(('http://', 'https://')):
        base_url = request.url_root.rstrip('/')
        if not target_url.startswith(base_url):
            target_url = '/'
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>正在跳转...</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="0; url={target_url}">
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                margin: 0;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }}
            .container {{
                max-width: 500px;
                margin: 0 auto;
            }}
            .spinner {{
                width: 50px;
                height: 50px;
                border: 5px solid rgba(255,255,255,0.3);
                border-radius: 50%;
                border-top-color: white;
                animation: spin 1s ease-in-out infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📱 扫码成功</h1>
            <div class="spinner"></div>
            <p>正在跳转到目标页面...</p>
            <p>如果长时间未跳转，请<a href="{target_url}" style="color: #fff; text-decoration: underline;">点击这里</a></p>
        </div>
        <script>
            // JavaScript作为备用跳转方式
            setTimeout(function() {{
                window.location.href = "{target_url}";
            }}, 500); // 0.5秒后跳转
        </script>
    </body>
    </html>
    """

@app.route('/download-page')
def download_page():
    """文件下载页面"""
    filepath = request.args.get('file', '')
    if not filepath:
        return "文件路径未指定", 400
    
    try:
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
        if not os.path.exists(full_path):
            return "文件不存在", 404
            
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(full_path) if os.path.isfile(full_path) else FileManager.get_folder_size(full_path)
        
        # 返回简单的下载页面
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>文件下载 - {filename}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .container {{ max-width: 500px; margin: 0 auto; }}
                .file-info {{ background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .download-btn {{ 
                    background: #4CAF50; color: white; padding: 15px 30px; 
                    text-decoration: none; border-radius: 5px; font-size: 18px;
                    display: inline-block; margin: 10px;
                }}
                .download-btn:hover {{ background: #45a049; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📁 文件下载</h1>
                <div class="file-info">
                    <h2>{filename}</h2>
                    <p>大小: {filesize // 1024} KB</p>
                </div>
                <a href="/download/{filepath}" class="download-btn">⬇️ 点击下载</a>
                <p><small>该页面由二维码扫描访问</small></p>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"错误: {str(e)}", 500

@app.route('/api/generate_qr')
def generate_qr():
    """生成主访问二维码（使用实际IP地址）"""
    try:
        # 获取实际的网络IP地址而不是localhost
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # 也可以尝试获取更准确的局域网IP
        try:
            # 创建一个UDP连接来获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            pass
            
        base_url = f"http://{local_ip}:8080"
        main_url = f"{base_url}/"
        return jsonify({
            'success': True,
            'qr_content': main_url,
            'url': main_url,
            'ip': local_ip
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500





@app.route('/mobile-upload')
def mobile_upload():
    """移动端上传页面"""
    return render_template('mobile_upload.html')


if __name__ == '__main__':
    print(f"🚀 启动文件传输服务...")
    print(f"🌐 访问地址: http://{app.config['SERVER_HOST']}:{app.config['SERVER_PORT']}")
    print(f"📁 上传目录: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
    print(f"⚠️  请注意：此服务仅适用于局域网内可信环境")
    
    app.run(host=app.config['SERVER_HOST'], port=app.config['SERVER_PORT'], debug=True)
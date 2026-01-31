class FileTransferApp {
    constructor() {
        this.currentUploadId = null;
        this.uploadProgressInterval = null;
        this.searchQuery = '';
        this.sortBy = 'name';
        this.sortOrder = 'asc';
        this.init();
        // 页面加载完成后自动生成二维码
        this.generateDefaultQR();
    }

    init() {
        this.setupEventListeners();
        this.setupFileControls();
        this.loadFiles();
    }

    setupFileControls() {
        // 搜索功能
        const searchInput = document.getElementById('searchInput');
        const searchBtn = document.getElementById('searchBtn');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        
        if (searchInput) {
            searchInput.addEventListener('keyup', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch();
                }
            });
        }
        
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.performSearch());
        }
        
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                if (searchInput) {
                    searchInput.value = '';
                    this.searchQuery = '';
                    clearSearchBtn.style.display = 'none';
                    this.loadFiles();
                }
            });
        }
        
        // 排序功能
        const sortBySelect = document.getElementById('sortBy');
        const sortOrderSelect = document.getElementById('sortOrder');
        const refreshBtn = document.getElementById('refreshBtn');
        
        if (sortBySelect) {
            sortBySelect.addEventListener('change', () => {
                this.sortBy = sortBySelect.value;
                this.loadFiles();
            });
        }
        
        if (sortOrderSelect) {
            sortOrderSelect.addEventListener('change', () => {
                this.sortOrder = sortOrderSelect.value;
                this.loadFiles();
            });
        }
        
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadFiles());
        }
    }

    performSearch() {
        const searchInput = document.getElementById('searchInput');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        
        if (searchInput) {
            this.searchQuery = searchInput.value.trim();
            if (this.searchQuery) {
                if (clearSearchBtn) {
                    clearSearchBtn.style.display = 'inline-block';
                }
            } else {
                if (clearSearchBtn) {
                    clearSearchBtn.style.display = 'none';
                }
            }
            this.loadFiles();
        }
    }

    setupEventListeners() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const folderInput = document.getElementById('folderInput');

        // 点击上传区域 - 文件上传
        document.getElementById('fileUploadBtn').addEventListener('click', () => {
            fileInput.click();
        });

        // 点击文件夹上传区域
        document.getElementById('folderUploadBtn').addEventListener('click', () => {
            folderInput.click();
        });

        // 文件选择处理
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files, false);
        });

        folderInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files, true);
        });

        // 拖拽上传
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.unhighlight, false);
        });

        uploadArea.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            // 检测是否是文件夹拖拽
            const isFolder = Array.from(files).some(file => 
                file.webkitRelativePath && file.webkitRelativePath.includes('/')
            );
            this.handleFileSelect(files, isFolder);
        }, false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    highlight(e) {
        document.getElementById('uploadArea').classList.add('dragover');
    }

    unhighlight(e) {
        document.getElementById('uploadArea').classList.remove('dragover');
    }

    async handleFileSelect(files, isFolder = false) {
        if (files.length === 0) return;

        const formData = new FormData();
        
        // 添加文件到FormData
        for (let file of files) {
            formData.append('file', file);
        }

        // 如果是文件夹，添加文件夹结构信息
        if (isFolder) {
            const folderStructure = this.buildFolderStructure(files);
            formData.append('folder_structure', JSON.stringify(folderStructure));
        }

        try {
            this.showProgress();
            this.currentUploadId = this.generateUploadId();
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (result.success) {
                this.updateProgress(100, '上传完成！');
                setTimeout(() => {
                    this.hideProgress();
                    this.loadFiles();
                }, 1000);
            } else {
                this.updateProgress(0, `上传失败: ${result.error}`);
            }
        } catch (error) {
            this.updateProgress(0, `上传出错: ${error.message}`);
        }
    }

    buildFolderStructure(files) {
        const structure = {};
        for (let file of files) {
            if (file.webkitRelativePath) {
                const parts = file.webkitRelativePath.split('/');
                let current = structure;
                for (let i = 0; i < parts.length - 1; i++) {
                    if (!current[parts[i]]) {
                        current[parts[i]] = {};
                    }
                    current = current[parts[i]];
                }
            }
        }
        
        // 获取根文件夹名
        const firstPath = files[0].webkitRelativePath;
        const rootFolder = firstPath.split('/')[0];
        
        return {
            name: rootFolder,
            structure: structure
        };
    }

    generateUploadId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    showProgress() {
        document.getElementById('progressContainer').style.display = 'block';
        document.getElementById('progressFill').style.width = '0%';
        document.getElementById('progressText').textContent = '准备上传...';
    }

    hideProgress() {
        document.getElementById('progressContainer').style.display = 'none';
    }

    updateProgress(percentage, text) {
        document.getElementById('progressFill').style.width = percentage + '%';
        document.getElementById('progressText').textContent = text;
    }

    async loadFiles() {
        try {
            // 构建查询参数
            let url = '/api/files';
            const params = [];
            
            if (this.searchQuery) {
                params.push(`search=${encodeURIComponent(this.searchQuery)}`);
            }
            
            if (this.sortBy && this.sortBy !== 'name') {
                params.push(`sort=${this.sortBy}`);
            }
            
            if (this.sortOrder && this.sortOrder !== 'asc') {
                params.push(`order=${this.sortOrder}`);
            }
            
            if (params.length > 0) {
                url += '?' + params.join('&');
            }
            
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success) {
                this.renderFileTree(result.data);
            } else {
                document.getElementById('fileTree').innerHTML = `<p>加载失败: ${result.error}</p>`;
            }
        } catch (error) {
            document.getElementById('fileTree').innerHTML = `<p>加载出错: ${error.message}</p>`;
        }
    }

    renderFileTree(fileTree) {
        const container = document.getElementById('fileTree');
        
        if (!fileTree || fileTree.length === 0) {
            const message = this.searchQuery ? 
                `<p>未找到包含 "${this.searchQuery}" 的文件</p>` : 
                '<p>暂无文件</p>';
            container.innerHTML = message;
            return;
        }

        let html = '<div class="file-list">';
        fileTree.forEach(item => {
            html += this.renderFileItem(item, 0);
        });
        html += '</div>';
        
        container.innerHTML = html;
        
        // 绑定文件夹点击事件
        this.bindFolderEvents();
    }

    renderFileItem(item, level) {
        const indent = level * 20;
        let html = '';
        
        // 检测文件类型用于图标显示
        const fileType = this.getFileType(item);
        
        if (item.type === 'folder') {
            const collapsedClass = item.collapsed ? 'collapsed' : '';
            html += `
                <div class="file-item folder-item ${collapsedClass}" 
                     data-path="${item.path}" 
                     data-type="folder"
                     style="margin-left: ${indent}px">
                    <span class="folder-name">${item.name}</span>
                    <span class="file-size">(${this.formatSize(item.size)})</span>
                    <div class="file-actions">
                        <button class="download-btn" onclick="event.stopPropagation(); app.downloadFolder('${item.path}')">📦 打包下载</button>
                        <button class="qr-btn" onclick="event.stopPropagation(); app.generateFileQR('${item.path}')">📱 二维码</button>
                    </div>
                </div>
                <div class="folder-contents ${collapsedClass}" id="folder-${this.escapeHtml(item.path)}">`;
            
            if (item.children && !item.collapsed) {
                item.children.forEach(child => {
                    html += this.renderFileItem(child, level + 1);
                });
            }
            
            html += '</div>';
        } else {
            html += `
                <div class="file-item file-item-leaf" 
                     data-path="${item.path}" 
                     data-type="${fileType}"
                     style="margin-left: ${indent}px">
                    <span class="file-name">${item.name}</span>
                    <span class="file-size">(${this.formatSize(item.size)})</span>
                    <div class="file-actions">
                        <button class="download-btn" onclick="app.downloadFile('${item.path}')">⬇️ 下载</button>
                        <button class="qr-btn" onclick="app.generateFileQR('${item.path}')">📱 二维码</button>
                    </div>
                </div>`;
        }
        
        return html;
    }

    getFileType(item) {
        if (item.type === 'folder') return 'folder';
        
        const extension = item.name.toLowerCase().split('.').pop();
        const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'];
        const videoExts = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv'];
        const audioExts = ['mp3', 'wav', 'flac', 'aac', 'ogg'];
        const archiveExts = ['zip', 'rar', '7z', 'tar', 'gz'];
        const documentExts = ['doc', 'docx', 'txt', 'rtf'];
        const pdfExts = ['pdf'];
        
        if (imageExts.includes(extension)) return 'image';
        if (videoExts.includes(extension)) return 'video';
        if (audioExts.includes(extension)) return 'audio';
        if (archiveExts.includes(extension)) return 'archive';
        if (documentExts.includes(extension)) return 'document';
        if (pdfExts.includes(extension)) return 'pdf';
        return 'file';
    }

    bindFolderEvents() {
        // 为所有文件夹绑定点击事件
        const folderItems = document.querySelectorAll('.folder-item');
        folderItems.forEach(folder => {
            folder.addEventListener('click', (e) => {
                if (e.target.closest('.file-actions')) return; // 点击操作按钮时不触发折叠
                
                const folderPath = folder.getAttribute('data-path');
                const contents = document.getElementById(`folder-${this.escapeHtml(folderPath)}`);
                const isCollapsed = folder.classList.contains('collapsed');
                
                if (isCollapsed) {
                    folder.classList.remove('collapsed');
                    if (contents) contents.classList.remove('collapsed');
                } else {
                    folder.classList.add('collapsed');
                    if (contents) contents.classList.add('collapsed');
                }
            });
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML.replace(/[^a-zA-Z0-9]/g, '_');
    }

    formatSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    downloadFile(filepath) {
        window.open(`/download/${filepath}`, '_blank');
    }

    downloadFolder(folderpath) {
        window.open(`/download/${folderpath}`, '_blank');
    }

    async generateQR(filepath) {
        try {
            const response = await fetch(`/api/generate_qr/${filepath}`);
            const result = await response.json();
            
            if (result.success) {
                this.showQRModal(result.qr_content, result.download_url, '文件下载二维码');
            } else {
                alert('生成二维码失败: ' + result.error);
            }
        } catch (error) {
            alert('生成二维码出错: ' + error.message);
        }
    }



    showQRModal(qrContent, downloadUrl, title = '扫一扫下载') {
        const modal = document.getElementById('qrModal');
        const qrContainer = document.getElementById('qrCode');
        const linkElement = document.getElementById('downloadLink');
        const titleElement = modal.querySelector('h3');
        
        // 设置标题
        titleElement.textContent = title;
        
        // 清空之前的内容
        qrContainer.innerHTML = '';
        
        // 生成二维码
        new QRCode(qrContainer, {
            text: qrContent,
            width: 200,
            height: 200
        });
        
        linkElement.innerHTML = `下载链接: <a href="${downloadUrl}" target="_blank">${downloadUrl}</a>`;
        
        modal.style.display = 'block';
    }

    async generateQR() {
        try {
            const response = await fetch('/api/generate_qr');
            const result = await response.json();
            
            if (result.success) {
                this.showMainQRModal(result.qr_content, result.url);
            } else {
                alert('生成二维码失败: ' + result.error);
            }
        } catch (error) {
            alert('生成二维码出错: ' + error.message);
        }
    }
    showMainQRModal(qrContent, url) {
        const modal = document.getElementById('mainQRModal');
        const qrContainer = document.getElementById('mainQRCode');
        const linkElement = document.getElementById('mainQRUrl');
        
        // 清空之前的内容
        qrContainer.innerHTML = '';
        
        // 生成二维码
        new QRCode(qrContainer, {
            text: qrContent,
            width: 200,
            height: 200
        });
        
        linkElement.innerHTML = `访问地址: <a href="${url}" target="_blank">${url}</a>`;
        
        modal.style.display = 'block';
    }

    async generateFileQR(filepath) {
        try {
            // 为文件生成下载链接
            const downloadUrl = `${window.location.origin}/download/${filepath}`;
            this.showQRModal(downloadUrl, downloadUrl, '文件下载二维码');
        } catch (error) {
            alert('生成文件二维码出错: ' + error.message);
        }
    }

    async generateQR() {
        try {
            const response = await fetch('/api/generate_qr');
            const result = await response.json();
            
            if (result.success) {
                this.showMainQRModal(result.qr_content, result.url);
            } else {
                alert('生成二维码失败: ' + result.error);
            }
        } catch (error) {
            alert('生成二维码出错: ' + error.message);
        }
    }

    showMainQRModal(qrContent, url) {
        const modal = document.getElementById('mainQRModal');
        const qrContainer = document.getElementById('mainQRCode');
        const linkElement = document.getElementById('mainQRUrl');
        
        // 清空之前的内容
        qrContainer.innerHTML = '';
        
        // 生成二维码
        new QRCode(qrContainer, {
            text: qrContent,
            width: 200,
            height: 200
        });
        
        linkElement.innerHTML = `访问地址: <a href="${url}" target="_blank">${url}</a>`;
        
        modal.style.display = 'block';
    }
    async generateDefaultQR() {
        try {
            const response = await fetch('/api/generate_qr');
            const result = await response.json();
            
            if (result.success) {
                this.showDefaultQR(result.qr_content, result.url, result.ip);
            } else {
                console.error('生成默认二维码失败:', result.error);
                // 显示错误信息
                const qrContainer = document.getElementById('defaultQRCode');
                if (qrContainer) {
                    qrContainer.innerHTML = '<p style="color: red;">二维码生成失败</p>';
                }
            }
        } catch (error) {
            console.error('生成默认二维码出错:', error);
            // 显示错误信息
            const qrContainer = document.getElementById('defaultQRCode');
            if (qrContainer) {
                qrContainer.innerHTML = '<p style="color: red;">网络错误，请刷新页面重试</p>';
            }
        }
    }

    showDefaultQR(qrContent, url, ip) {
        const qrContainer = document.getElementById('defaultQRCode');
        const linkElement = document.getElementById('defaultQRUrl');
        
        if (qrContainer) {
            // 清空之前的内容
            qrContainer.innerHTML = '';
            
            // 生成二维码
            try {
                new QRCode(qrContainer, {
                    text: qrContent,
                    width: 180,
                    height: 180
                });
            } catch (e) {
                qrContainer.innerHTML = '<p>二维码生成库加载失败</p>';
                console.error('QRCode生成失败:', e);
            }
        }
        
        if (linkElement) {
            linkElement.innerHTML = `访问地址: <strong>${url}</strong><br>本机IP: ${ip}`;
        }
    }
}

// 初始化应用
const app = new FileTransferApp();
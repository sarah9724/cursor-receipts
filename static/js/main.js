// 表单验证
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('input[required]');
    for (const input of inputs) {
        if (!input.value.trim()) {
            alert('请填写所有必填字段');
            return false;
        }
    }
    return true;
}

// 显示消息
function showMessage(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

// 切换登录/注册标签
function switchTab(tab) {
    // 更新按钮状态
    document.getElementById('loginTab').classList.toggle('active', tab === 'login');
    document.getElementById('registerTab').classList.toggle('active', tab === 'register');
    
    // 显示/隐藏表单
    document.getElementById('loginForm').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('registerForm').style.display = tab === 'register' ? 'block' : 'none';
}

// 在modal内显示消息
function showModalMessage(message, type = 'success') {
    // 移除已有的消息
    const existingAlert = document.querySelector('.modal-alert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} modal-alert`;
    alertDiv.textContent = message;
    
    // 获取当前显示的表单
    const currentForm = document.querySelector('.auth-form[style*="block"]');
    if (currentForm) {
        // 在表单标题后插入消息
        const title = currentForm.querySelector('h2');
        title.insertAdjacentElement('afterend', alertDiv);
        
        // 3秒后自动移除
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    }
}

// 处理登录
async function handleLogin(e) {
    e.preventDefault();
    
    const phone = document.getElementById('loginPhone').value;
    const password = document.getElementById('loginPassword').value;
    
    if (!phone || !password) {
        showMessage('请填写手机号和密码', 'danger');
        return;
    }
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ phone, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('登录成功，显示主界面');
            
            // 添加logged-in类到body
            document.body.classList.add('logged-in');
            
            // 隐藏登录/注册表单
            document.getElementById('registerModal').style.display = 'none';
            
            // 显示用户信息
            document.getElementById('userInfoDisplay').style.display = 'block';
            document.getElementById('freeUsesDisplay').textContent = data.free_uses || 0;
            
            // 显示发票处理表单
            const invoiceForm = document.getElementById('invoiceForm');
            invoiceForm.style.display = 'block';
            
            // 确保搜索字段区域可见
            const searchFieldsArea = document.getElementById('searchFieldsArea');
            if (searchFieldsArea) {
                console.log('设置搜索字段区域为可见');
                searchFieldsArea.style.display = 'block';
                searchFieldsArea.style.visibility = 'visible';
                
                // 确保搜索字段可用
                const searchInputs = searchFieldsArea.querySelectorAll('input[name="search_texts[]"]');
                console.log(`找到 ${searchInputs.length} 个搜索输入字段`);
                
                // 如果未找到搜索字段，尝试创建
                if (searchInputs.length === 0) {
                    console.log('未找到搜索字段，尝试修复');
                    
                    // 清空并重建搜索字段区域内容
                    const searchInputsDiv = searchFieldsArea.querySelector('.search-inputs');
                    if (searchInputsDiv) {
                        searchInputsDiv.innerHTML = `
                            <div class="form-group">
                                <label for="searchText1">搜索文本1:</label>
                                <input type="text" id="searchText1" name="search_texts[]" class="form-control search-text-input" placeholder="输入搜索文本1">
                            </div>
                            <div class="form-group">
                                <label for="searchText2">搜索文本2:</label>
                                <input type="text" id="searchText2" name="search_texts[]" class="form-control search-text-input" placeholder="输入搜索文本2">
                            </div>
                            <div class="form-group">
                                <label for="searchText3">搜索文本3:</label>
                                <input type="text" id="searchText3" name="search_texts[]" class="form-control search-text-input" placeholder="输入搜索文本3">
                            </div>
                        `;
                    }
                }
            } else {
                console.error('未找到搜索字段区域，尝试创建');
                
                // 尝试创建搜索字段区域
                const invoiceForm = document.getElementById('invoiceForm');
                if (invoiceForm) {
                    const uploadForm = invoiceForm.querySelector('form');
                    if (uploadForm) {
                        const submitButton = uploadForm.querySelector('button[type="submit"]');
                        
                        // 创建搜索字段区域元素
                        const searchFieldsDiv = document.createElement('div');
                        searchFieldsDiv.id = 'searchFieldsArea';
                        searchFieldsDiv.className = 'search-fields';
                        searchFieldsDiv.style.display = 'block';
                        searchFieldsDiv.style.visibility = 'visible';
                        searchFieldsDiv.innerHTML = `
                            <h4>搜索条件（可选）</h4>
                            <p class="text-secondary">输入公司名称或其他关键词，只处理包含这些文本的发票。</p>
                            <div class="search-inputs">
                                <div class="form-group">
                                    <label for="searchText1">搜索文本1:</label>
                                    <input type="text" id="searchText1" name="search_texts[]" class="form-control search-text-input" placeholder="输入搜索文本1">
                                </div>
                                <div class="form-group">
                                    <label for="searchText2">搜索文本2:</label>
                                    <input type="text" id="searchText2" name="search_texts[]" class="form-control search-text-input" placeholder="输入搜索文本2">
                                </div>
                                <div class="form-group">
                                    <label for="searchText3">搜索文本3:</label>
                                    <input type="text" id="searchText3" name="search_texts[]" class="form-control search-text-input" placeholder="输入搜索文本3">
                                </div>
                            </div>
                        `;
                        
                        // 插入到表单中，提交按钮之前
                        if (submitButton) {
                            uploadForm.insertBefore(searchFieldsDiv, submitButton);
                        } else {
                            uploadForm.appendChild(searchFieldsDiv);
                        }
                    }
                }
            }
            
            // 显示结果区域
            document.getElementById('result').style.display = 'block';
            
            // 隐藏登录提示信息
            document.getElementById('loginRequiredMessage').style.display = 'none';
            
            // 如果定义了showMainContent函数，调用它
            if (typeof showMainContent === 'function') {
                showMainContent();
            }
            
            // 获取用户信息
            getUserInfo();
        } else {
            showMessage(data.message, 'danger');
        }
    } catch (error) {
        showMessage('登录失败: ' + error.message, 'danger');
    }
}

// 处理注册
async function handleRegister(event) {
    event.preventDefault();
    
    const phone = document.getElementById('phone').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const referredBy = document.getElementById('referredBy').value;
    
    if (!phone || !email || !password) {
        alert('请填写必填字段');
        return;
    }
    
    if (password !== confirmPassword) {
        alert('两次密码输入不一致');
        return;
    }
    
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                phone, 
                email,
                password,
                referredBy: referredBy || null
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(data.message);
            // 注册成功后切换到登录页
            switchTab('login');
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('注册失败: ' + error.message);
    }
}

// 获取用户信息
async function getUserInfo() {
    try {
        const response = await fetch('/user_info');
        const data = await response.json();
        
        if (data.success) {
            // 只更新免费次数显示，不检查是否为0
            document.getElementById('freeUsesDisplay').textContent = data.free_uses || 0;
        }
    } catch (error) {
        console.error('获取用户信息失败:', error);
    }
}

// 检查登录状态
async function checkAuth() {
    try {
        const response = await fetch('/check_auth');
        const data = await response.json();
        
        if (data.success) {
            // 已登录
            document.body.classList.add('logged-in');
            document.getElementById('registerModal').style.display = 'none';
            document.getElementById('invoiceForm').style.display = 'block';
            document.getElementById('userInfoDisplay').style.display = 'block';
            document.getElementById('result').style.display = 'block';
            document.getElementById('loginRequiredMessage').style.display = 'none';
            getUserInfo();
        } else {
            // 未登录，显示登录模态窗口
            document.body.classList.remove('logged-in');
            document.getElementById('registerModal').style.display = 'block';
            document.getElementById('invoiceForm').style.display = 'none';
            document.getElementById('userInfoDisplay').style.display = 'none';
            document.getElementById('result').style.display = 'none';
            document.getElementById('loginRequiredMessage').style.display = 'block';
        }
    } catch (error) {
        console.error('检查登录状态失败:', error);
        // 出错时，默认显示登录模态窗口
        document.body.classList.remove('logged-in');
        document.getElementById('registerModal').style.display = 'block';
        document.getElementById('invoiceForm').style.display = 'none';
        document.getElementById('userInfoDisplay').style.display = 'none';
        document.getElementById('result').style.display = 'none';
        document.getElementById('loginRequiredMessage').style.display = 'block';
    }
}

// 显示免费次数用完modal
function showFreeUsageModal() {
    console.log('显示免费次数用完modal');  // 添加调试日志
    const modal = document.getElementById('freeUsageModal');
    if (modal) {
        modal.style.display = 'flex';
        // 强制重绘
        modal.offsetHeight;
        modal.style.opacity = '1';
        // 禁止背景滚动
        document.body.style.overflow = 'hidden';
    } else {
        console.error('找不到免费次数用完modal');  // 添加调试日志
    }
}

// 关闭免费次数用完modal
function closeFreeUsageModal() {
    console.log('关闭免费次数用完modal');  // 添加调试日志
    const modal = document.getElementById('freeUsageModal');
    if (modal) {
        modal.style.opacity = '0';
        setTimeout(() => {
            modal.style.display = 'none';
            // 恢复背景滚动
            document.body.style.overflow = 'auto';
        }, 300);
    }
}

// 显示支付modal
function showPaymentModal() {
    console.log('显示支付modal');
    
    // 先关闭免费次数用完的modal
    closeFreeUsageModal();
    
    // 获取支付modal
    const modal = document.getElementById('paymentModal');
    if (modal) {
        // 确保支付modal中有必要的元素
        if (!document.getElementById('paymentAmount')) {
            // 动态添加支付金额和验证码输入框
            const verifySection = modal.querySelector('.verify-section');
            if (verifySection) {
                const inputsHtml = `
                    <div class="form-group" style="margin-bottom: 15px;">
                        <input type="text" id="paymentAmount" class="form-control" placeholder="输入实际支付金额" style="margin-bottom: 10px;">
                        <input type="text" id="paymentVerifyCode" class="form-control" placeholder="输入支付验证码">
                    </div>
                `;
                verifySection.innerHTML = inputsHtml + verifySection.innerHTML;
            }
        }
        
        // 显示modal
        modal.style.display = 'flex';
        modal.style.opacity = '1';
        
        // 禁止背景滚动
        document.body.style.overflow = 'hidden';
        
        console.log('支付modal显示完成');
    } else {
        console.error('找不到支付modal');
        alert('无法显示支付界面，请刷新页面重试');
    }
}

// 确认支付
async function confirmPayment() {
    console.log('确认支付被点击');
    
    const amount = document.getElementById('paymentAmount')?.value;
    const verifyCode = document.getElementById('paymentVerifyCode')?.value;
    
    if (!amount || !verifyCode) {
        alert('请输入支付金额和验证码');
        return;
    }
    
    try {
        const response = await fetch('/verify_payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                amount,
                verify_code: verifyCode
            })
        });
        
        const data = await response.json();
        console.log('支付验证响应:', data);
        
        if (data.success) {
            alert('支付验证成功!');
            
            // 关闭支付modal
            const modal = document.getElementById('paymentModal');
            if (modal) {
                modal.style.display = 'none';
            }
            
            // 刷新页面以重置状态
            window.location.reload();
        } else {
            alert('支付验证失败: ' + data.message);
        }
    } catch (error) {
        console.error('支付验证出错:', error);
        alert('支付验证出错: ' + error.message);
    }
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，初始化表单');
    
    // 首先隐藏主要内容区域
    document.getElementById('invoiceForm').style.display = 'none';
    document.getElementById('userInfoDisplay').style.display = 'none';
    document.getElementById('result').style.display = 'none';
    document.getElementById('loginRequiredMessage').style.display = 'block';
    
    // 检查登录状态
    checkAuth();
    
    // 移除测试按钮
    const resultDiv = document.getElementById('result');
    if (resultDiv) {
        const testButton = resultDiv.querySelector('button[onclick*="testFreeUsageModal"]');
        if (testButton) {
            testButton.remove();
        }
    }
    
    // 为所有表单添加验证
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this.id)) {
                e.preventDefault();
            }
        });
    });
    
    // 创建隐藏的文件输入元素
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.pdf';
    fileInput.multiple = true;
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    // 文件选择按钮点击事件
    document.getElementById('selectFileBtn').addEventListener('click', function() {
        fileInput.click();
    });

    // 文件选择事件
    fileInput.addEventListener('change', function() {
        const selectedFiles = this.files;
        const selectedFilesDiv = document.querySelector('.selected-files');
        
        if (selectedFiles.length > 0) {
            let fileList = '';
            for (let i = 0; i < selectedFiles.length; i++) {
                fileList += `<div>${selectedFiles[i].name}</div>`;
            }
            selectedFilesDiv.innerHTML = fileList;
        } else {
            selectedFilesDiv.innerHTML = '';
        }
    });

    // 修改表单提交处理
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        console.log('找到上传表单，添加提交处理程序');
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();  // 确保阻止表单默认提交
            console.log('表单提交被触发');
            
            // 检查是否选择了文件
            if (fileInput.files.length === 0) {
                alert('请选择要处理的发票文件');
                return;
            }
            
            // 创建FormData对象
            const formData = new FormData(this);
            
            // 添加选择的文件
            for (let i = 0; i < fileInput.files.length; i++) {
                formData.append('invoices[]', fileInput.files[i]);
                console.log(`添加文件: ${fileInput.files[i].name}`);
            }
            
            // 获取搜索文本输入字段值并显示调试信息
            const searchInputs = document.querySelectorAll('.search-text-input');
            console.log(`找到 ${searchInputs.length} 个搜索字段`);
            
            if (searchInputs.length === 0) {
                // 尝试备用方式获取搜索字段
                const alternativeInputs = document.querySelectorAll('input[name="search_texts[]"]');
                console.log(`备用方法找到 ${alternativeInputs.length} 个搜索字段`);
                
                alternativeInputs.forEach((input, index) => {
                    if (input.value && input.value.trim()) {
                        formData.append('search_texts[]', input.value.trim());
                        console.log(`添加搜索文本 ${index+1}: ${input.value.trim()}`);
                    }
                });
            } else {
                searchInputs.forEach((input, index) => {
                    if (input.value && input.value.trim()) {
                        formData.append('search_texts[]', input.value.trim());
                        console.log(`添加搜索文本 ${index+1}: ${input.value.trim()}`);
                    }
                });
            }
            
            // 显示进度提示
            document.getElementById('progress').style.display = 'flex';
            
            try {
                // 发送请求
                console.log('发送请求到服务器...');
                const response = await fetch('/process_invoice', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                const data = await response.json();
                console.log('收到响应数据:', data);  // 添加调试日志
                
                document.getElementById('progress').style.display = 'none';
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                
                if (data.success) {
                    // 更新剩余免费次数显示
                    if (data.free_uses_remaining !== undefined) {
                        const freeUsesDisplay = document.getElementById('freeUsesDisplay');
                        if (freeUsesDisplay) {
                            freeUsesDisplay.textContent = data.free_uses_remaining;
                        }
                    }
                    
                    // 构建处理成功的文件列表HTML
                    let processedFilesHtml = '';
                    if (data.processed_filenames && data.processed_filenames.length > 0) {
                        processedFilesHtml = `
                            <div class="file-list-section">
                                <h4>成功处理的文件：</h4>
                                <ul class="file-list">
                                    ${data.processed_filenames.map(filename => `<li>${filename}</li>`).join('')}
                                </ul>
                            </div>
                        `;
                    }

                    // 构建重复文件列表HTML
                    let duplicateFilesHtml = '';
                    if (data.duplicate_filenames && data.duplicate_filenames.length > 0) {
                        duplicateFilesHtml = `
                            <div class="file-list-section">
                                <h4>重复的文件：</h4>
                                <ul class="file-list">
                                    ${data.duplicate_filenames.map(filename => `<li>${filename}</li>`).join('')}
                                </ul>
                            </div>
                        `;
                    }

                    resultDiv.innerHTML = `
                        <div class="card result-card">
                            <h3>处理结果</h3>
                            <p class="success-message" style="color: #28a745; font-size: 18px; font-weight: bold; margin: 15px 0; padding: 10px; background-color: #f3fff3; border-left: 4px solid #28a745;">
                                ${data.message || `成功处理了${data.processed_files}个文件，${data.duplicate_files || 0}个重复文件`}
                            </p>
                            <p>总文件数：${data.total_files}</p>
                            <p>成功处理：${data.processed_files}</p>
                            <p>重复文件：${data.duplicate_files || 0}</p>
                            ${data.download_url ? `<p>您的发票信息已经整理完毕，并已生成报告，<a href="#" onclick="downloadExcel('${data.download_url}'); return false;">点击此处下载</a></p>` : ''}
                            ${processedFilesHtml}
                            ${duplicateFilesHtml}
                        </div>
                    `;
                    
                    // 强制滚动到结果区域
                    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } else {
                    // 检查是否是免费次数用完
                    if (data.message && data.message.includes('免费次数已用完')) {
                        console.log('检测到免费次数用完');  // 添加调试日志
                        showFreeUsageModal();
                        return;
                    }
                    
                    resultDiv.innerHTML = `
                        <div class="card result-card">
                            <h3>处理失败</h3>
                            <p class="error-message">${data.message || data.error}</p>
                            ${data.details ? `<div class="error-details">${data.details}</div>` : ''}
                        </div>
                    `;
                }
            } catch (error) {
                console.error('请求错误:', error);  // 添加错误日志
                document.getElementById('progress').style.display = 'none';
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `
                    <div class="card result-card">
                        <h3>处理失败</h3>
                        <p class="error-message">处理过程中发生错误</p>
                        <div class="error-details">${error.message}</div>
                    </div>
                `;
            }
        });
    }

    // 为登录成功添加事件处理
    window.showMainContent = function() {
        if (registerModal) {
            registerModal.style.display = 'none';
        }
        
        document.getElementById('invoiceForm').style.display = 'block';
        document.getElementById('userInfoDisplay').style.display = 'block';
        // 只有在用户登录后才显示结果区域
        document.getElementById('result').style.display = 'block';
        // 隐藏登录提示
        document.getElementById('loginRequiredMessage').style.display = 'none';
    };
});

// 添加Excel文件下载函数
async function downloadExcel(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('下载失败');
        }
        
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = '发票数据.xlsx';  // 设置下载文件名
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);
    } catch (error) {
        console.error('下载Excel文件失败:', error);
        alert('下载Excel文件失败，请稍后重试');
    }
} 
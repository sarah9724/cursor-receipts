from flask import Flask, render_template, request, jsonify, send_file, session
from invoice_process import process_invoice, process_multiple_invoices
import os
import shutil
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 添加secret key用于session

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_invoice', methods=['POST'])
def handle_invoice():
    try:
        # 获取上传的文件
        if 'invoices[]' not in request.files:
            return jsonify({'success': False, 'message': '没有上传文件'})
        
        files = request.files.getlist('invoices[]')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
            
        # 获取搜索文本
        search_texts = request.form.getlist('search_texts[]')
        search_texts = [text.strip() for text in search_texts if text.strip()]
        
        # 处理发票
        result = process_multiple_invoices(files, search_texts)
        
        if result['success']:
            # 将临时文件信息存储在session中
            session['temp_file_info'] = {
                'excel_path': result['excel_path'],
                'temp_dir': result['temp_dir']
            }
            # 删除不需要返回给前端的信息
            del result['excel_path']
            del result['temp_dir']
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '处理请求时发生错误'
        })

@app.route('/download_excel/<filename>')
def download_excel(filename):
    try:
        # 安全检查
        if not filename.startswith('Invoice_Data_') or not filename.endswith('.xlsx'):
            return jsonify({'success': False, 'message': '无效的文件名'})
        
        # 从session中获取文件信息
        file_info = session.get('temp_file_info')
        if not file_info:
            return jsonify({'success': False, 'message': '文件信息已过期'})
        
        excel_path = file_info['excel_path']
        temp_dir = file_info['temp_dir']
        
        if not os.path.exists(excel_path):
            return jsonify({'success': False, 'message': '文件不存在'})
        
        # 发送文件
        try:
            return send_file(
                excel_path,
                as_attachment=True,
                download_name=filename
            )
        finally:
            # 下载完成后清理文件
            try:
                if os.path.exists(excel_path):
                    os.remove(excel_path)
                    logger.info(f"已删除Excel文件: {excel_path}")
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                    logger.info(f"已删除临时目录: {temp_dir}")
                # 清理session
                session.pop('temp_file_info', None)
            except Exception as cleanup_error:
                logger.error(f"清理文件时发生错误: {str(cleanup_error)}")
                
    except Exception as e:
        logger.error(f"下载文件时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '下载文件时发生错误'
        })

if __name__ == '__main__':
    app.run(debug=True) 
from flask import Flask, render_template, request, jsonify, send_file, session
from invoice_process import process_invoice, process_multiple_invoices
import os
import logging
import io

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process_invoice', methods=['POST'])
def handle_invoice():
    try:
        if 'invoices[]' not in request.files:
            return jsonify({'success': False, 'message': '没有上传文件'})
        
        files = request.files.getlist('invoices[]')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
            
        search_texts = request.form.getlist('search_texts[]')
        search_texts = [text.strip() for text in search_texts if text.strip()]
        
        result = process_multiple_invoices(files, search_texts)
        
        if result['success']:
            # 直接返回文件内容
            return send_file(
                io.BytesIO(result['excel_content']),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=result['excel_filename']
            )
        
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
        
        # 从session中获取文件数据
        excel_data = session.get('excel_data')
        if not excel_data:
            return jsonify({'success': False, 'message': '文件信息已过期'})
        
        # 直接从session中获取文件内容
        return send_file(
            io.BytesIO(excel_data['content']),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"下载文件时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '下载文件时发生错误'
        })

if __name__ == '__main__':
    app.run() 
import os
import shutil
import pdfplumber
import openpyxl
from openpyxl import Workbook
from datetime import datetime
import re
import tempfile
from werkzeug.utils import secure_filename
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加文件大小检查
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def extract_invoice_data(pdf):
    """提取PDF中的发票数据"""
    first_page_text = pdf.pages[0].extract_text()
    full_text = ""
    top_right_text = pdf.pages[0].crop((pdf.pages[0].width * 0.5, 0, pdf.pages[0].width, pdf.pages[0].height * 0.2)).extract_text()
    
    for page in pdf.pages:
        full_text += page.extract_text() + "\n"
 
    return first_page_text, full_text, top_right_text

def parse_data(first_page_text, full_text, top_right_text, filename, buyer_name):
    """解析发票数据"""
    # 查找发票代码和发票号码
    invoice_code_search = re.search(r"发票代码\s*[:：]?\s*(\d+)", first_page_text)
    invoice_number_search = re.search(r"发票号码\s*[:：]?\s*(\d+)", first_page_text)

    if not invoice_code_search and not invoice_number_search and top_right_text:
        invoice_code_search_in_top_right = re.search(r"发票代码[:：]\s{0,3}(\d+)", top_right_text)
        invoice_number_search_in_top_right = re.search(r"发票号码[:：]\s{0,3}(\d+)", top_right_text)

        invoice_code = invoice_code_search_in_top_right.group(1) if invoice_code_search_in_top_right else ""
        invoice_number = invoice_number_search_in_top_right.group(1) if invoice_number_search_in_top_right else ""
    else:
        invoice_code = invoice_code_search.group(1) if invoice_code_search else ""
        invoice_number = invoice_number_search.group(1) if invoice_number_search else ""

    # 查找金额
    amounts = re.findall(r"[￥¥]\s{0,3}(\d+(?:\.\d{1,2})?)", first_page_text)
    amounts_float = [float(amount) for amount in amounts]
    total_amount = max(amounts_float) if amounts_float else "未找到金额"

    # 查找日期
    date_search = re.search(r"(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)", first_page_text + top_right_text)
    invoice_date = date_search.group(1) if date_search else "未找到发票日期"

    # 提取项目信息
    items = re.findall(r"\*(.*?)\*", full_text)
    simplified_item_names = ''.join(dict.fromkeys(''.join(re.findall(r'[\u4e00-\u9fa5]', item)) for item in items if item.strip()))

    # 提取购买方和销售方名称
    company_pattern = r"(?:名\s*称\s*[:：]\s*|^)(.+?(?:公司|事务所))"
    companies = re.findall(company_pattern, first_page_text, re.MULTILINE)
    
    if len(companies) >= 2:
        buyer_name = companies[0]
        seller_name = companies[1]
    else:
        buyer_name = buyer_name if buyer_name else "未找到购买方名称"
        seller_name = "未找到销售方名称"

    return {
        "filename": filename,
        "invoice_code": invoice_code,
        "invoice_number": invoice_number,
        "items": simplified_item_names,
        "total_amount": str(total_amount),
        "invoice_date": invoice_date,
        "buyer_name": buyer_name,
        "seller_name": seller_name
    }

def create_excel_report(data, temp_dir):
    """
    创建Excel报告
    
    Args:
        data: 发票数据字典
        temp_dir: 临时目录路径
        
    Returns:
        str: Excel文件路径
    """
    workbook = Workbook()
    sheet = workbook.active
    headers = ["文件名", "发票代码", "发票号码", "项目信息", "价税合计", "发票日期", "购买方名称", "销售方名称"]
    sheet.append(headers)
    
    # 添加数据行
    row_data = [
        data["filename"],
        data["invoice_code"],
        data["invoice_number"],
        data["items"],
        data["total_amount"],
        data["invoice_date"],
        data["buyer_name"],
        data["seller_name"]
    ]
    sheet.append(row_data)

    # 保存到临时目录
    excel_filename = f"Invoice_Data_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    excel_path = os.path.join(temp_dir, excel_filename)
    workbook.save(excel_path)
    return excel_path, excel_filename

def process_invoice(file_storage, search_texts=None):
    """处理从网页上传的发票文件"""
    temp_dir = None
    pdf_path = None
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        # 保存上传的文件
        filename = secure_filename(file_storage.filename)
        pdf_path = os.path.join(temp_dir, filename)
        file_storage.save(pdf_path)
        
        logger.info(f"文件已保存到临时目录: {pdf_path}")
        
        # 处理PDF文件
        with pdfplumber.open(pdf_path) as pdf:
            first_page_text, full_text, top_right_text = extract_invoice_data(pdf)
            
            # 如果提供了搜索文本，检查是否匹配
            if search_texts:
                matching_texts = [text for text in search_texts if text in full_text]
                if not matching_texts:
                    return {
                        'success': False,
                        'message': '未找到匹配的搜索文本'
                    }
                buyer_name = matching_texts[0]
            else:
                buyer_name = ""
            
            # 解析发票数据
            result = parse_data(first_page_text, full_text, top_right_text, filename, buyer_name)
        
        # 生成Excel报告
        excel_path, excel_filename = create_excel_report(result, temp_dir)
        
        # 只删除PDF文件，保留Excel文件
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return {
            'success': True,
            'data': result,
            'excel_filename': excel_filename,
            'excel_path': excel_path,
            'temp_dir': temp_dir,  # 添加临时目录路径
            'message': '发票处理成功'
        }
        
    except Exception as e:
        logger.error(f"处理发票时发生错误: {str(e)}")
        # 清理文件
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
            if temp_dir and os.path.exists(temp_dir):
                # 尝试删除目录中的所有文件
                for file in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)
        except Exception as cleanup_error:
            logger.error(f"清理文件时发生错误: {str(cleanup_error)}")
            
        return {
            'success': False,
            'error': str(e),
            'message': '发票处理失败'
        }

def process_multiple_invoices(files, search_texts=None):
    """处理多个发票文件"""
    temp_dir = None
    processed_invoices = set()  # 用于存储已处理的发票代码和号码组合
    results = []
    duplicate_count = 0
    
    try:
        # 确保使用/tmp目录
        temp_dir = '/tmp'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        for file in files:
            if len(file.read()) > MAX_FILE_SIZE:
                return {
                    'success': False,
                    'message': f'文件 {file.filename} 超过大小限制'
                }
            file.seek(0)  # 重置文件指针
            try:
                # 使用原始文件名
                original_filename = file.filename
                # 为了避免文件系统路径问题，仅在保存时使用secure_filename
                safe_filename = secure_filename(original_filename)
                pdf_path = os.path.join(temp_dir, safe_filename)
                file.save(pdf_path)
                
                logger.info(f"处理文件: {original_filename}")
                
                # 处理PDF文件
                with pdfplumber.open(pdf_path) as pdf:
                    first_page_text, full_text, top_right_text = extract_invoice_data(pdf)
                    
                    # 如果提供了搜索文本，检查是否匹配
                    if search_texts:
                        matching_texts = [text for text in search_texts if text in full_text]
                        if not matching_texts:
                            continue  # 跳过不匹配的文件
                        buyer_name = matching_texts[0]
                    else:
                        buyer_name = ""
                    
                    # 解析发票数据，传入原始文件名
                    result = parse_data(first_page_text, full_text, top_right_text, original_filename, buyer_name)
                    
                    # 检查是否为重复发票
                    invoice_key = (result['invoice_code'], result['invoice_number'])
                    if invoice_key in processed_invoices:
                        duplicate_count += 1
                        logger.info(f"发现重复发票: {original_filename}")
                        continue
                    
                    processed_invoices.add(invoice_key)
                    results.append(result)
                
                # 删除处理完的PDF文件
                os.remove(pdf_path)
                
            except Exception as e:
                logger.error(f"处理文件 {original_filename} 时发生错误: {str(e)}")
                continue
        
        if not results:
            return {
                'success': False,
                'message': '没有找到有效的发票数据'
            }
        
        # 生成Excel报告
        excel_path, excel_filename = create_excel_report(results, temp_dir)
        
        # 读取Excel文件内容
        with open(excel_path, 'rb') as f:
            excel_content = f.read()
        
        return {
            'success': True,
            'total_processed': len(results),
            'duplicate_count': duplicate_count,
            'excel_filename': excel_filename,
            'excel_content': excel_content,  # 直接返回文件内容
            'message': '发票处理成功'
        }
        
    except Exception as e:
        logger.error(f"批量处理发票时发生错误: {str(e)}")
        # 清理文件
        try:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as cleanup_error:
            logger.error(f"清理文件时发生错误: {str(cleanup_error)}")
            
        return {
            'success': False,
            'error': str(e),
            'message': '批量处理发票失败'
        }
    finally:
        # 确保清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"清理临时文件失败: {str(e)}")

def create_excel_report(data_list, temp_dir):
    """创建包含多个发票数据的Excel报告"""
    workbook = Workbook()
    sheet = workbook.active
    headers = ["文件名", "发票代码", "发票号码", "项目信息", "价税合计", "发票日期", "购买方名称", "销售方名称"]
    sheet.append(headers)
    
    # 添加所有发票数据
    for data in data_list:
        row_data = [
            data["filename"],
            data["invoice_code"],
            data["invoice_number"],
            data["items"],
            data["total_amount"],
            data["invoice_date"],
            data["buyer_name"],
            data["seller_name"]
        ]
        sheet.append(row_data)

    # 保存到临时目录
    excel_filename = f"Invoice_Data_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    excel_path = os.path.join(temp_dir, excel_filename)
    workbook.save(excel_path)
    return excel_path, excel_filename

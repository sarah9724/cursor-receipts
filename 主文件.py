import os
import shutil
import pdfplumber
import openpyxl
from openpyxl import Workbook
import tkinter as tk
from tkinter import filedialog, messagebox, Entry, Label, Frame
from datetime import datetime
import re

# 提取PDF中的发票数据
def extract_invoice_data(pdf):
    first_page_text = pdf.pages[0].extract_text()
    full_text = ""
    top_right_text = pdf.pages[0].crop((pdf.pages[0].width * 0.5, 0, pdf.pages[0].width, pdf.pages[0].height * 0.2)).extract_text()
    
    for page in pdf.pages:
        full_text += page.extract_text() + "\n"
 
    return first_page_text, full_text, top_right_text

# 解析发票数据
def parse_data(first_page_text, full_text, top_right_text, filename, buyer_name):
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
    # 将项目名称列表转换为字符串，避免列表传入Excel，并去除重复项
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

    return filename, invoice_code, invoice_number, simplified_item_names, total_amount, invoice_date, buyer_name, seller_name

# 创建Excel报告
def create_excel_report(data, output_folder):
    workbook = Workbook()
    sheet = workbook.active
    headers = ["文件名", "发票代码", "发票号码", "项目信息", "价税合计", "发票日期", "购买方名称", "销售方名称"]
    sheet.append(headers)

    for entry in data:
        # 确保所有数据是字符串或数值
        entry = [str(item) if isinstance(item, list) else item for item in entry]
        sheet.append(entry)

    excel_filename = f"Invoice_Data_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    workbook.save(os.path.join(output_folder, excel_filename))
    return excel_filename

# 处理PDF发票
def process_invoices(search_texts, folder_path):
    # 创建存放处理后发票的新文件夹
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    new_folder_path = os.path.join(folder_path, f"Processed_Invoices_{timestamp}")
    os.makedirs(new_folder_path, exist_ok=True)

    # 创建存放重复发票的新文件夹
    duplicate_folder_path = os.path.join(new_folder_path, "重复发票")
    os.makedirs(duplicate_folder_path, exist_ok=True)

    extracted_data = []
    file_counter = 1
    processed_invoices = set()  # 用于存储已处理的发票代码和号码组合

    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(folder_path, filename)
            # 使用 pdfplumber 打开PDF文件
            with pdfplumber.open(pdf_path) as pdf:
                first_page_text, full_text, top_right_text = extract_invoice_data(pdf)
                
                if search_texts:
                    # 检查是否有任何搜索文本在发票中
                    matching_texts = [search_text for search_text in search_texts if search_text in full_text]
                    if matching_texts:
                        buyer_name = matching_texts[0]  # 使用第一个匹配的搜索文本作为购买方名称
                    else:
                        continue  # 如果没有匹配的搜索文本，跳过此发票
                else:
                    buyer_name = ""  # 如果��有搜索文本，留空，让parse_data函数处理
                
                result = parse_data(first_page_text, full_text, top_right_text, filename, buyer_name)
                
                # 检查是否为重复发票
                invoice_key = (result[1], result[2])  # 发票代码和发票号码的组合
                if invoice_key in processed_invoices:
                    # 如果是重复发票，复制到重复发票文件夹
                    shutil.copy(pdf_path, os.path.join(duplicate_folder_path, filename))
                else:
                    # 如果不是重复发票，进行正常处理
                    processed_invoices.add(invoice_key)
                    new_filename = f"{file_counter:03d}_{result[6]}_{result[4]}_{result[5]}.pdf"
                    new_filename = re.sub(r'[<>:"/\\|?*]', '_', new_filename)  # 替换非法字符
                    shutil.copy(pdf_path, os.path.join(new_folder_path, new_filename))
                    extracted_data.append((new_filename,) + result[1:])
                    file_counter += 1
    
    # 生成Excel报告
    if extracted_data:
        excel_filename = create_excel_report(extracted_data, new_folder_path)
        message = f"Excel报告已生成：{excel_filename}，位于{new_folder_path}，共包含{len(extracted_data)}条记录。"
        if os.listdir(duplicate_folder_path):
            message += f"\n重复发票已复制到：{duplicate_folder_path}"
    else:
        message = "未找到符合条件的发票。"

    messagebox.showinfo("搜索和处理结果", message)

# 主函数
def main():
    def on_submit():
        search_texts = [entry.get().strip() for entry in entries if entry.get().strip()]
        folder_path = filedialog.askdirectory(title="选择包含发票PDF文件的文件夹")
        if folder_path:
            process_invoices(search_texts, folder_path)

    root = tk.Tk()
    root.title("发票搜索和数据提取工具")
    
    Label(root, text="请输入搜索字符（最多5个，可以留空）:").pack(padx=10, pady=10)
    entries_frame = Frame(root)
    entries = []
    for i in range(5):
        entry = Entry(entries_frame, width=40)
        entry.pack(padx=5, pady=5)
        entries.append(entry)
    entries_frame.pack()
    
    process_button = tk.Button(root, text="选择文件夹并处理", command=on_submit)
    process_button.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
import json

def clean_ocr_text(text):
    """
    Bước 1: Làm sạch rác OCR và các đoạn text lặp lại
    """
    # Xóa đánh dấu trang
    text = re.sub(r'===== PAGE \d+ =====', '', text)
    # Xóa chữ ký điện tử
    text = re.sub(r'Signature Not Verified\nĐược ký bởi.*?\nNgày ký:.*?\n', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Xóa các dòng rác chứa nhiều ký tự vô nghĩa (tùy chỉnh thêm theo thực tế)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if len(line.strip()) < 3 and not line.strip().isalnum():
            continue
        cleaned_lines.append(line)
        
    return '\n'.join(cleaned_lines)

def parse_html_tables(text):
    """
    Bước 2: Tìm và parse HTML tables trong text OCR sang cấu trúc dễ xử lý hơn
    """
    soup = BeautifulSoup(text, 'html.parser')
    tables = soup.find_all('table')
    
    extracted_tables = []
    for table in tables:
        rows = table.find_all('tr')
        table_data = []
        for row in rows:
            cols = row.find_all(['td', 'th'])
            cols = [ele.text.strip() for ele in cols]
            table_data.append(cols)
        extracted_tables.append(table_data)
        
    # TODO: Thay thế bảng HTML gốc bằng Markdown hoặc text đã format
    
    return text, extracted_tables

def normalize_numbers(tables):
    """
    Bước 3: Chuẩn hóa số liệu (Format Normalization)
    Trong BCTC Việt Nam, dấu chấm (.) thường dùng phân cách hàng nghìn, dấu phẩy (,) dùng cho thập phân.
    OCR thường hay nhầm lẫn. Hàm này sẽ cố gắng chuyển đổi về định dạng float chuẩn (1234567.89).
    """
    normalized_tables = []
    for table in tables:
        new_table = []
        for row in table:
            new_row = []
            for cell in row:
                # Nếu cell có dạng số với dấu phân cách hàng nghìn là dấu chấm (VD: 1.234.567)
                # hoặc có dấu phẩy thập phân (VD: 1.234,56)
                if re.match(r'^-?\d{1,3}(?:\.\d{3})*(?:,\d+)?$', cell) or re.match(r'^-?\(\d{1,3}(?:\.\d{3})*(?:,\d+)?\)$', cell):
                    is_negative = cell.startswith('(') or cell.startswith('-')
                    clean_num = cell.replace('(', '').replace(')', '').replace('-', '')
                    
                    # Đổi dấu phẩy thành dấu chấm tạm thời cho phần thập phân
                    if ',' in clean_num:
                        parts = clean_num.split(',')
                        integer_part = parts[0].replace('.', '')
                        decimal_part = parts[1]
                        clean_num = f"{integer_part}.{decimal_part}"
                    else:
                        clean_num = clean_num.replace('.', '')
                        
                    if is_negative:
                        clean_num = "-" + clean_num
                    new_row.append(clean_num)
                else:
                    new_row.append(cell)
            new_table.append(new_row)
        normalized_tables.append(new_table)
    return normalized_tables

def structure_document(text, tables):
    """
    Bước 4: Phân mảnh cấu trúc báo cáo (Document Structuring)
    Tìm các từ khóa tiêu đề để cắt file văn bản thành các phần (Chunks) logic.
    """
    sections = {
        "bang_can_doi": "",
        "ket_qua_kinh_doanh": "",
        "luu_chuyen_tien_te": "",
        "thuyet_minh": "",
        "khac": text
    }
    
    # Tìm index của các tiêu đề phổ biến
    idx_cdkt = text.find("BẢNG CÂN ĐỐI KẾ TOÁN")
    idx_kqkd = text.find("KẾT QUẢ HOẠT ĐỘNG KINH DOANH")
    idx_lctt = text.find("LƯU CHUYỂN TIỀN TỆ")
    idx_tm = text.find("THUYẾT MINH BÁO CÁO")
    
    # Logic cắt chuỗi đơn giản dựa trên index tìm được
    # Trong thực tế cần dùng Regex tinh vi hơn để tránh trùng lặp ở mục lục
    # TODO: Refine extraction logic based on index positions
    
    return sections

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()
        
    # Bước 1: Làm sạch rác và ngắt trang
    cleaned_text = clean_ocr_text(raw_text)
    
    # Bước 2: Tái tạo cấu trúc bảng từ HTML
    processed_text, tables = parse_html_tables(cleaned_text)
    
    # Bước 3: Chuẩn hóa số liệu trong các bảng
    normalized_tables = normalize_numbers(tables)
    
    # Bước 4: Tách mảnh cấu trúc logic (Chunks)
    structured_chunks = structure_document(processed_text, normalized_tables)
    
    return structured_chunks, normalized_tables

def main():
    base_dir = Path("./ViFinQA/financial_statements")
    
    # Test với một file mẫu
    sample_file = base_dir / "AAA/2015/AAA_financial_statements_2015_consolidated/AAA_financial_statements_2015_consolidated_extracted.txt"
    
    if sample_file.exists():
        print(f"Đang xử lý file: {sample_file}")
        structured_chunks, normalized_tables = process_file(sample_file)
        print(f"Đã tìm thấy {len(normalized_tables)} bảng trong tài liệu.")
        if normalized_tables:
            print("Preview bảng đầu tiên sau chuẩn hóa số liệu:")
            for row in normalized_tables[0][:5]: # In 5 dòng đầu
                print(row)
    else:
        print("Không tìm thấy file mẫu, vui lòng kiểm tra lại đường dẫn.")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
30x20 바코드 라벨 생성 GUI
기존 40x30 라벨과 별도로 관리되는 30mm x 20mm 크기 라벨 생성기
"""

import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import os
import time
import re
import sys
import argparse
from datetime import datetime
import json
import sqlite3

# 스크립트 디렉토리 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 제품 데이터 (간단한 예시)
products = {"TEST001": "테스트 제품 1", "TEST002": "테스트 제품 2"}

def create_label_30x20(product_code, lot, expiry, version, location, category):
    """30mm x 20mm 크기의 라벨 생성"""
    # 제품명 조회
    product_name = products.get(product_code, "알 수 없는 제품")

    # 일련번호 생성
    serial_number = get_next_serial_number()
    
    # 바코드 데이터는 일련번호만 사용
    barcode_data = str(serial_number)

    # 라벨 캔버스 생성 (30mm x 20mm 용지, 4배 확대된 해상도)
    LABEL_WIDTH = 480  # 가로 (30mm * 4 * 4 = 480px)
    LABEL_HEIGHT = 320  # 세로 (20mm * 4 * 4 = 320px)
    label = Image.new('RGB', (LABEL_WIDTH, LABEL_HEIGHT), 'white')
    draw = ImageDraw.Draw(label)
    
    # 한글 폰트 설정
    try:
        font = ImageFont.truetype("malgun.ttf", 20)
        font_small = ImageFont.truetype("malgun.ttf", 16)
        font_product = ImageFont.truetype("malgun.ttf", 18)
        font_info = ImageFont.truetype("malgun.ttf", 18)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_product = ImageFont.load_default()
        font_info = ImageFont.load_default()

    # 텍스트 배치
    y_pos = 10
    
    # 제품명
    draw.text((15, y_pos), f"제품명: {product_name}", fill="black", font=font_product)
    y_pos += 24
    
    # 구분
    draw.text((15, y_pos), f"구분: {category}", fill="black", font=font_product)
    y_pos += 24
    
    # LOT, 유통기한, 버전
    lot_expiry_version_text = f"LOT: {lot}    유통기한: {expiry}    버전: {version}"
    draw.text((15, y_pos), lot_expiry_version_text, fill="black", font=font_info)
    y_pos += 24
    
    # 보관위치
    draw.text((15, y_pos), f"보관위치: {location}", fill="black", font=font_info)

    # 바코드 생성 및 추가
    try:
        barcode_class = barcode.get_barcode_class('code128')
        barcode_image = barcode_class(barcode_data, writer=ImageWriter())
        barcode_img = barcode_image.render({'write_text': False})
        
        # 바코드 크기 조정
        barcode_width = LABEL_WIDTH - 30
        barcode_height = 100
        barcode_img = barcode_img.resize((barcode_width, barcode_height), Image.Resampling.LANCZOS)
        
        # 바코드 배치
        barcode_x = 4
        barcode_y = LABEL_HEIGHT - barcode_height - 60
        label.paste(barcode_img, (barcode_x, barcode_y))
        
        # 바코드 아래 텍스트
        barcode_text = f"{product_code}-{lot}-{expiry}-{version}"
        text_bbox = draw.textbbox((0, 0), barcode_text, font=font_small)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (LABEL_WIDTH - text_width) // 2
        draw.text((text_x, LABEL_HEIGHT - 35), barcode_text, fill="black", font=font_small)
        
    except Exception as e:
        print(f"바코드 생성 실패: {e}")
        draw.text((15, LABEL_HEIGHT - 60), f"바코드: {barcode_data}", fill="black", font=font_small)

    # labeljpg_30x20 폴더 생성
    labeljpg_dir = os.path.join(SCRIPT_DIR, "labeljpg_30x20")
    if not os.path.exists(labeljpg_dir):
        os.makedirs(labeljpg_dir)
    
    # 라벨 저장
    filename = os.path.join(labeljpg_dir, f"{product_code}-{location}.jpg")
    label.save(filename)
    
    # 발행 내역 저장
    save_issue_history(product_code, lot, expiry, version, location, filename, category, serial_number)
    
    return label, filename

def save_issue_history(product_code, lot, expiry, version, location, filename, category, barcode_number):
    """발행 내역 저장"""
    try:
        history_file = os.path.join(SCRIPT_DIR, "issue_history_30x20.xlsx")
        
        # 기존 파일이 있으면 읽고, 없으면 새로 생성
        try:
            df_history = pd.read_excel(history_file)
        except FileNotFoundError:
            df_history = pd.DataFrame({
                '발행일시': [],
                '구분': [],
                '제품코드': [],
                '제품명': [],
                'LOT': [],
                '유통기한': [],
                '버전': [],
                '보관위치': [],
                '파일명': [],
                '바코드숫자': []
            })
        
        # 새 발행 내역 추가
        product_name = products.get(product_code, "알 수 없는 제품")
        new_row = {
            '발행일시': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            '구분': category,
            '제품코드': product_code,
            '제품명': product_name,
            'LOT': lot,
            '유통기한': expiry,
            '버전': version,
            '보관위치': location,
            '파일명': filename,
            '바코드숫자': barcode_number
        }
        
        df_history = pd.concat([df_history, pd.DataFrame([new_row])], ignore_index=True)
        df_history.to_excel(history_file, index=False)
        
        print(f"발행 내역이 {history_file}에 저장되었습니다.")
        
    except Exception as e:
        print(f"발행 내역 저장 중 오류: {e}")

def get_next_serial_number():
    """다음 일련번호 가져오기"""
    db_path = os.path.join(SCRIPT_DIR, 'label_serial_30x20.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT MAX(serial_number) FROM label_info')
    result = cursor.fetchone()
    
    conn.close()
    
    if result[0] is None:
        return 1
    else:
        return result[0] + 1

def init_serial_database():
    """일련번호 데이터베이스 초기화"""
    db_path = os.path.join(SCRIPT_DIR, 'label_serial_30x20.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS label_info")
    cursor.execute('''
        CREATE TABLE label_info (
            serial_number INTEGER,
            product_code TEXT NOT NULL,
            lot TEXT NOT NULL,
            expiry TEXT NOT NULL,
            version TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def show_preview(label_image, filename, product_code, lot, expiry, version, location, category):
    """미리보기 창"""
    preview_window = tk.Toplevel()
    preview_window.title("라벨 미리보기 (30x20)")
    preview_window.geometry("600x500")
    
    # 제목
    title_label = tk.Label(preview_window, text="생성된 라벨 미리보기 (30x20)", 
                           font=("맑은 고딕", 14, "bold"))
    title_label.pack(pady=10)
    
    # 라벨 정보
    info_frame = tk.Frame(preview_window)
    info_frame.pack(pady=5)
    
    tk.Label(info_frame, text=f"구분: {category}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"제품코드: {product_code}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"LOT: {lot}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"유통기한: {expiry}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"버전: {version}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"보관위치: {location}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"파일명: {filename}", font=("맑은 고딕", 10)).pack()
    
    # 이미지 표시
    temp_preview = "temp_preview_30x20.png"
    label_image.save(temp_preview)
    
    img = tk.PhotoImage(file=temp_preview)
    img_label = tk.Label(preview_window, image=img)
    img_label.image = img
    img_label.pack(pady=10)
    
    # 버튼 프레임
    button_frame = tk.Frame(preview_window)
    button_frame.pack(pady=20)
    
    # 인쇄 버튼
    def print_label():
        try:
            os.startfile(filename, "print")
            time.sleep(2)
            preview_window.destroy()
        except Exception as e:
            messagebox.showerror("인쇄 오류", f"인쇄 실패: {e}")
    
    print_btn = tk.Button(button_frame, text="인쇄", command=print_label,
                          bg="#4CAF50", fg="white", font=("맑은 고딕", 11),
                          relief=tk.FLAT, bd=0, padx=20, pady=5)
    print_btn.pack(side=tk.LEFT, padx=5)
    
    # 닫기 버튼
    def close_preview():
        try:
            os.remove(temp_preview)
        except:
            pass
        preview_window.destroy()
    
    close_btn = tk.Button(button_frame, text="닫기", command=close_preview,
                          bg="#f44336", fg="white", font=("맑은 고딕", 11),
                          relief=tk.FLAT, bd=0, padx=20, pady=5)
    close_btn.pack(side=tk.LEFT, padx=5)
    
    preview_window.protocol("WM_DELETE_WINDOW", close_preview)

def on_submit():
    """라벨 생성 제출"""
    try:
        product_code = combo_code.get().upper()
        category = category_var.get()
        location = location_var.get()
        
        if not product_code or not location:
            messagebox.showwarning("경고", "제품코드와 보관위치를 입력하세요.")
            return
        
        if category in ["관리품", "표준품", "벌크표준"]:
            lot = entry_lot.get()
            expiry = entry_expiry.get()
            version = entry_version.get()
            if not lot or not expiry or not version:
                messagebox.showwarning("경고", f"{category}은 LOT, 유통기한, 버전을 모두 입력하세요.")
                return
        else:
            lot = "SAMPLE"
            expiry = "N/A"
            version = "N/A"
        
        # 라벨 생성
        label_image, filename = create_label_30x20(product_code, lot, expiry, version, location, category)
        
        # 미리보기 창 표시
        show_preview(label_image, filename, product_code, lot, expiry, version, location, category)
        
        messagebox.showinfo("완료", f"30x20 라벨({filename})이 생성되었습니다!")
        
    except Exception as e:
        messagebox.showerror("오류", f"라벨 생성 중 오류가 발생했습니다:\n{e}")

def update_product_name(event=None):
    """제품명 업데이트"""
    code = combo_code.get().upper()
    name = products.get(code, "알 수 없는 제품")
    label_product_name.config(text=f"제품명: {name}")

def update_category_ui():
    """구분에 따라 UI 업데이트"""
    category = category_var.get()
    
    if category == "샘플재고":
        lot_label.pack_forget()
        entry_lot.pack_forget()
        expiry_label.pack_forget()
        expiry_frame.pack_forget()
        entry_expiry.pack_forget()
        version_label.pack_forget()
        entry_version.pack_forget()
        
        entry_lot.delete(0, tk.END)
        entry_lot.insert(0, "SAMPLE")
        entry_expiry.delete(0, tk.END)
        entry_expiry.insert(0, "N/A")
        entry_version.delete(0, tk.END)
        entry_version.insert(0, "N/A")
    else:
        lot_label.pack(pady=5)
        entry_lot.pack(pady=5)
        expiry_label.pack(pady=5)
        expiry_frame.pack(pady=5)
        entry_expiry.pack(side=tk.LEFT, padx=(0, 10))
        version_label.pack(pady=5)
        entry_version.pack(pady=5)
        
        entry_lot.delete(0, tk.END)
        entry_lot.insert(0, "")
        entry_expiry.delete(0, tk.END)
        entry_expiry.insert(0, "")
        entry_version.delete(0, tk.END)
        entry_version.insert(0, "")

# 데이터베이스 초기화
init_serial_database()

# GUI 생성
root = tk.Tk()
root.title("바코드 라벨 관리 시스템 - 30x20 라벨 발행")
root.geometry("500x600")

# 제목
title_label = tk.Label(root, text="30x20 바코드 라벨 생성기", 
                       font=("맑은 고딕", 16, "bold"))
title_label.pack(pady=10)

# 구분 선택
tk.Label(root, text="구분:").pack(pady=5)
category_var = tk.StringVar(value="관리품")
category_frame = tk.Frame(root)
category_frame.pack(pady=5)

management_radio = tk.Radiobutton(category_frame, text="관리품", variable=category_var, value="관리품",
                                  font=("맑은 고딕", 10), command=update_category_ui)
management_radio.grid(row=0, column=0, padx=10, pady=5)

standard_radio = tk.Radiobutton(category_frame, text="표준품", variable=category_var, value="표준품",
                                font=("맑은 고딕", 10), command=update_category_ui)
standard_radio.grid(row=0, column=1, padx=10, pady=5)

bulk_radio = tk.Radiobutton(category_frame, text="벌크표준", variable=category_var, value="벌크표준",
                            font=("맑은 고딕", 10), command=update_category_ui)
bulk_radio.grid(row=1, column=0, padx=10, pady=5)

sample_radio = tk.Radiobutton(category_frame, text="샘플재고", variable=category_var, value="샘플재고",
                              font=("맑은 고딕", 10), command=update_category_ui)
sample_radio.grid(row=1, column=1, padx=10, pady=5)

# 제품코드
tk.Label(root, text="제품코드:").pack(pady=5)
product_codes = list(products.keys())
combo_code = ttk.Combobox(root, values=product_codes, width=30)
combo_code.pack(pady=5)
combo_code.bind("<<ComboboxSelected>>", update_product_name)

# 제품명 표시
label_product_name = tk.Label(root, text="제품명: ", wraplength=400)
label_product_name.pack(pady=5)

# 보관위치
tk.Label(root, text="보관위치:").pack(pady=5)
location_var = tk.StringVar()
location_combo = ttk.Combobox(root, textvariable=location_var, 
                              values=[f"{zone}-{section:02d}-{position:02d}" 
                                     for zone in ['A', 'B'] 
                                     for section in range(1, 6) 
                                     for position in range(1, 4)], width=15)
location_combo.pack(pady=5)

# LOT 번호
lot_label = tk.Label(root, text="LOT 번호:")
entry_lot = tk.Entry(root, width=30)

# 유통기한
expiry_label = tk.Label(root, text="유통기한:")
expiry_frame = tk.Frame(root)
entry_expiry = tk.Entry(expiry_frame, width=20)

# 버전
version_label = tk.Label(root, text="버전:")
entry_version = tk.Entry(root, width=30)

# 달력 버튼
def show_calendar():
    def set_date():
        selected_date = cal.get_date()
        entry_expiry.delete(0, tk.END)
        entry_expiry.insert(0, selected_date.strftime("%Y-%m-%d"))
        top.destroy()
    
    top = tk.Toplevel(root)
    top.title("유통기한 선택")
    top.geometry("300x250")
    
    cal = DateEntry(top, width=12, background='darkblue', foreground='white', 
                   borderwidth=2, date_pattern='yyyy-mm-dd')
    cal.pack(pady=20)
    
    tk.Button(top, text="선택", command=set_date).pack(pady=10)

tk.Button(expiry_frame, text="📅", command=show_calendar, width=3).pack(side=tk.LEFT)

# 초기 UI 설정
update_category_ui()

# 버튼
button_frame = tk.Frame(root)
button_frame.pack(pady=20)

tk.Button(button_frame, text="30x20 라벨 생성", command=on_submit,
          bg="#4CAF50", fg="white", font=("맑은 고딕", 12, "bold"),
          relief=tk.FLAT, bd=0, padx=20, pady=10).pack()

# 안내 메시지
info_label = tk.Label(root, text="30mm x 20mm 크기의 바코드 라벨을 생성합니다.\n기존 40x30 라벨과 별도로 관리됩니다.",
                      font=("맑은 고딕", 10), fg="blue")
info_label.pack(pady=10)

print("30x20 바코드 라벨 GUI가 준비되었습니다.")
print("이 파일은 30mm x 20mm 크기의 라벨을 생성합니다.")
print("기존 40x30 라벨과 별도로 관리됩니다.")

root.mainloop()

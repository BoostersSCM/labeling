# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import qrcode
import os
import time
import re
import subprocess
import sys
import argparse
from datetime import datetime

# 상위 디렉토리의 execute_query.py 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execute_query import call_query
from mysql_auth import boosta_boosters
from boosters_query import q_boosters_items_for_barcode_reader, q_boosters_items_limit_date


# ✅ CSV/엑셀에서 제품 리스트 불러오기
def load_products():
    df = call_query(q_boosters_items_for_barcode_reader.query,boosta_boosters)
    df_limit_date = call_query(q_boosters_items_limit_date.query,boosta_boosters)
    df = pd.merge(df, df_limit_date, on='제품코드', how='left')
    products_dict = dict(zip(df['제품코드'].astype(str), df['제품명']))
    
    # 바코드 정보도 함께 로드 (바코드 컬럼이 있는 경우)
    barcode_dict = {}
    if '바코드' in df.columns:
        for _, row in df.iterrows():
            barcode = str(row['바코드']).strip()
            if barcode and barcode != 'nan':
                barcode_dict[barcode] = str(row['제품코드'])
    
    # 유통기한 정보도 함께 로드
    expiry_info_dict = {}
    for _, row in df.iterrows():
        product_code = str(row['제품코드'])
        expiry_days = row.get('유통기한_일수')
        expiry_unit = row.get('유통기한_구분')
        
        if expiry_days is not None and expiry_unit is not None and str(expiry_days) != 'nan' and str(expiry_unit) != 'nan':
            expiry_info_dict[product_code] = {
                'days': expiry_days,
                'unit': expiry_unit
            }
    
    return products_dict, barcode_dict, expiry_info_dict

# products, barcode_to_product = load_products("barcode_label/products.xlsx")  # 올바른 경로
products, barcode_to_product, expiry_info = load_products()  
# 보관위치 검증 함수
def validate_location(location):
    """
    보관위치 형식 검증: 알파벳(A,B) + 숫자2자리(01~05) + 숫자2자리(01~03)
    예: A-01-01, B-03-02
    """
    pattern = r'^[AB]-(0[1-5])-(0[1-3])$'
    if not re.match(pattern, location):
        return False, "보관위치 형식이 올바르지 않습니다.\n\n형식: 알파벳(A,B) + 숫자2자리(01~05) + 숫자2자리(01~03)\n예시: A-01-01, B-03-02"
    
    return True, ""

# 바코드 리딩 처리 함수
def process_barcode_scan(barcode_data):
    """
    바코드 리딩 데이터 처리 (순차적 유도)
    - 보관위치 바코드: A-01-01 형식이면 보관위치에 입력 후 제품 바코드 유도
    - 제품 바코드: 88로 시작하면 제품코드에 입력 후 보관위치 바코드 유도
    """
    barcode_data = barcode_data.strip()
    
    # 보관위치 바코드인지 확인
    is_valid_location, _ = validate_location(barcode_data)
    if is_valid_location:
        entry_location.delete(0, tk.END)
        entry_location.insert(0, barcode_data)
        
        # 상태 업데이트
        update_barcode_status("✅ 보관위치 스캔 완료 → 제품 바코드를 스캔하세요", "#4CAF50")
        
        # 제품 바코드 입력 유도
        show_next_barcode_prompt("보관위치", "제품")
        return True
    
    # 제품 바코드인지 확인 (88로 시작하는 경우)
    if barcode_data.startswith('88'):
        if barcode_data in barcode_to_product:
            product_code = barcode_to_product[barcode_data]
            combo_code.set(product_code)
            update_product_name()
            
            # 상태 업데이트
            update_barcode_status("✅ 제품 스캔 완료 → 보관위치 바코드를 스캔하세요", "#4CAF50")
            
            # 보관위치 바코드 입력 유도
            show_next_barcode_prompt("제품", "보관위치")
            return True
        else:
            messagebox.showwarning("바코드 오류", f"등록되지 않은 제품 바코드입니다: {barcode_data}")
            return False
    
    # 알 수 없는 바코드 형식
    messagebox.showwarning("바코드 오류", f"알 수 없는 바코드 형식입니다: {barcode_data}")
    return False

def check_barcode_completion():
    """
    바코드 입력 완료 여부 확인
    보관위치와 제품코드가 모두 입력되면 True 반환
    """
    location = entry_location.get().strip()
    product_code = combo_code.get().strip()
    
    # 보관위치가 올바른 형식이고 제품코드가 선택되었는지 확인
    is_valid_location, _ = validate_location(location)
    has_product = product_code and product_code in products
    
    return is_valid_location and has_product

def show_next_barcode_prompt(current_type, next_type):
    """
    다음 바코드 입력을 유도하는 메시지 표시
    """
    if next_type == "제품":
        messagebox.showinfo("바코드 스캔 완료", 
                          f"✅ {current_type} 바코드 스캔 완료\n\n"
                          f"다음 단계: 제품 바코드를 스캔하세요\n"
                          f"제품 바코드는 '88'로 시작합니다.")
        combo_code.focus()
    else:  # next_type == "보관위치"
        messagebox.showinfo("바코드 스캔 완료", 
                          f"✅ {current_type} 바코드 스캔 완료\n\n"
                          f"다음 단계: 보관위치 바코드를 스캔하세요\n"
                          f"보관위치 형식: A-01-01, B-03-02")
        entry_location.focus()

def update_barcode_status(status_text, color="#2196F3"):
    """
    바코드 리딩 창의 상태 표시 업데이트
    """
    try:
        # 바코드 리딩 창이 열려있는지 확인하고 상태 업데이트
        for widget in root.winfo_children():
            if isinstance(widget, tk.Toplevel) and widget.title() == "바코드 리딩":
                for child in widget.winfo_children():
                    if isinstance(child, tk.Frame):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, tk.Label) and "📋" in grandchild.cget("text"):
                                grandchild.config(text=status_text, fg=color)
                                break
    except:
        pass  # 창이 닫혀있거나 오류가 발생해도 무시

# 발행 내역 저장 함수
def save_issue_history(product_code, lot, expiry, location, filename, category):
    try:
        # 발행 내역 파일 경로
        history_file = os.path.join(os.path.dirname(__file__), "issue_history.xlsx")
        # 파일이 없으면 디렉토리 생성 및 빈 파일 생성
        if not os.path.exists(history_file):
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
            # 빈 DataFrame으로 엑셀 파일 생성
            empty_df = pd.DataFrame({
                '발행일시': [],
                '구분': [],
                '제품코드': [],
                '제품명': [],
                'LOT': [],
                '유통기한': [],
                '폐기일자': [],
                '보관위치': [],
                '파일명': []
            })
            empty_df.to_excel(history_file, index=False)
        
        # 폐기일자 계산 (유통기한 + 1년)
        try:
            # 유통기한이 이미 datetime 객체인 경우
            if isinstance(expiry, datetime):
                expiry_date = expiry
            else:
                # 문자열인 경우 파싱
                expiry_date = datetime.strptime(str(expiry), "%Y-%m-%d")
            
            # 1년 후 날짜 계산
            disposal_date = expiry_date.replace(year=expiry_date.year + 1)
            disposal_date_str = disposal_date.strftime("%Y-%m-%d")
        except Exception as e:
            print(f"폐기일자 계산 오류: {e}, 유통기한: {expiry}")
            disposal_date_str = "N/A"
        
        # 기존 파일이 있으면 읽고, 없으면 새로 생성
        try:
            df_history = pd.read_excel(history_file)
        except FileNotFoundError:
            df_history = pd.DataFrame({
                '발행일시': [],
                '제품코드': [],
                '제품명': [],
                'LOT': [],
                '유통기한': [],
                '폐기일자': [],
                '보관위치': [],
                '파일명': []
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
            '폐기일자': disposal_date_str,
            '보관위치': location,
            '파일명': filename
        }
        
        df_history = pd.concat([df_history, pd.DataFrame([new_row])], ignore_index=True)
        df_history.to_excel(history_file, index=False)
        
        print(f"발행 내역이 {history_file}에 저장되었습니다.")
        
    except Exception as e:
        print(f"발행 내역 저장 중 오류: {e}")

# 미리보기 함수
def show_preview(label_image, filename, product_code, lot, expiry, location, category):
    # 미리보기 창 생성
    preview_window = tk.Toplevel()
    preview_window.title("라벨 미리보기")
    preview_window.geometry("800x600")
    
    # 제목
    title_label = tk.Label(preview_window, text="생성된 라벨 미리보기", 
                           font=("맑은 고딕", 14, "bold"))
    title_label.pack(pady=10)
    
    # 라벨 정보
    info_frame = tk.Frame(preview_window)
    info_frame.pack(pady=5)
    
    tk.Label(info_frame, text=f"구분: {category}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"제품코드: {product_code}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"LOT: {lot}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"유통기한: {expiry}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"보관위치: {location}", font=("맑은 고딕", 10)).pack()
    tk.Label(info_frame, text=f"파일명: {filename}", font=("맑은 고딕", 10)).pack()
    
    # 스크롤 가능한 캔버스 생성
    canvas_frame = tk.Frame(preview_window)
    canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 캔버스와 스크롤바
    canvas = tk.Canvas(canvas_frame, bg="white")
    v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
    h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=canvas.xview)
    
    canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    
    # 라벨 이미지 표시
    temp_preview = "temp_preview.png"
    label_image.save(temp_preview)
    
    # 이미지 로드 및 크기 조정
    img = tk.PhotoImage(file=temp_preview)
    
    # 이미지 크기 조정 (원본 크기 유지)
    img_width = img.width()
    img_height = img.height()
    
    # 캔버스에 이미지 추가
    canvas.create_image(0, 0, anchor=tk.NW, image=img)
    # 참조 유지를 위해 전역 변수로 저장
    canvas._image = img
    
    # 스크롤 영역 설정
    canvas.configure(scrollregion=canvas.bbox("all"))
    
    # 스크롤바 배치
    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # 버튼 프레임
    button_frame = tk.Frame(preview_window)
    button_frame.pack(pady=20)
    
    # 인쇄 버튼
    def print_label():
        try:
            os.startfile(filename, "print")
            time.sleep(2)
            messagebox.showinfo("인쇄 완료", "라벨이 프린터로 전송되었습니다.\n\n💡 인쇄 팁:\n- 인쇄 창에서 '크기 조정' 옵션을 '실제 크기'로 설정하세요\n- '여백'을 '없음'으로 설정하면 더 깔끔하게 인쇄됩니다")
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
            os.remove(temp_preview)  # 임시 파일 삭제
        except:
            pass
        preview_window.destroy()
    
    close_btn = tk.Button(button_frame, text="닫기", command=close_preview,
                          bg="#f44336", fg="white", font=("맑은 고딕", 11),
                          relief=tk.FLAT, bd=0, padx=20, pady=5)
    close_btn.pack(side=tk.LEFT, padx=5)
    
    # 창이 닫힐 때 임시 파일 삭제
    preview_window.protocol("WM_DELETE_WINDOW", close_preview)

def create_label(product_code, lot, expiry, location, category):
    # 제품명 조회
    product_name = products.get(product_code, "알 수 없는 제품")

    # 바코드에 포함할 전체 정보 (구분에 따라 다름)
    if category == "관리품":
        barcode_data = f"{product_code}-{lot}-{expiry}"
    else:
        barcode_data = f"{product_code}-SAMPLE"

    # 바코드 생성 (텍스트 없이)
    ean = barcode.get('code128', barcode_data, writer=ImageWriter())
    barcode_filename = ean.save('barcode', {'write_text': False})

    # 라벨 캔버스 생성 (로고와 QR코드를 위해 높이 증가)
    label = Image.new('RGB', (600, 400), 'white')
    draw = ImageDraw.Draw(label)
    
    # 한글 폰트 설정 (Windows 기본 폰트 사용)
    try:
        font = ImageFont.truetype("malgun.ttf", 20)  # 맑은 고딕
        font_small = ImageFont.truetype("malgun.ttf", 16)  # 작은 폰트
    except:
        try:
            font = ImageFont.truetype("gulim.ttc", 20)  # 굴림체
            font_small = ImageFont.truetype("gulim.ttc", 16)  # 작은 폰트
        except:
            font = ImageFont.load_default()  # 기본 폰트
            font_small = ImageFont.load_default()

    # 텍스트 줄바꿈 함수
    def wrap_text(text, max_width):
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if len(test_line) * 10 <= max_width:  # 대략적인 폰트 너비 계산
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    # 좌측 상단: 회사 로고 (PNG 파일에서 불러오기)
    try:
        logo_path = "barcode_label/logo.png"
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path)
            logo_img = logo_img.resize((120, 60))  # 로고 크기 조정
            label.paste(logo_img, (20, 20))  # 좌측 상단에 배치
        else:
            # 로고 파일이 없으면 텍스트로 대체
            company_name = "부스터스 뷰티"
            draw.text((20, 20), company_name, fill="#2E86AB", font=font)
            draw.text((20, 45), "BOOSTERS BEAUTY", fill="#2E86AB", font=font_small)
    except Exception as e:
        # 로고 로드 실패 시 텍스트로 대체
        print(f"로고 로드 실패: {e}")
        company_name = "부스터스 뷰티"
        draw.text((20, 20), company_name, fill="#2E86AB", font=font)
        draw.text((20, 45), "BOOSTERS BEAUTY", fill="#2E86AB", font=font_small)
    
    # 우측 상단: QR코드 생성
    qr_data = f"제품코드: {product_code}\n제품명: {product_name}\nLOT: {lot}\n유통기한: {expiry}"
    
    try:
        # QR코드 생성 및 저장
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # 임시 파일로 저장 후 다시 로드
        qr_temp_file = "temp_qr.png"
        qr_img.save(qr_temp_file, "PNG")
        qr_img_pil = Image.open(qr_temp_file)
        qr_img_pil = qr_img_pil.resize((80, 80))
        label.paste(qr_img_pil, (500, 20))  # 우측 상단에 배치
        os.remove(qr_temp_file)  # 임시 파일 삭제
        
    except Exception as e:
        # QR코드 생성 실패 시 텍스트로 대체
        print(f"QR코드 생성 실패: {e}")
        qr_text = f"QR: {product_code}"
        draw.text((500, 20), qr_text, fill="black", font=font_small)
        draw.text((500, 40), "스캔하여", fill="black", font=font_small)
        draw.text((500, 60), "상세정보 확인", fill="black", font=font_small)

    # 제품 정보 (로고 아래로 이동)
    draw.text((20, 100), f"제품코드: {product_code}", fill="black", font=font)
    
    # 제품명 줄바꿈 처리
    product_name_lines = wrap_text(product_name, 450)  # QR코드 공간 고려
    y_pos = 140
    for line in product_name_lines:
        draw.text((20, y_pos), f"제품명: {line}" if y_pos == 140 else line, fill="black", font=font)
        y_pos += 25
    
    draw.text((20, y_pos), f"LOT: {lot}", fill="black", font=font)
    draw.text((20, y_pos + 40), f"유통기한: {expiry}", fill="black", font=font)
    draw.text((20, y_pos + 80), f"보관위치: {location}", fill="black", font=font)

    # 바코드 붙이기 (하단으로 이동)
    barcode_img = Image.open(barcode_filename)
    barcode_width = 400
    barcode_x = (600 - barcode_width) // 2  # 중앙 정렬
    label.paste(barcode_img.resize((barcode_width, 100)), (barcode_x, 270))

    # labeljpg 폴더 생성 및 확인
    labeljpg_dir = "labeljpg"
    if not os.path.exists(labeljpg_dir):
        os.makedirs(labeljpg_dir)
    
    # 라벨 저장 (파일명: 제품코드-LOT-유통기한-보관위치.jpg)
    filename = os.path.join(labeljpg_dir, f"{product_code}-{lot}-{expiry}-{location}.jpg")
    
    # 파일 저장 전 디렉토리 재확인
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    label.save(filename)
    
    # 발행 내역 저장
    save_issue_history(product_code, lot, expiry, location, filename, category)
    
    # 미리보기 창 표시
    show_preview(label, filename, product_code, lot, expiry, location, category)

    # 발행 완료 메시지
    messagebox.showinfo("완료", f"라벨({filename})이 생성되었습니다!\n발행 내역이 자동으로 저장되었습니다.\n\n미리보기 창에서 인쇄하실 수 있습니다.")

def update_category_ui():
    """구분에 따라 UI 업데이트"""
    category = category_var.get()
    
    if category == "관리품":
        # 관리품일 때 LOT과 유통기한 표시
        lot_label.pack(pady=5)
        entry_lot.pack(pady=5)
        expiry_label.pack(pady=5)
        expiry_frame.pack(pady=5)
        entry_expiry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 관리품으로 전환 시 기본값 설정
        entry_lot.delete(0, tk.END)
        entry_lot.insert(0, "")
        entry_expiry.delete(0, tk.END)
        entry_expiry.insert(0, "")
        
        # 제품코드 초기화
        combo_code.set("")
        label_product_name.config(text="제품명: ")
        
        # 포커스를 제품코드 입력창으로 이동
        combo_code.focus()
        
    else:
        # 샘플재고일 때 LOT과 유통기한 숨김
        lot_label.pack_forget()
        entry_lot.pack_forget()
        expiry_label.pack_forget()
        expiry_frame.pack_forget()
        entry_expiry.pack_forget()
        
        # 샘플재고로 전환 시 기본값 설정
        entry_lot.delete(0, tk.END)
        entry_lot.insert(0, "SAMPLE")
        entry_expiry.delete(0, tk.END)
        entry_expiry.insert(0, "N/A")
        
        # 제품코드 초기화
        combo_code.set("")
        label_product_name.config(text="제품명: ")
        
        # 포커스를 제품코드 입력창으로 이동
        combo_code.focus()

def update_product_name(event=None):
    code = combo_code.get().upper()  # 소문자를 대문자로 변환
    name = products.get(code, "알 수 없는 제품")
    
    # 유통기한 정보 표시
    expiry_text = ""
    if code in expiry_info:
        expiry_data = expiry_info[code]
        expiry_days = expiry_data['days']
        expiry_unit = expiry_data['unit']
        if expiry_days is not None and expiry_unit is not None and str(expiry_days) != 'nan' and str(expiry_unit) != 'nan':
            expiry_text = f" {expiry_days} {expiry_unit}"
    
    label_product_name.config(text=f"제품명: {name}")
    
    # 유통기한 라벨 업데이트
    expiry_label.config(text=f"유통기한:{expiry_text}")
    
    # 유통기한 기본값 설정
    if code in expiry_info:
        expiry_data = expiry_info[code]
        expiry_days = expiry_data['days']
        expiry_unit = expiry_data['unit']
        
        if expiry_days is not None and expiry_unit is not None and str(expiry_days) != 'nan' and str(expiry_unit) != 'nan':
            try:
                # 오늘 날짜에서 30일을 뺀 후 유통기한을 더함
                from datetime import datetime, timedelta
                today = datetime.now()
                base_date = today - timedelta(days=30)
                
                # 유통기한 계산
                if expiry_unit == '월':
                    # 월 단위 계산 (대략 30일로 계산)
                    calculated_days = int(expiry_days) * 30
                elif expiry_unit == '일':
                    calculated_days = int(expiry_days)
                else:
                    calculated_days = 0
                
                if calculated_days > 0:
                    expiry_date = base_date + timedelta(days=calculated_days)
                    entry_expiry.delete(0, tk.END)
                    entry_expiry.insert(0, expiry_date.strftime("%Y-%m-%d"))
            except Exception as e:
                print(f"유통기한 계산 오류: {e}")

def on_submit():
    product_code = combo_code.get().upper()  # 소문자를 대문자로 변환
    category = category_var.get()
    location = entry_location.get()
    
    # 기본 입력 검증
    if not product_code or not location:
        messagebox.showwarning("경고", "제품코드와 보관위치를 입력하세요.")
        return
    
    # 관리품일 때만 LOT과 유통기한 검증
    if category == "관리품":
        lot = entry_lot.get()
        expiry = entry_expiry.get()
        if not lot or not expiry:
            messagebox.showwarning("경고", "관리품은 LOT과 유통기한을 모두 입력하세요.")
            return
    else:
        # 샘플재고일 때는 기본값 설정
        lot = "SAMPLE"
        expiry = "N/A"
    
    # 보관위치 형식 검증
    is_valid, error_message = validate_location(location)
    if not is_valid:
        messagebox.showerror("보관위치 오류", error_message)
        entry_location.focus()
        return
    
    create_label(product_code, lot, expiry, location, category)

# ✅ Tkinter GUI 생성
root = tk.Tk()
root.title("바코드 라벨 관리 시스템 - 라벨 발행")
root.geometry("600x500")

# 명령행 인수 처리
parser = argparse.ArgumentParser(description='라벨 발행 GUI')
parser.add_argument('--location', type=str, help='보관위치 설정')
args, unknown = parser.parse_known_args()

# 전역 바코드 리딩 단축키 (Ctrl+B)
def open_barcode_global(event):
    open_barcode_input()

root.bind('<Control-b>', open_barcode_global)
root.bind('<Control-B>', open_barcode_global)

# 구분 선택
tk.Label(root, text="구분:").pack(pady=5)
category_var = tk.StringVar(value="관리품")
category_frame = tk.Frame(root)
category_frame.pack(pady=5)

# 라디오 버튼으로 구분 선택
management_radio = tk.Radiobutton(category_frame, text="관리품", variable=category_var, value="관리품",
                                  font=("맑은 고딕", 10), command=lambda: refresh_ui_for_management())
management_radio.pack(side=tk.LEFT, padx=10)

sample_radio = tk.Radiobutton(category_frame, text="샘플재고", variable=category_var, value="샘플재고",
                              font=("맑은 고딕", 10), command=lambda: refresh_ui_for_sample())
sample_radio.pack(side=tk.LEFT, padx=10)

def refresh_ui_for_management():
    """관리품 선택 시 UI 새로고침"""
    update_category_ui()
    # 관리품 관련 안내 메시지
    messagebox.showinfo("관리품 모드", 
                       "✅ 관리품 모드로 전환되었습니다.\n\n"
                       "📋 관리품은 다음 정보가 필요합니다:\n"
                       "• 제품코드\n"
                       "• LOT 번호\n"
                       "• 유통기한\n"
                       "• 보관위치\n\n"
                       "모든 필드를 입력한 후 라벨을 생성하세요.")

def refresh_ui_for_sample():
    """샘플재고 선택 시 UI 새로고침"""
    update_category_ui()
    # 샘플재고 관련 안내 메시지
    messagebox.showinfo("샘플재고 모드", 
                       "✅ 샘플재고 모드로 전환되었습니다.\n\n"
                       "📋 샘플재고는 다음 정보가 필요합니다:\n"
                       "• 제품코드\n"
                       "• 보관위치\n\n"
                       "LOT과 유통기한은 자동으로 설정됩니다:\n"
                       "• LOT: SAMPLE\n"
                       "• 유통기한: N/A")

# 제품코드 검색 및 드롭다운
tk.Label(root, text="제품코드:").pack(pady=5)
product_codes = list(products.keys())
product_var = tk.StringVar()

# 검색 가능한 콤보박스
combo_code = ttk.Combobox(root, textvariable=product_var, values=product_codes, width=30)
combo_code.pack(pady=5)
combo_code.bind("<KeyRelease>", lambda e: filter_products())
combo_code.bind("<<ComboboxSelected>>", update_product_name)

# 제품명 표시
label_product_name = tk.Label(root, text="제품명: ", wraplength=450)
label_product_name.pack(pady=5)

# LOT 번호 (관리품일 때만 표시)
lot_label = tk.Label(root, text="LOT 번호:")
entry_lot = tk.Entry(root, width=30)

# 유통기한 (수기입력 + 달력) - 관리품일 때만 표시
global expiry_label, expiry_frame, entry_expiry
expiry_label = tk.Label(root, text="유통기한:")
expiry_frame = tk.Frame(root)
entry_expiry = tk.Entry(expiry_frame, width=20)

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
    
    # 현재 유통기한 입력창의 값을 기본값으로 사용
    current_expiry = entry_expiry.get().strip()
    default_date = None
    
    if current_expiry:
        try:
            # 현재 입력된 날짜를 기본값으로 설정
            default_date = datetime.strptime(current_expiry, "%Y-%m-%d")
        except:
            pass
    
    # 기본값이 없으면 오늘 날짜 사용
    if default_date is None:
        default_date = datetime.now()
    
    cal = DateEntry(top, width=12, background='darkblue', foreground='white', 
                   borderwidth=2, date_pattern='yyyy-mm-dd')
    cal.pack(pady=20)
    
    # 기본 날짜 설정
    if default_date:
        cal.set_date(default_date)
    
    tk.Button(top, text="선택", command=set_date).pack(pady=10)

tk.Button(expiry_frame, text="📅", command=show_calendar, width=3).pack(side=tk.LEFT)

# 보관위치 (수기입력 + 바코드 스캐너)
tk.Label(root, text="보관위치:").pack(pady=5)
location_frame = tk.Frame(root)
location_frame.pack(pady=5)

entry_location = tk.Entry(location_frame, width=20)
entry_location.pack(side=tk.LEFT, padx=(0, 10))

# 명령행 인수로 받은 보관위치가 있으면 자동 설정
if args.location:
    entry_location.insert(0, args.location)

# 보관위치 실시간 검증
def validate_location_realtime(*args):
    location = entry_location.get().strip()
    if location:
        is_valid, _ = validate_location(location)
        if is_valid:
            help_label.config(text="✓ 올바른 형식입니다", fg="green")
        else:
            help_label.config(text="형식: A-01-01, B-03-02 (A,B 구역, 01~05, 01~03)", fg="red")
    else:
        help_label.config(text="형식: A-01-01, B-03-02 (A,B 구역, 01~05, 01~03)", fg="gray")

entry_location.bind('<KeyRelease>', validate_location_realtime)

# 보관위치 도움말
help_label = tk.Label(root, text="형식: A-01-01, B-03-02 (A,B 구역, 01~05, 01~03)", 
                      font=("맑은 고딕", 8), fg="gray")
help_label.pack(pady=2)

# 바코드 리딩 입력 창
def open_barcode_input():
    def submit_barcode():
        barcode_data = barcode_entry.get().strip()
        if barcode_data:
            if process_barcode_scan(barcode_data):
                # 바코드 처리 후 입력창 초기화
                barcode_entry.delete(0, tk.END)
                barcode_entry.focus()
                
                # 바코드 입력 완료 확인
                if check_barcode_completion():
                    # 완료 메시지 표시 후 창 닫기
                    messagebox.showinfo("바코드 입력 완료", 
                                      "✅ 모든 바코드 입력이 완료되었습니다!\n\n"
                                      "보관위치: " + entry_location.get() + "\n"
                                      "제품코드: " + combo_code.get() + "\n\n"
                                      "바코드 리딩 창을 닫습니다.")
                    top.destroy()
                else:
                    # 아직 완료되지 않았으면 계속 사용
                    pass
            else:
                # 바코드 처리 실패 시 입력창 초기화
                barcode_entry.delete(0, tk.END)
                barcode_entry.focus()
        else:
            messagebox.showwarning("입력 오류", "바코드를 입력하세요.")
    
    def simulate_location_barcode():
        import random
        # 올바른 형식의 보관위치만 생성 (A,B 구역, 01~05, 01~03)
        locations = [
            "A-01-01", "A-01-02", "A-01-03",
            "A-02-01", "A-02-02", "A-02-03",
            "A-03-01", "A-03-02", "A-03-03",
            "A-04-01", "A-04-02", "A-04-03",
            "A-05-01", "A-05-02", "A-05-03",
            "B-01-01", "B-01-02", "B-01-03",
            "B-02-01", "B-02-02", "B-02-03",
            "B-03-01", "B-03-02", "B-03-03",
            "B-04-01", "B-04-02", "B-04-03",
            "B-05-01", "B-05-02", "B-05-03"
        ]
        barcode_entry.delete(0, tk.END)
        barcode_entry.insert(0, random.choice(locations))
        # 상태 업데이트
        update_barcode_status("🔄 보관위치 바코드 시뮬레이션 중...", "#FF9800")
        # 자동으로 제출
        submit_barcode()
        
        # 완료 확인 (시뮬레이션 후 잠시 대기)
        top.after(1500, check_and_close_if_complete)
    
    def check_and_close_if_complete():
        """완료 상태 확인 후 창 닫기"""
        if check_barcode_completion():
            messagebox.showinfo("바코드 입력 완료", 
                              "✅ 모든 바코드 입력이 완료되었습니다!\n\n"
                              "보관위치: " + entry_location.get() + "\n"
                              "제품코드: " + combo_code.get() + "\n\n"
                              "바코드 리딩 창을 닫습니다.")
            top.destroy()
    
    def simulate_product_barcode():
        # 88로 시작하는 제품 바코드 시뮬레이션
        import random
        product_barcodes = ["8801234567890", "8809876543210", "8812345678901"]
        barcode_entry.delete(0, tk.END)
        barcode_entry.insert(0, random.choice(product_barcodes))
        # 상태 업데이트
        update_barcode_status("🔄 제품 바코드 시뮬레이션 중...", "#FF9800")
        # 자동으로 제출
        submit_barcode()
        
        # 완료 확인 (시뮬레이션 후 잠시 대기)
        top.after(1500, check_and_close_if_complete)
    
    top = tk.Toplevel(root)
    top.title("바코드 리딩")
    top.geometry("500x450")
    top.resizable(False, False)
    
    # 제목
    title_label = tk.Label(top, text="바코드 리딩", font=("맑은 고딕", 14, "bold"))
    title_label.pack(pady=20)
    
    # 설명
    info_text = """바코드를 순차적으로 스캔하거나 입력하세요:

📋 바코드 스캔 순서:
1. 보관위치 바코드 (A-01-01 형식)
2. 제품 바코드 (88로 시작하는 코드)

✅ 스캔 완료 후 자동으로 다음 단계를 안내합니다.
✅ 두 바코드 모두 입력되면 창이 자동으로 닫힙니다.
✅ 바코드 리딩이 성공하면 창이 자동으로 닫힙니다.

실제 바코드 스캐너를 사용하거나 아래 버튼으로 시뮬레이션하세요.

💡 단축키: Ctrl+B로 언제든지 바코드 리딩 창을 열 수 있습니다."""
    
    info_label = tk.Label(top, text=info_text, font=("맑은 고딕", 10), justify=tk.LEFT)
    info_label.pack(pady=10)
    
    # 바코드 입력 프레임
    input_frame = tk.Frame(top)
    input_frame.pack(pady=20)
    
    # 현재 상태 표시
    status_label = tk.Label(input_frame, text="📋 바코드를 스캔하거나 입력하세요", 
                           font=("맑은 고딕", 10, "bold"), fg="#2196F3")
    status_label.pack(pady=5)
    
    tk.Label(input_frame, text="바코드:", font=("맑은 고딕", 10)).pack()
    barcode_entry = tk.Entry(input_frame, width=30, font=("맑은 고딕", 12))
    barcode_entry.pack(pady=5)
    barcode_entry.focus()
    
    # Enter 키로 제출
    barcode_entry.bind('<Return>', lambda e: submit_barcode())
    
    # 버튼 프레임
    button_frame = tk.Frame(top)
    button_frame.pack(pady=20)
    
    # 제출 버튼
    submit_btn = tk.Button(button_frame, text="확인", command=submit_barcode,
                           bg="#4CAF50", fg="white", font=("맑은 고딕", 10),
                           relief=tk.FLAT, bd=0, padx=20, pady=5)
    submit_btn.pack(side=tk.LEFT, padx=5)
    
    # 시뮬레이션 버튼들
    sim_frame = tk.Frame(top)
    sim_frame.pack(pady=15)
    
    # 시뮬레이션 제목
    sim_title = tk.Label(sim_frame, text="🧪 시뮬레이션 버튼", font=("맑은 고딕", 10, "bold"))
    sim_title.pack(pady=5)
    
    # 버튼들을 세로로 배치
    location_btn = tk.Button(sim_frame, text="1️⃣ 보관위치 바코드 시뮬레이션", command=simulate_location_barcode,
                             bg="#2196F3", fg="white", font=("맑은 고딕", 10),
                             relief=tk.FLAT, bd=0, padx=20, pady=8, width=25)
    location_btn.pack(pady=5)
    
    product_btn = tk.Button(sim_frame, text="2️⃣ 제품 바코드 시뮬레이션", command=simulate_product_barcode,
                            bg="#FF9800", fg="white", font=("맑은 고딕", 10),
                            relief=tk.FLAT, bd=0, padx=20, pady=8, width=25)
    product_btn.pack(pady=5)
    
    # 취소 버튼
    cancel_btn = tk.Button(button_frame, text="창 닫기", command=top.destroy,
                           bg="#f44336", fg="white", font=("맑은 고딕", 10),
                           relief=tk.FLAT, bd=0, padx=20, pady=5)
    cancel_btn.pack(side=tk.LEFT, padx=5)

tk.Button(location_frame, text="📷", command=open_barcode_input, width=3).pack(side=tk.LEFT)

# 제품 검색 필터링 함수
def filter_products():
    search_term = combo_code.get().upper()
    filtered_codes = [code for code in product_codes if search_term in code.upper()]
    combo_code['values'] = filtered_codes

# 초기 UI 설정
update_category_ui()

# 발행 내역 조회 함수 (검색 및 필터링 기능 포함)
def open_dashboard():
    """대시보드 창 열기"""
    try:
        # 현재 스크립트의 디렉토리에서 label_dashboard.py 실행
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dashboard_path = os.path.join(script_dir, "label_dashboard.py")
        
        if os.path.exists(dashboard_path):
            subprocess.Popen([sys.executable, dashboard_path])
        else:
            messagebox.showerror("오류", "label_dashboard.py 파일을 찾을 수 없습니다.")
    except Exception as e:
        messagebox.showerror("오류", f"대시보드 창을 열 수 없습니다: {str(e)}")

def open_location_visualizer():
    """관리품 위치 찾기 창 열기"""
    try:
        # 현재 스크립트의 디렉토리에서 location_visualizer.py 실행
        script_dir = os.path.dirname(os.path.abspath(__file__))
        visualizer_path = os.path.join(script_dir, "location_visualizer.py")
        
        if os.path.exists(visualizer_path):
            subprocess.Popen([sys.executable, visualizer_path])
        else:
            messagebox.showerror("오류", "location_visualizer.py 파일을 찾을 수 없습니다.")
    except Exception as e:
        messagebox.showerror("오류", f"관리품 위치 찾기 창을 열 수 없습니다: {str(e)}")

def open_zone_manager():
    """구역 관리 창 열기"""
    try:
        # 현재 스크립트의 디렉토리에서 zone_manager.py 실행
        script_dir = os.path.dirname(os.path.abspath(__file__))
        zone_manager_path = os.path.join(script_dir, "zone_manager.py")
        
        if os.path.exists(zone_manager_path):
            subprocess.Popen([sys.executable, zone_manager_path])
        else:
            messagebox.showerror("오류", "zone_manager.py 파일을 찾을 수 없습니다.")
    except Exception as e:
        messagebox.showerror("오류", f"구역 관리 창을 열 수 없습니다: {str(e)}")

def view_history():
    try:
        history_file = "barcode_label/issue_history.xlsx"
        if os.path.exists(history_file):
            df_history = pd.read_excel(history_file)
            
            # 새 창에 발행 내역 표시
            history_window = tk.Toplevel(root)
            history_window.title("발행 내역 조회 및 관리")
            history_window.geometry("1200x700")
            
            # 검색 및 필터링 프레임
            search_frame = tk.Frame(history_window)
            search_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # 검색 옵션
            tk.Label(search_frame, text="검색:", font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
            
            # 검색 필드 선택
            search_field_var = tk.StringVar(value="제품코드")
            search_field_combo = ttk.Combobox(search_frame, textvariable=search_field_var, 
                                            values=["구분", "제품코드", "제품명", "LOT", "유통기한", "보관위치"], 
                                            width=10, state="readonly")
            search_field_combo.pack(side=tk.LEFT, padx=5)
            
            # 검색어 입력
            search_var = tk.StringVar()
            search_entry = tk.Entry(search_frame, textvariable=search_var, width=20)
            search_entry.pack(side=tk.LEFT, padx=5)
            search_entry.bind('<Return>', lambda e: apply_filters())  # Enter 키로 검색
            
            # 날짜 필터 프레임
            date_filter_frame = tk.Frame(history_window)
            date_filter_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(date_filter_frame, text="날짜 범위:", font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
            
            # 시작일
            start_date_var = tk.StringVar()
            start_date_entry = tk.Entry(date_filter_frame, textvariable=start_date_var, width=12)
            start_date_entry.pack(side=tk.LEFT, padx=5)
            start_date_entry.insert(0, "YYYY-MM-DD")
            start_date_entry.bind('<FocusIn>', lambda e: start_date_entry.delete(0, tk.END) if start_date_entry.get() == "YYYY-MM-DD" else None)
            start_date_entry.bind('<FocusOut>', lambda e: start_date_entry.insert(0, "YYYY-MM-DD") if not start_date_entry.get() else None)
            tk.Label(date_filter_frame, text="~").pack(side=tk.LEFT, padx=2)
            
            # 종료일
            end_date_var = tk.StringVar()
            end_date_entry = tk.Entry(date_filter_frame, textvariable=end_date_var, width=12)
            end_date_entry.pack(side=tk.LEFT, padx=5)
            end_date_entry.insert(0, "YYYY-MM-DD")
            end_date_entry.bind('<FocusIn>', lambda e: end_date_entry.delete(0, tk.END) if end_date_entry.get() == "YYYY-MM-DD" else None)
            end_date_entry.bind('<FocusOut>', lambda e: end_date_entry.insert(0, "YYYY-MM-DD") if not end_date_entry.get() else None)
            
            # 정렬 옵션
            sort_frame = tk.Frame(history_window)
            sort_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(sort_frame, text="정렬:", font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
            
            sort_field_var = tk.StringVar(value="발행일시")
            sort_field_combo = ttk.Combobox(sort_frame, textvariable=sort_field_var, 
                                          values=["발행일시", "구분", "제품코드", "제품명", "LOT", "유통기한", "보관위치"], 
                                          width=10, state="readonly")
            sort_field_combo.pack(side=tk.LEFT, padx=5)
            
            sort_order_var = tk.StringVar(value="내림차순")
            sort_order_combo = ttk.Combobox(sort_frame, textvariable=sort_order_var, 
                                          values=["오름차순", "내림차순"], 
                                          width=8, state="readonly")
            sort_order_combo.pack(side=tk.LEFT, padx=5)
            
            # 버튼 프레임
            button_frame = tk.Frame(history_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # 검색 및 필터링 함수
            def apply_filters():
                try:
                    # 검색어 필터링
                    filtered_df = df_history.copy()
                    
                    search_term = search_var.get().strip()
                    if search_term:
                        search_field = search_field_var.get()
                        filtered_df = filtered_df[filtered_df[search_field].astype(str).str.contains(search_term, case=False, na=False)]
                    
                    # 날짜 필터링
                    start_date = start_date_var.get().strip()
                    end_date = end_date_var.get().strip()
                    
                    if start_date or end_date:
                        try:
                            filtered_df['발행일시'] = pd.to_datetime(filtered_df['발행일시'])
                            
                            if start_date:
                                start_dt = pd.to_datetime(start_date)
                                filtered_df = filtered_df[filtered_df['발행일시'] >= start_dt]
                            
                            if end_date:
                                end_dt = pd.to_datetime(end_date)
                                filtered_df = filtered_df[filtered_df['발행일시'] <= end_dt]
                        except:
                            pass
                    
                    # 정렬
                    sort_field = sort_field_var.get()
                    ascending = sort_order_var.get() == "오름차순"
                    
                    if sort_field == "발행일시":
                        filtered_df['발행일시'] = pd.to_datetime(filtered_df['발행일시'])
                    
                    if hasattr(filtered_df, 'sort_values'):
                        filtered_df = filtered_df.sort_values(by=sort_field, ascending=ascending)
                    
                    # 트리뷰 업데이트
                    for item in tree.get_children():
                        tree.delete(item)
                    
                    # 데이터 추가
                    if hasattr(filtered_df, 'iterrows'):
                        for idx, row in filtered_df.iterrows():
                            tree.insert('', 'end', values=list(row), tags=(str(idx),))
                    
                    # 결과 개수 표시
                    result_count = len(filtered_df)
                    total_count = len(df_history)
                    status_label.config(text=f"검색 결과: {result_count}개 / 전체: {total_count}개")
                    
                except Exception as e:
                    messagebox.showerror("필터링 오류", f"필터링 중 오류가 발생했습니다: {e}")
            
            # 초기화 함수
            def reset_filters():
                search_var.set("")
                start_date_var.set("")
                end_date_var.set("")
                sort_field_var.set("발행일시")
                sort_order_var.set("내림차순")
                apply_filters()
            
            # 검색 버튼
            search_btn = tk.Button(button_frame, text="🔍 검색", command=apply_filters,
                                  bg="#2196F3", fg="white", font=("맑은 고딕", 10),
                                  relief=tk.FLAT, bd=0, padx=15, pady=3)
            search_btn.pack(side=tk.LEFT, padx=5)
            
            # 초기화 버튼
            reset_btn = tk.Button(button_frame, text="🔄 초기화", command=reset_filters,
                                 bg="#FF9800", fg="white", font=("맑은 고딕", 10),
                                 relief=tk.FLAT, bd=0, padx=15, pady=3)
            reset_btn.pack(side=tk.LEFT, padx=5)
            
            # 엑셀 내보내기 버튼
            def export_to_excel():
                try:
                    export_filename = f"발행내역_내보내기_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    
                    # 현재 트리뷰에 표시된 데이터 수집
                    export_data = []
                    for item in tree.get_children():
                        values = tree.item(item)['values']
                        export_data.append(values)
                    
                    if export_data:
                        export_df = pd.DataFrame(export_data, columns=df_history.columns)
                        export_df.to_excel(export_filename, index=False)
                        messagebox.showinfo("내보내기 완료", f"데이터가 {export_filename}로 내보내기되었습니다.")
                    else:
                        messagebox.showwarning("내보내기 실패", "내보낼 데이터가 없습니다.")
                        
                except Exception as e:
                    messagebox.showerror("내보내기 오류", f"내보내기 실패: {e}")
            
            export_btn = tk.Button(button_frame, text="📊 엑셀 내보내기", command=export_to_excel,
                                  bg="#4CAF50", fg="white", font=("맑은 고딕", 10),
                                  relief=tk.FLAT, bd=0, padx=15, pady=3)
            export_btn.pack(side=tk.LEFT, padx=5)
            
            # 프레임 생성
            tree_frame = tk.Frame(history_window)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Treeview로 표시 (다중 선택 가능)
            tree = ttk.Treeview(tree_frame, columns=list(df_history.columns), show='headings', height=15, selectmode='extended')
            
            # 스크롤바 추가
            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # 컬럼 설정
            column_widths = {
                '발행일시': 150,
                '구분': 80,
                '제품코드': 100,
                '제품명': 200,
                'LOT': 100,
                '유통기한': 120,
                '보관위치': 100,
                '파일명': 200
            }
            
            for col in df_history.columns:
                tree.heading(col, text=col)
                tree.column(col, width=column_widths.get(col, 120))
            
            # 데이터 추가
            for idx, row in df_history.iterrows():
                tree.insert('', 'end', values=list(row), tags=(str(idx),))
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 상태 라벨 (검색 결과 개수 표시)
            status_label = tk.Label(history_window, text=f"전체: {len(df_history)}개", 
                                   relief=tk.SUNKEN, bd=1, padx=10, pady=5)
            status_label.pack(fill=tk.X, padx=10, pady=5)
            
            # 재발행 함수
            def reprint_selected():
                selected_item = tree.selection()
                if not selected_item:
                    messagebox.showwarning("경고", "재발행할 항목을 선택하세요.")
                    return
                
                # 선택된 항목의 데이터 가져오기
                item_values = tree.item(selected_item[0])['values']
                category = item_values[0]  # 구분
                product_code = item_values[1]  # 제품코드
                lot = item_values[3]           # LOT
                expiry = item_values[4]        # 유통기한
                location = item_values[5]      # 보관위치
                filename = item_values[6]      # 파일명
                
                # 파일 존재 확인 (labeljpg 폴더 내에서 확인)
                labeljpg_dir = "labeljpg"
                file_path = os.path.join(labeljpg_dir, filename)
                
                if os.path.exists(file_path):
                    try:
                        # 파일을 다시 생성하여 새로운 UI 적용
                        create_label(product_code, lot, expiry, location, category)
                        messagebox.showinfo("재발행 완료", f"라벨을 새로 생성했습니다.\n\n구분: {category}\n제품: {product_code}\nLOT: {lot}\n유통기한: {expiry}\n보관위치: {location}\n\n미리보기 창에서 확인 후 인쇄하세요.")
                    except Exception as e:
                        messagebox.showerror("재발행 오류", f"라벨 생성 실패: {e}")
                else:
                    # 파일이 없으면 새로 생성
                    try:
                        create_label(product_code, lot, expiry, location, category)
                        messagebox.showinfo("재발행 완료", f"라벨을 새로 생성했습니다.\n\n구분: {category}\n제품: {product_code}\nLOT: {lot}\n유통기한: {expiry}\n보관위치: {location}\n\n미리보기 창에서 확인 후 인쇄하세요.")
                    except Exception as e:
                        messagebox.showerror("재발행 오류", f"라벨 생성 실패: {e}")
            
            # 삭제 함수 (다중 선택 지원)
            def delete_selected():
                selected_items = tree.selection()
                if not selected_items:
                    messagebox.showwarning("경고", "삭제할 항목을 선택하세요.")
                    return
                
                # 다중 선택된 항목들의 정보 수집
                selected_data = []
                for item in selected_items:
                    item_values = tree.item(item)['values']
                    selected_data.append({
                        'item_id': item,
                        'category': item_values[0],
                        'product_code': item_values[1],
                        'product_name': item_values[2],
                        'lot': item_values[3],
                        'expiry': item_values[4],
                        'location': item_values[5],
                        'filename': item_values[6]
                    })
                
                # 삭제 확인 메시지 (다중 선택 시)
                if len(selected_items) == 1:
                    data = selected_data[0]
                    confirm_msg = f"다음 항목을 삭제하시겠습니까?\n\n구분: {data['category']}\n제품코드: {data['product_code']}\n제품명: {data['product_name']}\nLOT: {data['lot']}\n유통기한: {data['expiry']}\n보관위치: {data['location']}"
                else:
                    confirm_msg = f"선택된 {len(selected_items)}개 항목을 모두 삭제하시겠습니까?\n\n"
                    for i, data in enumerate(selected_data[:3], 1):  # 처음 3개만 표시
                        confirm_msg += f"{i}. {data['category']} - {data['product_code']} - {data['product_name']} (LOT: {data['lot']})\n"
                    if len(selected_data) > 3:
                        confirm_msg += f"... 외 {len(selected_data) - 3}개 항목"
                
                if not messagebox.askyesno("삭제 확인", confirm_msg):
                    return
                
                try:
                    # 엑셀 파일에서 해당 행들 삭제
                    df_history = pd.read_excel(history_file)
                    deleted_count = 0
                    file_deleted_count = 0
                    
                    # 선택된 항목들을 역순으로 삭제 (인덱스 변경 방지)
                    for data in selected_data:
                        # 선택된 항목과 일치하는 행 찾기
                        mask = (df_history['구분'] == data['category']) & \
                               (df_history['제품코드'] == data['product_code']) & \
                               (df_history['LOT'] == data['lot']) & \
                               (df_history['유통기한'] == data['expiry']) & \
                               (df_history['보관위치'] == data['location'])
                        
                        # 해당 행 삭제
                        df_history = df_history[~mask]
                        deleted_count += 1
                        
                        # 트리뷰에서도 삭제
                        tree.delete(data['item_id'])
                        
                        # 파일도 삭제 (선택사항) - labeljpg 폴더 내에서 확인
                        labeljpg_dir = "labeljpg"
                        file_path = os.path.join(labeljpg_dir, data['filename'])
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                file_deleted_count += 1
                            except:
                                pass
                    
                    # 파일 저장
                    if hasattr(df_history, 'to_excel'):
                        df_history.to_excel(history_file, index=False)
                    
                    # 완료 메시지
                    if len(selected_items) == 1:
                        messagebox.showinfo("삭제 완료", f"선택한 항목이 삭제되었습니다.\n파일도 함께 삭제되었습니다." if file_deleted_count > 0 else "선택한 항목이 삭제되었습니다.")
                    else:
                        messagebox.showinfo("삭제 완료", f"선택된 {deleted_count}개 항목이 삭제되었습니다.\n파일 {file_deleted_count}개도 함께 삭제되었습니다.")
                    
                except Exception as e:
                    messagebox.showerror("삭제 오류", f"삭제 실패: {e}")
            
            # 버튼 프레임
            button_frame = tk.Frame(history_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # 재발행 버튼
            reprint_btn = tk.Button(button_frame, text="선택 항목 재발행", command=reprint_selected, 
                                   bg="#4CAF50", fg="white", font=("맑은 고딕", 11), 
                                   relief=tk.FLAT, bd=0, padx=15, pady=5)
            reprint_btn.pack(side=tk.LEFT, padx=5)
            
            # 삭제 버튼
            delete_btn = tk.Button(button_frame, text="선택 항목 삭제 (다중선택)", command=delete_selected, 
                                  bg="#f44336", fg="white", font=("맑은 고딕", 11), 
                                  relief=tk.FLAT, bd=0, padx=15, pady=5)
            delete_btn.pack(side=tk.LEFT, padx=5)
            
            # 닫기 버튼
            close_btn = tk.Button(button_frame, text="닫기", command=history_window.destroy)
            close_btn.pack(side=tk.RIGHT, padx=5)
            
            # 선택된 항목 정보 표시 (다중 선택 지원)
            def show_selection_info(event):
                selected_items = tree.selection()
                if selected_items:
                    if len(selected_items) == 1:
                        # 단일 선택
                        item_values = tree.item(selected_items[0])['values']
                        info_text = f"선택된 항목:\n구분: {item_values[0]}\n제품코드: {item_values[1]}\n제품명: {item_values[2]}\nLOT: {item_values[3]}\n유통기한: {item_values[4]}\n보관위치: {item_values[5]}"
                    else:
                        # 다중 선택
                        info_text = f"선택된 항목: {len(selected_items)}개\n"
                        for i, item in enumerate(selected_items[:3], 1):  # 처음 3개만 표시
                            item_values = tree.item(item)['values']
                            info_text += f"{i}. {item_values[0]} - {item_values[1]} - {item_values[2]} (LOT: {item_values[3]})\n"
                        if len(selected_items) > 3:
                            info_text += f"... 외 {len(selected_items) - 3}개 항목"
                    info_label.config(text=info_text)
                else:
                    info_label.config(text="항목을 선택하세요 (Ctrl+클릭으로 다중 선택 가능)")
            
            tree.bind('<<TreeviewSelect>>', show_selection_info)
            
            # 선택 정보 표시 라벨
            info_label = tk.Label(history_window, text="항목을 선택하세요 (Ctrl+클릭으로 다중 선택 가능)", 
                                 relief=tk.SUNKEN, bd=1, padx=10, pady=5)
            info_label.pack(fill=tk.X, padx=10, pady=5)
            
            # 초기 필터 적용 (최신순으로 정렬)
            apply_filters()
            
        else:
            messagebox.showinfo("알림", "발행 내역이 없습니다.")
            
    except Exception as e:
        messagebox.showerror("오류", f"발행 내역 조회 중 오류: {e}")

# 버튼 프레임
button_frame = tk.Frame(root)
button_frame.pack(pady=20)

tk.Button(button_frame, text="라벨 생성 및 인쇄", command=on_submit).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="📷 바코드 리딩", command=open_barcode_input, 
          bg="#FF9800", fg="white", font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=5)

# 두 번째 버튼 프레임 (관리 도구들)
button_frame2 = tk.Frame(root)
button_frame2.pack(pady=10)

tk.Button(button_frame2, text="📊 대시보드", command=open_dashboard, 
          bg="#2196F3", fg="white", font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame2, text="🧐 관리품 위치 찾기", command=open_location_visualizer, 
          bg="#4CAF50", fg="white", font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame2, text="📋 발행 내역", command=view_history, 
          bg="#9C27B0", fg="white", font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame2, text="⚙️ 구역 관리", command=open_zone_manager, 
          bg="#607D8B", fg="white", font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=5)

root.mainloop()
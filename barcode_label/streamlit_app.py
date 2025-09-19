#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
바코드 라벨 관리 시스템 - Streamlit 버전
"""

import streamlit as st
import os
import sys
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import json
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import io
import base64
import subprocess

# UTF-8 인코딩 설정
import locale
try:
    locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Korean_Korea.utf8')
    except:
        pass

# pandas 옵션 설정
pd.set_option('display.encoding', 'utf-8')

def get_korean_font(size):
    """한글을 지원하는 폰트를 찾아서 반환 (Streamlit Cloud 최적화)"""
    import platform
    import urllib.request
    import tempfile

    # 현재 파일의 디렉토리 경로
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1순위: 앱에 포함된 폰트 파일 사용
    font_path = os.path.join(current_dir, "fonts", "NotoSansKR-Regular.ttf")
    print(f"1순위 폰트 경로 확인: {font_path}")

    if os.path.exists(font_path):
        try:
            print(f"앱에 포함된 폰트를 사용합니다: {font_path}")
            return ImageFont.truetype(font_path, size)
        except Exception as e:
            print(f"앱 포함 폰트 로드 실패: {e}")

    # 2순위: Streamlit Cloud 환경에서 웹 폰트 다운로드 (비상용)
    if os.environ.get('STREAMLIT_CLOUD', False):
        font_url = "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR-Regular.ttf"
        try:
            # 임시 디렉토리에 폰트 저장
            font_filename = os.path.basename(font_url)
            temp_font_path = os.path.join(tempfile.gettempdir(), font_filename)
            
            if not os.path.exists(temp_font_path):
                print(f"웹 폰트를 다운로드합니다... ({font_url})")
                urllib.request.urlretrieve(font_url, temp_font_path)
            
            print(f"다운로드한 웹 폰트를 사용합니다: {temp_font_path}")
            return ImageFont.truetype(temp_font_path, size)
        except Exception as e:
            print(f"웹 폰트 다운로드 또는 로드 실패: {e}")

    # 3순위: 로컬 환경(Windows, macOS 등)에서 시스템 폰트 탐색
    system = platform.system()
    if system == "Windows":
        font_name = "malgun.ttf"  # 맑은 고딕
    elif system == "Darwin": # macOS
        font_name = "AppleGothic.ttf"
    elif system == "Linux":
        # Linux에서는 다양한 경로를 확인해야 할 수 있음
        font_name = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    
    try:
        return ImageFont.truetype(font_name, size)
    except Exception:
        pass # 시스템 폰트 못찾으면 다음으로 넘어감

    # 최후의 수단: 기본 폰트 사용 (한글 깨짐)
    print("경고: 한글 지원 폰트를 찾지 못했습니다. 기본 폰트를 사용합니다.")
    return ImageFont.load_default()

def safe_text(text):
    """한글 텍스트를 안전하게 처리"""
    if not text:
        return ""
    
    # 모든 환경에서 한글을 그대로 유지
    return str(text)

def draw_korean_text_with_fallback(draw, position, text, font, fill="black"):
    """한글 텍스트를 그리되, 폰트가 없으면 대체 방법 사용"""
    if not text:
        return
        
    print(f"텍스트 그리기 시도: '{text}' (폰트: {font})")
    
    try:
        # 먼저 지정된 폰트로 시도
        if font:
            draw.text(position, text, fill=fill, font=font)
            print(f"폰트로 텍스트 그리기 성공: {text}")
            return
    except Exception as e:
        print(f"한글 텍스트 그리기 실패 (폰트: {font}): {e}")
    
    # 폰트가 없으면 기본 폰트로 시도
    try:
        default_font = ImageFont.load_default()
        draw.text(position, text, fill=fill, font=default_font)
        print(f"기본 폰트로 텍스트 그리기 성공: {text}")
        return
    except Exception as e2:
        print(f"기본 폰트로도 실패: {e2}")
    
    # 그래도 실패하면 텍스트를 그대로 시도 (마지막 시도)
    try:
        draw.text(position, text, fill=fill)
        print(f"폰트 없이 텍스트 그리기 성공: {text}")
        return
    except Exception as e3:
        print(f"모든 텍스트 그리기 시도 실패: {text} - {e3}")
        # 최후의 수단: 텍스트를 이미지로 변환해서 붙이기
        try:
            text_img = create_text_image(text, font, fill)
            if text_img:
                label.paste(text_img, position, text_img)
                print(f"이미지로 텍스트 그리기 성공: {text}")
        except Exception as e4:
            print(f"이미지로도 텍스트 그리기 실패: {text} - {e4}")

def create_text_image(text, font, fill="black", background="white"):
    """텍스트를 이미지로 변환하여 반환"""
    try:
        # 텍스트 크기 계산
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 이미지 생성
        img = Image.new('RGB', (text_width + 10, text_height + 10), background)
        draw = ImageDraw.Draw(img)
        
        # 텍스트 그리기
        draw.text((5, 5), text, fill=fill, font=font)
        
        return img
    except Exception as e:
        print(f"텍스트 이미지 생성 실패: {e}")
        return None

def draw_korean_text_as_image(draw, position, text, font, fill="black", background="white"):
    """한글 텍스트를 이미지로 변환하여 그리기"""
    try:
        # 텍스트를 이미지로 변환
        text_img = create_text_image(text, font, fill, background)
        if text_img:
            # 이미지를 지정된 위치에 붙이기
            draw._image.paste(text_img, position, text_img)
        else:
            # 이미지 생성 실패 시 기본 방법 사용
            draw_korean_text_with_fallback(draw, position, text, font, fill)
    except Exception as e:
        print(f"이미지 텍스트 그리기 실패: {e}")
        # 실패 시 기본 방법 사용
        draw_korean_text_with_fallback(draw, position, text, font, fill)

def get_mysql_connection():
    """MySQL 연결 반환"""
    if not MYSQL_AVAILABLE or not mysql_config:
        return None
    
    try:
        import pymysql
        connection = pymysql.connect(
            host=mysql_config['host'],
            user=mysql_config['user'],
            password=mysql_config['password'],
            database=mysql_config['database'],
            port=mysql_config['port'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"MySQL 연결 실패: {e}")
        return None

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 기존 모듈들 import
try:
    from google_sheets_manager import sheets_manager
    GOOGLE_SERVICES_AVAILABLE = True
except ImportError as e:
    GOOGLE_SERVICES_AVAILABLE = False
    st.warning(f"구글 스프레드시트 연동 모듈을 불러올 수 없습니다: {e}")

# MySQL 연결 설정
MYSQL_AVAILABLE = False
mysql_config = None

try:
    # Streamlit secrets에서 MySQL 설정 가져오기
    if 'mysql' in st.secrets:
        mysql_config = {
            'host': st.secrets['mysql']['host'],
            'user': st.secrets['mysql']['user'],
            'password': st.secrets['mysql']['password'],
            'database': st.secrets['mysql']['database'],
            'port': st.secrets['mysql'].get('port', 3306)
        }
        MYSQL_AVAILABLE = True
        print("MySQL 설정이 로드되었습니다.")
    else:
        print("MySQL 설정이 없습니다. secrets.toml 파일을 확인하세요.")
except Exception as e:
    print(f"MySQL 설정 로드 실패: {e}")
    MYSQL_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="바코드 라벨 관리 시스템",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 전역 변수 초기화
if 'products' not in st.session_state:
    st.session_state.products = {}
if 'zone_config' not in st.session_state:
    st.session_state.zone_config = {}

def load_products():
    """제품 정보 로드"""
    try:
        products_file = os.path.join(current_dir, 'products.xlsx')
        if os.path.exists(products_file):
            df = pd.read_excel(products_file, engine='openpyxl')
            products_dict = dict(zip(df['제품코드'], df['제품명']))
            st.session_state.products = products_dict
            return products_dict
    except Exception as e:
        st.error(f"제품 정보 로드 실패: {e}")
    return {}

def load_zone_config():
    """구역 설정 로드"""
    try:
        config_file = os.path.join(current_dir, 'zone_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                st.session_state.zone_config = config
                return config
    except Exception as e:
        st.error(f"구역 설정 로드 실패: {e}")
    return {}

def init_serial_database():
    """일련번호 데이터베이스 초기화"""
    try:
        db_path = os.path.join(current_dir, 'label_serial.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS label_info (
                serial_number INTEGER PRIMARY KEY,
                product_code TEXT,
                lot TEXT,
                expiry TEXT,
                version TEXT,
                location TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"데이터베이스 초기화 실패: {e}")
        return False

def get_next_serial_number():
    """다음 일련번호 생성"""
    try:
        db_path = os.path.join(current_dir, 'label_serial.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT MAX(serial_number) FROM label_info')
        result = cursor.fetchone()
        next_serial = (result[0] or 0) + 1
        
        conn.close()
        return next_serial
    except Exception as e:
        st.error(f"일련번호 생성 실패: {e}")
        return 1

def save_label_info(product_code, lot, expiry, version, location, category):
    """라벨 정보 저장"""
    try:
        serial_number = get_next_serial_number()
        db_path = os.path.join(current_dir, 'label_serial.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO label_info 
            (serial_number, product_code, lot, expiry, version, location, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (serial_number, product_code, lot, expiry, version, location, category))
        
        conn.commit()
        conn.close()
        return serial_number
    except Exception as e:
        st.error(f"라벨 정보 저장 실패: {e}")
        return None

def create_barcode_image(serial_number, product_code, lot, expiry, version, location, category):
    """바코드 이미지 생성"""
    try:
        # 제품명 조회
        product_name = st.session_state.products.get(product_code, "Unknown Product")
        
        # 바코드 생성
        barcode_class = barcode.get_barcode_class('code128')
        barcode_image = barcode_class(str(serial_number), writer=ImageWriter())
        barcode_img = barcode_image.render({'write_text': False})
        
        # 라벨 크기 설정 (30mm x 20mm, 4배 확대된 해상도)
        LABEL_WIDTH = 480  # 30mm * 4 * 4 = 480px
        LABEL_HEIGHT = 320  # 20mm * 4 * 4 = 320px
        
        # 라벨 이미지 생성
        label = Image.new('RGB', (LABEL_WIDTH, LABEL_HEIGHT), 'white')
        draw = ImageDraw.Draw(label)
        
        # 한글 폰트 설정 (30x20 라벨에 맞는 크기)
        print("한글 폰트 로딩 시작...")
        try:
            font_large = get_korean_font(20)    # 제품명용
            font_medium = get_korean_font(16)   # 구분용
            font_small = get_korean_font(14)    # 상세정보용
            font_tiny = get_korean_font(12)     # 바코드 텍스트용
            
            print(f"폰트 로딩 결과:")
            print(f"  font_large: {font_large}")
            print(f"  font_medium: {font_medium}")
            print(f"  font_small: {font_small}")
            print(f"  font_tiny: {font_tiny}")
            
            # 폰트가 None인 경우 기본 폰트 사용
            if font_large is None:
                print("font_large가 None이므로 기본 폰트 사용")
                font_large = ImageFont.load_default()
            if font_medium is None:
                print("font_medium이 None이므로 기본 폰트 사용")
                font_medium = ImageFont.load_default()
            if font_small is None:
                print("font_small이 None이므로 기본 폰트 사용")
                font_small = ImageFont.load_default()
            if font_tiny is None:
                print("font_tiny가 None이므로 기본 폰트 사용")
                font_tiny = ImageFont.load_default()
        except Exception as e:
            print(f"폰트 로딩 오류: {e}")
            import traceback
            traceback.print_exc()
            # 모든 폰트를 기본 폰트로 설정
            font_large = font_medium = font_small = font_tiny = ImageFont.load_default()
        
        # 폰트 로드 상태 확인 (디버그용)
        if hasattr(font_large, 'path'):
            print(f"폰트 로드 성공: {font_large.path}")
        else:
            print("기본 폰트 사용 중 (한글 지원 제한적)")
        
        # 텍스트 줄바꿈 함수 (30x20 라벨에 최적화)
        def draw_multiline_text(draw, text, position, font, max_width, fill="black", max_lines=2):
            """텍스트를 여러 줄로 나누어 그리기 (30x20 라벨에 최적화)"""
            x, y = position
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # 단어가 너무 길면 강제로 줄바꿈 (15자 단위)
                        if len(word) > 15:
                            lines.append(word[:15])
                            current_line = [word[15:]]
                        else:
                            lines.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # 최대 줄 수 제한 (30x20 라벨에 맞게 2줄)
            if len(lines) > max_lines:
                lines = lines[:max_lines-1]
                lines.append("...")  # 잘린 부분 표시
            
            for line in lines:
                draw_korean_text_with_fallback(draw, (x, y), line, font, fill)
                y += font.size + 2
            
            return y
        
        # 텍스트 정보 추가 (30x20 라벨에 최적화된 레이아웃)
        y_pos = 10
        margin = 15
        
        # 제품명 (여러 줄 지원, 최대 2줄)
        product_text = f"제품명: {product_name}"
        y_pos = draw_multiline_text(draw, product_text, (margin, y_pos), font_large, LABEL_WIDTH - 2*margin, max_lines=2)
        y_pos += 20
        
        # 구분
        draw_korean_text_with_fallback(draw, (margin, y_pos), f"구분: {category}", font_medium)
        y_pos += 20
        
        # LOT, 유통기한, 버전 (한 줄에 압축)
        lot_expiry_version_text = f"LOT: {lot}    유통기한: {expiry}    버전: {version}"
        draw_korean_text_with_fallback(draw, (margin, y_pos), lot_expiry_version_text, font_small)
        y_pos += 20
        
        # 보관위치
        draw_korean_text_with_fallback(draw, (margin, y_pos), f"보관위치: {location}", font_small)
        
        # 바코드 이미지 리사이즈 및 배치 (하단에 고정)
        barcode_height = 100
        barcode_width = LABEL_WIDTH - 30
        barcode_img = barcode_img.resize((barcode_width, barcode_height), Image.Resampling.LANCZOS)
        barcode_x = 4
        barcode_y = LABEL_HEIGHT - barcode_height - 60
        label.paste(barcode_img, (barcode_x, barcode_y))
        
        # 바코드 데이터 텍스트 (하단 중앙)
        barcode_text = f"{product_code}-{lot}-{expiry}-{version}"
        text_bbox = draw.textbbox((0, 0), barcode_text, font=font_tiny)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (LABEL_WIDTH - text_width) // 2
        draw.text((text_x, LABEL_HEIGHT - 35), barcode_text, fill="black", font=font_tiny)
        
        return label, serial_number
        
    except Exception as e:
        st.error(f"바코드 이미지 생성 실패: {e}")
        return None, None

def print_label_image(label_image, filename):
    """라벨 이미지 인쇄"""
    try:
        import platform
        import tempfile
        import time
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = temp_file.name
            label_image.save(temp_path, 'PNG')
        
        print(f"인쇄 시도: {temp_path}")  # 디버그용
        
        # 운영체제별 인쇄 명령 실행
        if platform.system() == "Windows":
            # Windows: 여러 방법 시도
            try:
                # 방법 1: os.startfile with print
                os.startfile(temp_path, "print")
                print("os.startfile(print) 성공")
                return True
            except Exception as e1:
                print(f"os.startfile(print) 실패: {e1}")
                try:
                    # 방법 2: 기본 프로그램으로 열기
                    os.startfile(temp_path)
                    print("os.startfile() 성공 - 사용자가 Ctrl+P로 인쇄해야 함")
                    return True
                except Exception as e2:
                    print(f"os.startfile() 실패: {e2}")
                    try:
                        # 방법 3: subprocess 사용
                        subprocess.run(['cmd', '/c', 'start', '/p', temp_path], check=True)
                        print("subprocess 성공")
                        return True
                    except Exception as e3:
                        print(f"subprocess 실패: {e3}")
                        return False
        elif platform.system() == "Darwin":  # macOS
            result = subprocess.run(["lp", temp_path], capture_output=True, text=True)
            if result.returncode == 0:
                print("macOS lp 성공")
                return True
            else:
                print(f"macOS lp 실패: {result.stderr}")
                return False
        elif platform.system() == "Linux":
            try:
                result = subprocess.run(["lp", temp_path], capture_output=True, text=True)
                if result.returncode == 0:
                    print("Linux lp 성공")
                    return True
                else:
                    raise FileNotFoundError
            except FileNotFoundError:
                result = subprocess.run(["lpr", temp_path], capture_output=True, text=True)
                if result.returncode == 0:
                    print("Linux lpr 성공")
                    return True
                else:
                    print(f"Linux lpr 실패: {result.stderr}")
                    return False
        else:
            # 기타 OS
            os.startfile(temp_path)
            print("기타 OS - 기본 프로그램으로 열기")
            return True
        
    except Exception as e:
        print(f"인쇄 함수 전체 실패: {e}")
        return False
    finally:
        # 3초 후 임시 파일 삭제
        import threading
        def cleanup_temp_file():
            time.sleep(3)
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    print(f"임시 파일 삭제: {temp_path}")
            except Exception as e:
                print(f"임시 파일 삭제 실패: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_temp_file)
        cleanup_thread.daemon = True
        cleanup_thread.start()

def save_issue_history(product_code, lot, expiry, version, location, filename, category, serial_number):
    """발행 내역 저장"""
    try:
        # 폐기일자 계산 (유통기한 + 1년)
        disposal_date = ''
        if expiry and expiry != 'N/A' and expiry != '':
            try:
                from datetime import datetime, timedelta
                # 유통기한을 날짜로 변환
                if isinstance(expiry, str):
                    expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                else:
                    expiry_date = expiry
                
                # 1년 추가
                disposal_date = (expiry_date + timedelta(days=365)).strftime('%Y-%m-%d')
            except Exception as e:
                print(f"폐기일자 계산 오류: {e}")
                disposal_date = ''
        
        # 발행 내역 데이터
        issue_data = {
            '일련번호': serial_number,
            '구분': category,
            '제품코드': product_code,
            '제품명': st.session_state.products.get(product_code, "Unknown Product"),
            'LOT': lot,
            '유통기한': expiry,
            '폐기일자': disposal_date,  # 유통기한 + 1년 자동 계산
            '보관위치': location,
            '버전': version,
            '발행일시': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Excel 파일에 저장
        excel_file = os.path.join(current_dir, 'issue_history.xlsx')
        
        # 컬럼 순서 정의 (구글 스프레드시트와 동일)
        column_order = [
            '일련번호', '구분', '제품코드', '제품명', 'LOT', 
            '유통기한', '폐기일자', '보관위치', '버전', '발행일시'
        ]
        
        if os.path.exists(excel_file):
            df = pd.read_excel(excel_file, engine='openpyxl')
        else:
            df = pd.DataFrame(columns=column_order)
        
        # 새 데이터 추가
        new_row = pd.DataFrame([issue_data])
        df = pd.concat([df, new_row], ignore_index=True)
        
        # 컬럼 순서에 맞게 정렬
        df = df.reindex(columns=column_order)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        
        # 구글 스프레드시트에 저장 (가능한 경우)
        if GOOGLE_SERVICES_AVAILABLE:
            try:
                print(f"Google Sheets 저장 시도: {issue_data}")
                # 개별 행을 스프레드시트에 추가
                result = sheets_manager.add_row_to_sheets(issue_data)
                print(f"Google Sheets 저장 결과: {result}")
                
                if result:
                    st.success("구글 스프레드시트에 저장되었습니다!")
                else:
                    st.warning("구글 스프레드시트 저장에 실패했습니다. 로그를 확인하세요.")
            except Exception as e:
                print(f"Google Sheets 저장 예외: {e}")
                import traceback
                traceback.print_exc()
                st.warning(f"구글 스프레드시트 저장 실패: {e}")
        else:
            print("Google Sheets 서비스가 사용 불가능합니다.")
        
        return True
        
    except Exception as e:
        st.error(f"발행 내역 저장 실패: {e}")
        return False

def main():
    """메인 애플리케이션"""
    
    # 헤더
    st.markdown('<h1 class="main-header">🏷️ 바코드 라벨 관리 시스템</h1>', unsafe_allow_html=True)
    
    # 초기화
    if not init_serial_database():
        st.error("데이터베이스 초기화에 실패했습니다.")
        return
    
    # 데이터 로드
    products = load_products()
    zone_config = load_zone_config()
    
    # 사이드바
    with st.sidebar:
        st.markdown("## 📋 메뉴")
        menu_option = st.selectbox(
            "기능 선택",
            ["🏷️ 라벨 생성", "📊 발행 내역 조회", "⚙️ 설정", "📈 대시보드"]
        )
    
    # 메인 컨텐츠
    if menu_option == "🏷️ 라벨 생성":
        show_label_creation_page(products, zone_config)
    elif menu_option == "📊 발행 내역 조회":
        show_history_page()
    elif menu_option == "⚙️ 설정":
        show_settings_page()
    elif menu_option == "📈 대시보드":
        show_dashboard_page()

def show_label_creation_page(products, zone_config):
    """라벨 생성 페이지"""
    st.markdown('<h2 class="section-header">🏷️ 바코드 라벨 생성</h2>', unsafe_allow_html=True)
    
    # 입력 폼
    col1, col2 = st.columns(2)
    
    with col1:
        # 제품코드 선택
        product_codes = list(products.keys()) if products else []
        if product_codes:
            selected_code = st.selectbox("제품코드", product_codes)
            product_name = products.get(selected_code, "")
            st.info(f"제품명: {product_name}")
        else:
            selected_code = st.text_input("제품코드", placeholder="예: BA00034")
            product_name = "Unknown Product"
        
        # 구분 선택
        category = st.selectbox(
            "구분",
            ["관리품", "표준품", "벌크표준", "샘플재고"]
        )
        
        # 보관위치 선택
        location_options = []
        if zone_config and 'zones' in zone_config:
            for zone_key, zone_data in zone_config['zones'].items():
                zone_name = zone_data['name']
                sections = zone_data.get('sections', {})
                rows = sections.get('rows', 5)
                columns = sections.get('columns', 3)
                
                for row in range(1, rows + 1):
                    for col in range(1, columns + 1):
                        location_options.append(f"{zone_key}-{row:02d}-{col:02d}")
        
        if location_options:
            location = st.selectbox("보관위치", location_options)
        else:
            location = st.text_input("보관위치", placeholder="예: A-03-01")
    
    with col2:
        # LOT, 유통기한, 버전 입력
        if category in ["관리품", "표준품", "벌크표준"]:
            lot = st.text_input("LOT 번호", placeholder="예: L2024001")
            expiry = st.date_input("유통기한", value=datetime.now().date() + timedelta(days=365))
            version = st.text_input("버전", placeholder="예: V1.0")
        else:
            lot = "SAMPLE"
            expiry = datetime.now().date()
            version = "N/A"
            st.info("샘플재고는 기본값이 설정됩니다.")
    
    # 라벨 생성 버튼
    if st.button("🏷️ 라벨 생성", type="primary", use_container_width=True):
        if not selected_code or not location:
            st.error("제품코드와 보관위치를 입력해주세요.")
            return
        
        if category in ["관리품", "표준품", "벌크표준"] and (not lot or not version):
            st.error("LOT 번호와 버전을 입력해주세요.")
            return
        
        # 라벨 생성
        with st.spinner("라벨을 생성하는 중..."):
            # 일련번호 생성 및 저장
            serial_number = save_label_info(selected_code, lot, str(expiry), version, location, category)
            
            if serial_number:
                # 바코드 이미지 생성
                label_image, _ = create_barcode_image(
                    serial_number, selected_code, lot, str(expiry), version, location, category
                )
                
                if label_image:
                    # 이미지 표시
                    st.success(f"라벨이 성공적으로 생성되었습니다! (일련번호: {serial_number})")
                    
                    # 이미지를 바이트로 변환
                    img_buffer = io.BytesIO()
                    label_image.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    
                    # 이미지 표시
                    st.image(label_image, caption=f"바코드 라벨 - {selected_code}-{location}", use_container_width=True)
                    
                    # 라벨 이미지를 세션 상태에 저장
                    st.session_state.current_label_image = label_image
                    st.session_state.current_filename = f"{selected_code}-{location}.png"
                    
                    # 다운로드 및 인쇄 버튼
                    col_download, col_print = st.columns(2)
                    
                    with col_download:
                        st.download_button(
                            label="📥 라벨 이미지 다운로드",
                            data=img_buffer.getvalue(),
                            file_name=f"{selected_code}-{location}.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    
                    with col_print:
                        # 인쇄용 파일 자동 생성 및 다운로드 제공
                        st.write("---")
                        st.write("**🖨️ 라벨 인쇄**")
                        
                        # 인쇄용 파일 자동 생성
                        print_filename = f"PRINT_{selected_code}-{location}.png"
                        print_path = os.path.join(current_dir, print_filename)
                        
                        try:
                            # 인쇄용 파일 생성
                            label_image.save(print_path, 'PNG')
                            
                            # 인쇄용 파일 다운로드 버튼
                            with open(print_path, "rb") as file:
                                st.download_button(
                                    label="🖨️ 인쇄용 파일 다운로드",
                                    data=file.read(),
                                    file_name=print_filename,
                                    mime="image/png",
                                    use_container_width=True,
                                    help="다운로드 후 파일을 열어서 Ctrl+P로 인쇄하세요"
                                )
                            
                            # 파일 열기 버튼 (Windows에서만)
                            if st.button("📂 파일 열기 (인쇄용)", use_container_width=True, key=f"open_{serial_number}"):
                                try:
                                    os.startfile(print_path)
                                    st.success("✅ 파일이 열렸습니다! Ctrl+P로 인쇄하세요.")
                                except Exception as e:
                                    st.error(f"❌ 파일 열기 실패: {e}")
                            
                            st.info(f"💡 인쇄용 파일이 생성되었습니다: `{print_path}`")
                            
                        except Exception as e:
                            st.error(f"❌ 인쇄용 파일 생성 실패: {e}")
                        
                        # 사용법 안내
                        st.write("---")
                        st.write("**📋 인쇄 방법:**")
                        st.write("1. 위의 '인쇄용 파일 다운로드' 버튼 클릭")
                        st.write("2. 다운로드된 파일을 더블클릭하여 열기")
                        st.write("3. Ctrl+P를 눌러서 인쇄 대화상자 열기")
                        st.write("4. 프린터 선택 후 인쇄")
                    
                    # 발행 내역 저장
                    save_issue_history(selected_code, lot, str(expiry), version, location, f"{selected_code}-{location}.png", category, serial_number)

def show_history_page():
    """발행 내역 조회 페이지"""
    st.markdown('<h2 class="section-header">📊 발행 내역 조회</h2>', unsafe_allow_html=True)
    
    # 발행 내역 로드
    excel_file = os.path.join(current_dir, 'issue_history.xlsx')
    
    if os.path.exists(excel_file):
        try:
            df = pd.read_excel(excel_file, engine='openpyxl')
            
            if not df.empty:
                # 필터링 옵션
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    categories = ['전체'] + list(df['구분'].unique())
                    selected_category = st.selectbox("구분 필터", categories)
                
                with col2:
                    locations = ['전체'] + list(df['보관위치'].unique())
                    selected_location = st.selectbox("보관위치 필터", locations)
                
                with col3:
                    date_range = st.date_input("날짜 범위", value=[], key="date_filter")
                
                # 데이터 필터링
                filtered_df = df.copy()
                
                if selected_category != '전체':
                    filtered_df = filtered_df[filtered_df['구분'] == selected_category]
                
                if selected_location != '전체':
                    filtered_df = filtered_df[filtered_df['보관위치'] == selected_location]
                
                # 데이터 표시
                st.dataframe(filtered_df, use_container_width=True)
                
                # 통계 정보
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("총 발행 수", len(filtered_df))
                
                with col2:
                    st.metric("관리품", len(filtered_df[filtered_df['구분'] == '관리품']))
                
                with col3:
                    st.metric("표준품", len(filtered_df[filtered_df['구분'] == '표준품']))
                
                with col4:
                    st.metric("샘플재고", len(filtered_df[filtered_df['구분'] == '샘플재고']))
                
                # 다운로드 버튼
                csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 CSV 다운로드",
                    data=csv_data.encode('utf-8-sig'),
                    file_name=f"발행내역_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv; charset=utf-8"
                )
                
            else:
                st.info("발행 내역이 없습니다.")
                
        except Exception as e:
            st.error(f"발행 내역 로드 실패: {e}")
    else:
        st.info("발행 내역 파일이 없습니다.")

def show_settings_page():
    """설정 페이지"""
    st.markdown('<h2 class="section-header">⚙️ 시스템 설정</h2>', unsafe_allow_html=True)
    
    # 구글 스프레드시트 설정
    if GOOGLE_SERVICES_AVAILABLE:
        st.markdown("### 🔗 구글 스프레드시트 연동")
        
        if st.button("☁️ 구글 스프레드시트 설정", use_container_width=True):
            try:
                # 기존 스프레드시트 연결 테스트
                if sheets_manager.authenticate():
                    st.success("구글 스프레드시트 연결이 성공했습니다!")
                    
                    # 현재 설정된 스프레드시트 정보 표시
                    if sheets_manager.spreadsheet_id:
                        st.info(f"연결된 스프레드시트 ID: {sheets_manager.spreadsheet_id}")
                        st.info(f"스프레드시트 URL: {sheets_manager.get_spreadsheet_url()}")
                    else:
                        st.warning("스프레드시트 ID가 설정되지 않았습니다. secrets.toml에서 설정하세요.")
                else:
                    st.error("구글 스프레드시트 인증에 실패했습니다.")
                    st.info("secrets.toml 파일에 Google Sheets 설정이 올바른지 확인하세요.")
            except Exception as e:
                st.error(f"설정 오류: {e}")
                import traceback
                st.error(f"상세 오류: {traceback.format_exc()}")
    else:
        st.warning("구글 스프레드시트 연동 모듈을 사용할 수 없습니다.")
    
    # 시스템 정보
    st.markdown("### 📋 시스템 정보")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **데이터베이스**: {'✅ 연결됨' if os.path.exists(os.path.join(current_dir, 'label_serial.db')) else '❌ 연결 안됨'}
        
        **제품 정보**: {'✅ 로드됨' if st.session_state.products else '❌ 로드 안됨'}
        
        **구역 설정**: {'✅ 로드됨' if st.session_state.zone_config else '❌ 로드 안됨'}
        """)
    
    with col2:
        st.info(f"""
        **구글 스프레드시트**: {'✅ 사용 가능' if GOOGLE_SERVICES_AVAILABLE else '❌ 사용 불가'}
        
        **MySQL 데이터베이스**: {'✅ 사용 가능' if MYSQL_AVAILABLE else '❌ 사용 불가'}
        
        **현재 일련번호**: {get_next_serial_number() - 1}
        """)

def show_dashboard_page():
    """대시보드 페이지"""
    st.markdown('<h2 class="section-header">📈 대시보드</h2>', unsafe_allow_html=True)
    
    # 발행 내역 로드
    excel_file = os.path.join(current_dir, 'issue_history.xlsx')
    
    if os.path.exists(excel_file):
        try:
            df = pd.read_excel(excel_file, engine='openpyxl')
            
            if not df.empty:
                # 날짜별 발행 현황
                df['발행일시'] = pd.to_datetime(df['발행일시'])
                df['발행일'] = df['발행일시'].dt.date
                
                daily_counts = df.groupby('발행일').size().reset_index(name='발행수')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📅 일별 발행 현황")
                    st.line_chart(daily_counts.set_index('발행일'))
                
                with col2:
                    st.markdown("### 🏷️ 구분별 발행 현황")
                    category_counts = df['구분'].value_counts()
                    st.bar_chart(category_counts)
                
                # 최근 발행 내역
                st.markdown("### 📋 최근 발행 내역")
                recent_df = df.tail(10).sort_values('발행일시', ascending=False)
                st.dataframe(recent_df[['일련번호', '구분', '제품코드', '제품명', '보관위치', '발행일시']], use_container_width=True)
                
            else:
                st.info("발행 내역이 없습니다.")
                
        except Exception as e:
            st.error(f"대시보드 데이터 로드 실패: {e}")
    else:
        st.info("발행 내역 파일이 없습니다.")

if __name__ == "__main__":
    main()

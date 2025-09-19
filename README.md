# 바코드 라벨 생성 시스템

Streamlit을 사용한 바코드 라벨 생성 및 관리 시스템입니다.

## 주요 기능

- 🏷️ **바코드 라벨 생성**: 제품 정보를 바탕으로 30mm x 20mm 크기의 바코드 라벨 생성
- 📊 **제품 관리**: Excel 파일을 통한 제품 정보 관리
- 🗂️ **발행 이력 관리**: 라벨 발행 내역을 Excel 및 Google Sheets에 저장
- 🖨️ **인쇄 지원**: 생성된 라벨을 PNG 파일로 내보내어 인쇄 가능
- 🌐 **웹 인터페이스**: Streamlit을 통한 직관적인 웹 인터페이스

## 시스템 요구사항

- Python 3.8 이상
- Windows 10/11 (한글 폰트 지원)
- 인터넷 연결 (Google Sheets 연동 시)

## 설치 방법

1. 저장소 클론
```bash
git clone <repository-url>
cd Barcode_label-main
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# 또는
source venv/bin/activate  # Linux/Mac
```

3. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

4. 설정 파일 생성
   - `client_secrets.json`: Google Sheets API 인증 파일
   - `mysql_auth.py`: MySQL 연결 설정 (선택사항)

## 사용 방법

### 1. Streamlit 앱 실행
```bash
python barcode_label/run_streamlit.py
```

### 2. 웹 브라우저에서 접속
- http://localhost:8501

### 3. 라벨 생성
1. 제품 코드 선택
2. LOT 번호 입력
3. 유통기한 입력
4. 보관 위치 선택
5. 버전 입력
6. "라벨 생성" 버튼 클릭

### 4. 라벨 인쇄
1. "인쇄용 파일 다운로드" 버튼 클릭
2. 다운로드된 PNG 파일을 열기
3. Ctrl+P로 인쇄

## 파일 구조

```
barcode_label/
├── streamlit_app.py          # 메인 Streamlit 애플리케이션
├── run_streamlit.py          # Streamlit 실행 스크립트
├── google_sheets_manager.py  # Google Sheets 연동 관리
├── stock_manager.py          # 재고 관리
├── zone_manager.py           # 보관 위치 관리
├── label_gui.py             # 기존 GUI 애플리케이션
├── label_gui_30x20.py       # 30x20 라벨 전용 GUI
├── barcode_printing.py      # 바코드 인쇄 관련
├── location_visualizer.py   # 위치 시각화
├── label_dashboard.py       # 대시보드
├── products.xlsx            # 제품 정보 데이터
├── labeljpg/                # 생성된 라벨 이미지
├── zpl/                     # ZPL 파일
└── requirements.txt         # 필요한 패키지 목록
```

## 주요 설정

### Google Sheets 연동
1. Google Cloud Console에서 프로젝트 생성
2. Google Sheets API 활성화
3. 서비스 계정 생성 및 키 다운로드
4. `client_secrets.json` 파일을 프로젝트 루트에 배치
5. 서비스 계정 이메일을 Google Sheets에 공유

### 제품 정보 관리
- `products.xlsx` 파일에서 제품 정보 관리
- 컬럼: 제품코드, 제품명, 구분, 유통기한

### 보관 위치 관리
- `zone_config.json`에서 보관 위치 설정
- 예: A-01, A-02, B-01, B-02 등

## 라벨 규격

- **크기**: 30mm x 20mm (4배 확대하여 480x320 픽셀로 생성)
- **포함 정보**: 바코드, 제품명, LOT, 유통기한, 보관위치, 버전
- **폰트**: 시스템 한글 폰트 자동 감지 (Malgun Gothic, Gulim 등)

## 문제 해결

### 한글 폰트 문제
- Windows에서 한글 폰트가 자동으로 감지됩니다
- 문제가 있는 경우 `streamlit_app.py`의 `get_korean_font()` 함수를 수정하세요

### Google Sheets 연결 문제
- `client_secrets.json` 파일이 올바른 위치에 있는지 확인
- 서비스 계정 이메일이 Google Sheets에 공유되어 있는지 확인
- 인터넷 연결 상태 확인

### 인쇄 문제
- 인쇄용 파일을 다운로드하여 수동으로 인쇄
- 프린터 드라이버가 올바르게 설치되어 있는지 확인

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여

버그 리포트나 기능 제안은 Issues를 통해 알려주세요.

## 변경 이력

- v1.0.0: 초기 버전
- v1.1.0: Google Sheets 연동 추가
- v1.2.0: Streamlit 웹 인터페이스 추가
- v1.3.0: 30x20 라벨 크기 최적화
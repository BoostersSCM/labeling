# 구글 스프레드시트 연동 설정 가이드

## 1. 필요한 라이브러리 설치

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client gspread
```

## 2. 구글 클라우드 콘솔 설정

### 2.1 Google Cloud Console 접속
1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택

### 2.2 Google Sheets API 활성화
1. "API 및 서비스" → "라이브러리" 메뉴로 이동
2. "Google Sheets API" 검색 후 활성화
3. "Google Drive API" 검색 후 활성화

### 2.3 사용자 인증 정보 생성 (OAuth 2.0)

#### 방법 1: OAuth 2.0 클라이언트 ID (사용자 인증)
1. "API 및 서비스" → "사용자 인증 정보" 메뉴로 이동
2. "사용자 인증 정보 만들기" → "OAuth 2.0 클라이언트 ID" 선택
3. 애플리케이션 유형: "데스크톱 앱" 선택
4. 이름 입력 후 "만들기" 클릭
5. 다운로드된 JSON 파일을 `client_secrets.json`으로 저장하여 `barcode_label` 폴더에 배치

#### 방법 2: 서비스 계정 (자동화용)
1. "API 및 서비스" → "사용자 인증 정보" 메뉴로 이동
2. "사용자 인증 정보 만들기" → "서비스 계정" 선택
3. 서비스 계정 이름 입력 후 "만들기" 클릭
4. "키" 탭에서 "키 추가" → "새 키 만들기" → "JSON" 선택
5. 다운로드된 JSON 파일을 `credentials.json`으로 저장하여 `barcode_label` 폴더에 배치

## 3. 구글 스프레드시트 설정

### 3.1 새 스프레드시트 생성
1. [Google Sheets](https://sheets.google.com/)에 접속
2. 새 스프레드시트 생성
3. 스프레드시트 URL에서 ID 복사:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
   ```

### 3.2 권한 설정
- **OAuth 2.0 방식**: 첫 실행 시 브라우저에서 구글 계정 인증
- **서비스 계정 방식**: 스프레드시트를 서비스 계정 이메일과 공유

## 4. 프로그램에서 설정

### 4.1 초기 설정
1. 라벨 생성 프로그램 실행
2. "📋 발행 내역" 버튼 클릭
3. "⚙️ 구글시트 설정" 버튼 클릭
4. 스프레드시트 ID 입력 또는 'new' 입력하여 새 스프레드시트 생성

### 4.2 사용 방법
- **☁️ 구글시트 업로드**: Excel 파일의 발행 내역을 구글 스프레드시트에 업로드
- **⬇️ 구글시트 다운로드**: 구글 스프레드시트의 데이터를 Excel 파일로 다운로드

## 5. 파일 구조

```
barcode_label/
├── google_sheets_manager.py    # 구글 스프레드시트 연동 모듈
├── client_secrets.json         # OAuth 2.0 클라이언트 설정 (선택사항)
├── credentials.json            # 서비스 계정 키 (선택사항)
├── token.pickle               # 인증 토큰 (자동 생성)
├── sheets_config.json         # 스프레드시트 설정 (자동 생성)
└── GOOGLE_SHEETS_SETUP.md     # 이 설정 가이드
```

## 6. 문제 해결

### 6.1 인증 오류
- `client_secrets.json` 또는 `credentials.json` 파일이 올바른 위치에 있는지 확인
- 구글 클라우드 콘솔에서 API가 활성화되어 있는지 확인

### 6.2 권한 오류
- 스프레드시트가 올바른 계정과 공유되어 있는지 확인
- 서비스 계정을 사용하는 경우 스프레드시트를 서비스 계정 이메일과 공유

### 6.3 모듈 오류
- 필요한 라이브러리가 설치되어 있는지 확인: `pip list | grep google`
- Python 환경이 올바른지 확인

## 7. 보안 주의사항

- `credentials.json` 파일은 민감한 정보를 포함하므로 안전하게 보관
- Git 등에 업로드하지 않도록 주의
- 프로덕션 환경에서는 환경 변수나 보안 저장소 사용 권장

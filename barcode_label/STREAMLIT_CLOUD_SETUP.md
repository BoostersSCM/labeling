# Streamlit Cloud 설정 가이드

## Google Sheets 연동 설정

Streamlit Cloud에서 Google Sheets 연동을 사용하려면 다음 환경 변수를 설정해야 합니다.

### 1. Google Cloud Console에서 서비스 계정 생성

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. "API 및 서비스" > "사용 설정된 API"에서 다음 API 활성화:
   - Google Sheets API
   - Google Drive API
4. "사용자 인증 정보" > "사용자 인증 정보 만들기" > "서비스 계정"
5. 서비스 계정 이름 입력 (예: `barcode-label-service`)
6. "역할"에서 "편집자" 선택
7. "키" 탭에서 "키 추가" > "새 키 만들기" > "JSON" 선택
8. JSON 파일 다운로드

### 2. Streamlit Cloud에서 Secrets 설정

1. Streamlit Cloud 대시보드에서 앱 선택
2. "Settings" > "Secrets" 탭으로 이동
3. 다음 TOML 형식으로 설정 추가:

```toml
# Google Sheets 연동 설정
[google_sheets]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
# 스프레드시트 설정
spreadsheet_id = "your-spreadsheet-id"
sheet_name = "발행이력"

# MySQL 데이터베이스 설정
[mysql]
host = "your-mysql-host.com"
user = "your-username"
password = "your-password"
database = "your-database-name"
port = 3306
```

### 3. Google Sheets 공유 설정

1. 사용할 Google Sheets 문서 열기
2. "공유" 버튼 클릭
3. 서비스 계정 이메일 주소 추가 (예: `your-service-account@your-project.iam.gserviceaccount.com`)
4. 권한을 "편집자"로 설정

### 4. 스프레드시트 ID 설정

Streamlit 앱에서 스프레드시트 ID를 설정해야 합니다:

1. Google Sheets URL에서 스프레드시트 ID 복사
   - URL 형식: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
2. Streamlit 앱의 "시스템 설정" 페이지에서 스프레드시트 ID 입력

## 문제 해결

### 인증 실패
- 서비스 계정 JSON이 올바른지 확인
- 필요한 API가 활성화되어 있는지 확인
- 서비스 계정 이메일이 스프레드시트에 공유되어 있는지 확인

### 권한 오류
- 서비스 계정에 "편집자" 권한이 부여되어 있는지 확인
- 스프레드시트 ID가 올바른지 확인

### 네트워크 오류
- Streamlit Cloud의 네트워크 설정 확인
- 방화벽이나 프록시 설정 확인

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
구글 스프레드시트 연동 관리자
발행 이력을 구글 스프레드시트에 저장하고 불러오는 기능
"""

import os
import json
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

class GoogleSheetsManager:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.credentials_file = os.path.join(self.script_dir, 'credentials.json')
        self.token_file = os.path.join(self.script_dir, 'token.pickle')
        self.config_file = os.path.join(self.script_dir, 'sheets_config.json')
        
        # Google Sheets API 스코프
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        self.service = None
        self.spreadsheet_id = None
        self.sheet_name = "발행이력"
        
        # 설정 로드
        self.load_config()
    
    def load_config(self):
        """구글 스프레드시트 설정 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.spreadsheet_id = config.get('spreadsheet_id')
                    self.sheet_name = config.get('sheet_name', '발행이력')
        except Exception as e:
            print(f"설정 로드 오류: {e}")
    
    def save_config(self):
        """구글 스프레드시트 설정 저장"""
        try:
            config = {
                'spreadsheet_id': self.spreadsheet_id,
                'sheet_name': self.sheet_name
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"설정 저장 오류: {e}")
    
    def authenticate(self):
        """구글 API 인증"""
        creds = None
        
        # Streamlit Cloud 환경에서는 Streamlit secrets 사용
        if os.environ.get('STREAMLIT_CLOUD', False) or os.environ.get('STREAMLIT_SERVER_HEADLESS', False):
            try:
                # Streamlit secrets에서 Google Sheets 설정 가져오기
                import streamlit as st
                if 'google_sheets' in st.secrets:
                    service_account_data = st.secrets['google_sheets']
                    creds = Credentials.from_service_account_info(
                        service_account_data, scopes=self.scopes
                    )
                    print("Streamlit secrets로 서비스 계정 인증되었습니다.")
                else:
                    print("Google Sheets 설정이 secrets.toml에 없습니다.")
                    return False
            except Exception as e:
                print(f"Streamlit secrets 인증 실패: {e}")
                return False
        else:
            # 로컬 환경에서는 파일 기반 인증
            # 토큰 파일이 있으면 로드
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            # 유효한 인증 정보가 없거나 만료된 경우
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # 서비스 계정 키 파일이 있으면 사용 (client_secrets.json이 서비스 계정 키인 경우)
                    client_secrets_file = os.path.join(self.script_dir, 'client_secrets.json')
                    if os.path.exists(client_secrets_file):
                        try:
                            # 서비스 계정 키로 인증 시도
                            creds = Credentials.from_service_account_file(
                                client_secrets_file, scopes=self.scopes
                            )
                            print("서비스 계정 키로 인증되었습니다.")
                        except Exception as e:
                            print(f"서비스 계정 키 인증 실패: {e}")
                            return False
                    else:
                        print(f"client_secrets.json 파일을 찾을 수 없습니다: {client_secrets_file}")
                        return False
                
                # 토큰 저장
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
        
        try:
            self.service = gspread.authorize(creds)
            return True
        except Exception as e:
            print(f"인증 오류: {e}")
            return False
    
    def create_spreadsheet(self, title="바코드 라벨 발행이력"):
        """새 구글 스프레드시트 생성"""
        print(f"스프레드시트 생성 시작: {title}")
        
        if not self.authenticate():
            print("인증 실패로 스프레드시트 생성 불가")
            return None
        
        try:
            print("구글 스프레드시트 API 호출 중...")
            spreadsheet = self.service.create(title)
            self.spreadsheet_id = spreadsheet.id
            print(f"스프레드시트 생성 성공: {self.spreadsheet_id}")
            
            # 기본 시트 이름 변경
            print("시트 이름 변경 중...")
            worksheet = spreadsheet.get_worksheet(0)
            worksheet.update_title(self.sheet_name)
            print(f"시트 이름 변경 완료: {self.sheet_name}")
            
            # 헤더 추가
            print("헤더 추가 중...")
            headers = [
                '일련번호', '구분', '제품코드', '제품명', 'LOT', 
                '유통기한', '폐기일자', '보관위치', '버전', '발행일시'
            ]
            worksheet.append_row(headers)
            print("헤더 추가 완료")
            
            # 설정 저장
            print("설정 저장 중...")
            self.save_config()
            print("설정 저장 완료")
            
            return spreadsheet.id
        except Exception as e:
            print(f"스프레드시트 생성 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_spreadsheet_url(self):
        """스프레드시트 URL 반환"""
        if self.spreadsheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        return None
    
    def upload_to_sheets(self, excel_file_path):
        """Excel 파일을 구글 스프레드시트에 업로드"""
        if not self.authenticate():
            return False
        
        try:
            # Excel 파일 읽기
            df = pd.read_excel(excel_file_path)
            
            # 스프레드시트가 없으면 생성
            if not self.spreadsheet_id:
                self.create_spreadsheet()
            
            if not self.spreadsheet_id:
                return False
            
            # 스프레드시트 열기
            spreadsheet = self.service.open_by_key(self.spreadsheet_id)
            
            # 시트 가져오기 (없으면 생성)
            try:
                worksheet = spreadsheet.worksheet(self.sheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=self.sheet_name, rows=1000, cols=10)
            
            # 기존 데이터 삭제 (헤더 제외)
            worksheet.clear()
            
            # 헤더 추가
            headers = list(df.columns)
            worksheet.append_row(headers)
            
            # 데이터 추가
            for _, row in df.iterrows():
                worksheet.append_row(row.tolist())
            
            print(f"구글 스프레드시트에 {len(df)}개 행이 업로드되었습니다.")
            return True
            
        except Exception as e:
            print(f"업로드 오류: {e}")
            return False
    
    def download_from_sheets(self, excel_file_path):
        """구글 스프레드시트에서 Excel 파일로 다운로드"""
        if not self.authenticate() or not self.spreadsheet_id:
            return False
        
        try:
            # 스프레드시트 열기
            spreadsheet = self.service.open_by_key(self.spreadsheet_id)
            
            # 시트 가져오기
            try:
                worksheet = spreadsheet.worksheet(self.sheet_name)
            except gspread.WorksheetNotFound:
                print(f"시트 '{self.sheet_name}'을 찾을 수 없습니다.")
                return False
            
            # 모든 데이터 가져오기
            data = worksheet.get_all_records()
            
            # DataFrame으로 변환
            df = pd.DataFrame(data)
            
            # Excel 파일로 저장
            df.to_excel(excel_file_path, index=False)
            
            print(f"구글 스프레드시트에서 {len(df)}개 행이 다운로드되었습니다.")
            return True
            
        except Exception as e:
            print(f"다운로드 오류: {e}")
            return False
    
    def add_row_to_sheets(self, row_data):
        """개별 행을 구글 스프레드시트에 추가"""
        print(f"Google Sheets에 데이터 추가 시도: {row_data}")
        
        if not self.authenticate():
            print("Google Sheets 인증 실패")
            return False
        
        try:
            # 스프레드시트가 없으면 생성
            if not self.spreadsheet_id:
                print("스프레드시트 ID가 없어서 새로 생성합니다.")
                self.create_spreadsheet()
            
            if not self.spreadsheet_id:
                print("스프레드시트 생성 실패")
                return False
            
            print(f"스프레드시트 ID: {self.spreadsheet_id}")
            
            # 스프레드시트 열기
            spreadsheet = self.service.open_by_key(self.spreadsheet_id)
            print("스프레드시트 열기 성공")
            
            # 시트 가져오기 (없으면 생성)
            try:
                worksheet = spreadsheet.worksheet(self.sheet_name)
                print(f"기존 시트 '{self.sheet_name}' 사용")
            except gspread.WorksheetNotFound:
                print(f"시트 '{self.sheet_name}'가 없어서 새로 생성합니다.")
                worksheet = spreadsheet.add_worksheet(title=self.sheet_name, rows=1000, cols=10)
                # 헤더 추가 (지정된 컬럼 순서에 맞게)
                headers = [
                    '일련번호', '구분', '제품코드', '제품명', 'LOT', 
                    '유통기한', '폐기일자', '보관위치', '버전', '발행일시'
                ]
                worksheet.append_row(headers)
                print("헤더 추가 완료")
            
            # 데이터 행 추가 (지정된 컬럼 순서에 맞게)
            row_values = [
                row_data.get('일련번호', ''),      # A열: 바코드 번호
                row_data.get('구분', ''),          # B열: 구분
                row_data.get('제품코드', ''),      # C열: 제품코드
                row_data.get('제품명', ''),        # D열: 제품명
                row_data.get('LOT', ''),          # E열: LOT
                row_data.get('유통기한', ''),      # F열: 유통기한
                row_data.get('폐기일자', ''),      # G열: 폐기일자 (유통기한 + 1년)
                row_data.get('보관위치', ''),      # H열: 보관위치
                row_data.get('버전', ''),          # I열: 버전
                row_data.get('발행일시', '')       # J열: 발행일시
            ]
            
            print(f"추가할 데이터: {row_values}")
            worksheet.append_row(row_values)
            print(f"구글 스프레드시트에 새 행이 추가되었습니다.")
            return True
            
        except Exception as e:
            print(f"행 추가 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

    def sync_with_sheets(self, excel_file_path, direction="upload"):
        """Excel 파일과 구글 스프레드시트 동기화"""
        if direction == "upload":
            return self.upload_to_sheets(excel_file_path)
        elif direction == "download":
            return self.download_from_sheets(excel_file_path)
        else:
            return False
    
    def setup_initial_config(self, spreadsheet_id=None):
        """초기 설정 (Streamlit 환경용)"""
        if not spreadsheet_id:
            print("구글 스프레드시트 ID가 제공되지 않았습니다.")
            return False
        
        if spreadsheet_id.lower() == 'new':
            # 새 스프레드시트 생성
            print("새 구글 스프레드시트를 생성합니다...")
            new_id = self.create_spreadsheet()
            if new_id:
                # 서비스 계정 이메일 정보 표시
                service_account_email = self._get_service_account_email()
                print(f"새 구글 스프레드시트가 생성되었습니다.")
                print(f"스프레드시트 ID: {new_id}")
                print(f"URL: {self.get_spreadsheet_url()}")
                print(f"⚠️ 다음 이메일을 스프레드시트에 공유하세요: {service_account_email}")
                print(f"권한: 편집자")
                return True
            else:
                print("스프레드시트 생성에 실패했습니다.")
                return False
        else:
            # 기존 스프레드시트 사용
            self.spreadsheet_id = spreadsheet_id
            self.save_config()
            
            # 연결 테스트
            if self.authenticate():
                try:
                    spreadsheet = self.service.open_by_key(self.spreadsheet_id)
                    print(f"구글 스프레드시트에 연결되었습니다.")
                    print(f"스프레드시트 ID: {self.spreadsheet_id}")
                    print(f"URL: {self.get_spreadsheet_url()}")
                    return True
                except Exception as e:
                    # 서비스 계정 이메일 정보와 함께 오류 메시지 표시
                    service_account_email = self._get_service_account_email()
                    print(f"스프레드시트에 연결할 수 없습니다: {e}")
                    print(f"⚠️ 해결 방법:")
                    print(f"1. 스프레드시트 ID가 올바른지 확인")
                    print(f"2. 다음 이메일을 스프레드시트에 공유하세요: {service_account_email}")
                    print(f"3. 권한: 편집자로 설정")
                    return False
            else:
                print("구글 API 인증에 실패했습니다.")
                return False
    
    def _get_service_account_email(self):
        """서비스 계정 이메일 가져오기"""
        try:
            client_secrets_file = os.path.join(self.script_dir, 'client_secrets.json')
            if os.path.exists(client_secrets_file):
                with open(client_secrets_file, 'r') as f:
                    secrets = json.load(f)
                    return secrets.get('client_email', '알 수 없음')
        except:
            pass
        return '알 수 없음'

# 전역 인스턴스
sheets_manager = GoogleSheetsManager()

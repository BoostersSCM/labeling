#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit 앱 실행 스크립트
"""

import subprocess
import sys
import os

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'ko_KR.UTF-8'
os.environ['LC_ALL'] = 'ko_KR.UTF-8'

def main():
    """Streamlit 앱 실행"""
    try:
        # 현재 디렉토리 확인
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_file = os.path.join(current_dir, 'streamlit_app.py')
        
        if not os.path.exists(app_file):
            print(f"❌ Streamlit 앱 파일을 찾을 수 없습니다: {app_file}")
            return
        
        print("🚀 Streamlit 바코드 라벨 관리 시스템을 시작합니다...")
        print("📱 웹 브라우저에서 http://localhost:8501 을 열어주세요.")
        print("⏹️  종료하려면 Ctrl+C를 누르세요.")
        print("-" * 50)
        
        # Streamlit 앱 실행 (UTF-8 인코딩 설정 포함)
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", app_file,
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false",
            "--global.developmentMode", "false"
        ], env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        
    except KeyboardInterrupt:
        print("\n👋 Streamlit 앱이 종료되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()


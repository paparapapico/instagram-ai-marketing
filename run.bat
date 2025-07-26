@echo off
echo Starting Instagram AI Marketing Platform...

REM 가상환경 활성화 (있는 경우)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM 의존성 설치
pip install -r requirements.txt

REM 애플리케이션 실행
python main.py

pause

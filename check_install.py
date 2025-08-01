# check_install.py - 의존성 설치 확인
import sys

def check_module(module_name, package_name=None):
    """모듈 설치 여부 확인"""
    try:
        __import__(module_name)
        print(f"✅ {module_name}: 설치됨")
        return True
    except ImportError:
        package = package_name or module_name
        print(f"❌ {module_name}: 미설치 (pip install {package})")
        return False

def main():
    """필수 모듈 확인"""
    print("📦 Instagram AI Marketing 의존성 확인")
    print("=" * 50)
    
    required_modules = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn[standard]'),
        ('pydantic', 'pydantic[email]'),
        ('jinja2', 'jinja2'),
        ('dotenv', 'python-dotenv'),
        ('bcrypt', 'bcrypt'),
        ('jwt', 'PyJWT'),
        ('requests', 'requests'),
        ('openai', 'openai'),
        ('PIL', 'Pillow'),
        ('schedule', 'schedule'),
        ('aiofiles', 'aiofiles'),
        ('sqlite3', None)  # 내장 모듈
    ]
    
    missing_modules = []
    
    for module, package in required_modules:
        if not check_module(module):
            if package:
                missing_modules.append(package)
    
    print("\n" + "=" * 50)
    
    if missing_modules:
        print(f"❌ {len(missing_modules)}개 모듈이 누락되었습니다.")
        print("\n📋 설치 명령어:")
        print(f"pip install {' '.join(missing_modules)}")
    else:
        print("🎉 모든 필수 모듈이 설치되어 있습니다!")
        print("이제 'python main.py'를 실행할 수 있습니다.")

if __name__ == "__main__":
    main()
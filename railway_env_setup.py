# railway_env_setup.py - Railway 환경변수 설정 도구
import subprocess
import os
from dotenv import load_dotenv

def load_local_env():
    """로컬 .env 파일 로드"""
    load_dotenv()
    
    # 필수 환경변수 목록
    required_vars = [
        'SECRET_KEY',
        'OPENAI_API_KEY', 
        'INSTAGRAM_ACCESS_TOKEN',
        'INSTAGRAM_BUSINESS_ACCOUNT_ID',
        'ENVIRONMENT',
        'DEBUG',
        'HOST',
        'PORT'
    ]
    
    env_vars = {}
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            env_vars[var] = value
        else:
            missing_vars.append(var)
    
    return env_vars, missing_vars

def set_railway_env_vars(env_vars):
    """Railway에 환경변수 설정"""
    print("🚂 Railway 환경변수 설정 중...")
    
    success_count = 0
    failed_vars = []
    
    for var_name, var_value in env_vars.items():
        try:
            # 민감한 정보는 마스킹해서 출력
            display_value = var_value
            if any(keyword in var_name.lower() for keyword in ['key', 'token', 'secret', 'password']):
                display_value = var_value[:8] + "..." + var_value[-4:] if len(var_value) > 12 else "***"
            
            print(f"   설정 중: {var_name} = {display_value}")
            
            # Railway CLI로 환경변수 설정
            result = subprocess.run([
                'railway', 'variables', 'set', 
                f'{var_name}={var_value}'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"   ✅ {var_name} 설정 완료")
                success_count += 1
            else:
                print(f"   ❌ {var_name} 설정 실패: {result.stderr}")
                failed_vars.append(var_name)
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ {var_name} 설정 시간 초과")
            failed_vars.append(var_name)
        except Exception as e:
            print(f"   ❌ {var_name} 설정 오류: {e}")
            failed_vars.append(var_name)
    
    return success_count, failed_vars

def check_railway_env_vars():
    """Railway 환경변수 확인"""
    print("\n🔍 Railway 환경변수 확인...")
    
    try:
        result = subprocess.run(['railway', 'variables'], 
                              capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ 설정된 환경변수:")
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if '=' in line:
                    var_name = line.split('=')[0]
                    print(f"   {var_name}")
        else:
            print(f"❌ 환경변수 조회 실패: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 환경변수 확인 오류: {e}")

def trigger_deployment():
    """배포 트리거"""
    print("\n🚀 배포 트리거...")
    
    try:
        # Railway 재배포
        result = subprocess.run(['railway', 'up', '--detach'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ 배포 시작됨")
            print(result.stdout)
        else:
            print(f"❌ 배포 실패: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏰ 배포 시간 초과 - 백그라운드에서 계속 진행됩니다.")
    except Exception as e:
        print(f"❌ 배포 오류: {e}")

def setup_auto_deploy():
    """자동 배포 설정 가이드"""
    print("\n⚙️ 자동 배포 설정 가이드:")
    print("1. Railway 대시보드 접속: https://railway.app/dashboard")
    print("2. 프로젝트 선택")
    print("3. Settings 탭 클릭")
    print("4. GitHub Repository 연결 확인")
    print("5. Auto Deploy 활성화")
    print("6. Branch를 'main' 또는 'master'로 설정")
    print("7. Deploy Trigger를 'Push to branch'로 설정")

def main():
    """메인 설정 함수"""
    print("🚂 Railway 배포 설정 도구")
    print("=" * 50)
    
    # 1. Railway CLI 확인
    try:
        result = subprocess.run(['railway', '--version'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Railway CLI가 설치되지 않았습니다.")
            print("💡 설치 방법: npm install -g @railway/cli")
            return
        print(f"✅ Railway CLI: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Railway CLI가 설치되지 않았습니다.")
        print("💡 설치 방법: npm install -g @railway/cli")
        return
    
    # 2. 로컬 환경변수 로드
    env_vars, missing_vars = load_local_env()
    
    if missing_vars:
        print(f"⚠️ 누락된 환경변수: {missing_vars}")
        print("먼저 .env 파일을 완성하세요.")
        return
    
    print(f"✅ 로컬 환경변수 {len(env_vars)}개 로드됨")
    
    # 3. Railway 환경변수 설정
    success_count, failed_vars = set_railway_env_vars(env_vars)
    
    print(f"\n📊 결과: {success_count}/{len(env_vars)} 환경변수 설정 완료")
    
    if failed_vars:
        print(f"❌ 실패한 변수: {failed_vars}")
    
    # 4. 설정된 환경변수 확인
    check_railway_env_vars()
    
    # 5. 배포 트리거
    if success_count == len(env_vars):
        trigger_deployment()
    
    # 6. 자동 배포 설정 가이드
    setup_auto_deploy()
    
    print("\n🎯 다음 단계:")
    print("1. Git에 변경사항 커밋 및 푸시")
    print("2. Railway 대시보드에서 자동 배포 설정 확인")
    print("3. 배포 로그 모니터링: railway logs")

if __name__ == "__main__":
    main()
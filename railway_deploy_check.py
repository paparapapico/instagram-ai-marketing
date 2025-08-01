# railway_deploy_check.py - Railway 배포 상태 확인 도구
import subprocess
import json
import os

def check_git_status():
    """Git 상태 확인"""
    print("🔍 Git 상태 확인...")
    
    try:
        # 현재 브랜치 확인
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True)
        current_branch = result.stdout.strip()
        print(f"📍 현재 브랜치: {current_branch}")
        
        # 원격 저장소 확인
        result = subprocess.run(['git', 'remote', '-v'], 
                              capture_output=True, text=True)
        remotes = result.stdout.strip()
        print(f"🔗 원격 저장소:")
        for line in remotes.split('\n'):
            print(f"   {line}")
        
        # 커밋되지 않은 변경사항 확인
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        uncommitted = result.stdout.strip()
        
        if uncommitted:
            print("⚠️ 커밋되지 않은 변경사항:")
            for line in uncommitted.split('\n'):
                print(f"   {line}")
            return False
        else:
            print("✅ 모든 변경사항이 커밋되었습니다.")
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Git 명령 오류: {e}")
        return False

def check_railway_connection():
    """Railway 연결 확인"""
    print("\n🚂 Railway 연결 확인...")
    
    try:
        # Railway CLI 설치 확인
        result = subprocess.run(['railway', '--version'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Railway CLI 설치됨: {result.stdout.strip()}")
        else:
            print("❌ Railway CLI가 설치되지 않았습니다.")
            print("💡 설치 방법: npm install -g @railway/cli")
            return False
        
        # Railway 로그인 상태 확인
        result = subprocess.run(['railway', 'whoami'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Railway 로그인됨: {result.stdout.strip()}")
        else:
            print("❌ Railway에 로그인되지 않았습니다.")
            print("💡 로그인 방법: railway login")
            return False
        
        # 프로젝트 연결 상태 확인
        result = subprocess.run(['railway', 'status'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Railway 프로젝트 연결됨")
            print(f"   상태: {result.stdout.strip()}")
            return True
        else:
            print("❌ Railway 프로젝트에 연결되지 않았습니다.")
            print("💡 연결 방법: railway link")
            return False
            
    except FileNotFoundError:
        print("❌ Railway CLI가 설치되지 않았습니다.")
        print("💡 설치 방법:")
        print("   1. Node.js 설치: https://nodejs.org/")
        print("   2. Railway CLI 설치: npm install -g @railway/cli")
        return False

def check_deployment_settings():
    """배포 설정 확인"""
    print("\n⚙️ 배포 설정 확인...")
    
    # railway.json 파일 확인
    if os.path.exists('railway.json'):
        print("✅ railway.json 파일 존재")
        try:
            with open('railway.json', 'r') as f:
                config = json.load(f)
            print(f"   설정: {json.dumps(config, indent=2)}")
        except Exception as e:
            print(f"⚠️ railway.json 읽기 오류: {e}")
    else:
        print("❌ railway.json 파일 없음")
    
    # Procfile 확인
    if os.path.exists('Procfile'):
        print("✅ Procfile 존재")
        with open('Procfile', 'r') as f:
            content = f.read().strip()
        print(f"   내용: {content}")
    else:
        print("❌ Procfile 없음")
    
    # requirements.txt 확인
    if os.path.exists('requirements.txt'):
        print("✅ requirements.txt 존재")
    else:
        print("❌ requirements.txt 없음")
    
    # main.py 확인
    if os.path.exists('main.py'):
        print("✅ main.py 존재")
    else:
        print("❌ main.py 없음")

def check_recent_deployments():
    """최근 배포 기록 확인"""
    print("\n📋 최근 배포 기록 확인...")
    
    try:
        result = subprocess.run(['railway', 'logs', '--tail', '10'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ 최근 로그:")
            print(result.stdout)
        else:
            print("❌ 로그 조회 실패")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("⏰ 로그 조회 시간 초과")
    except Exception as e:
        print(f"❌ 로그 조회 오류: {e}")

def main():
    """메인 진단 함수"""
    print("🔍 Railway 자동 배포 문제 진단")
    print("=" * 50)
    
    # 각 항목 확인
    git_ok = check_git_status()
    railway_ok = check_railway_connection()
    check_deployment_settings()
    check_recent_deployments()
    
    print("\n" + "=" * 50)
    print("📊 진단 결과")
    print("=" * 50)
    
    if git_ok and railway_ok:
        print("✅ 기본 설정은 정상입니다.")
        print("\n💡 수동 배포 시도:")
        print("   railway up")
        print("\n💡 자동 배포 재설정:")
        print("   1. Railway 대시보드에서 GitHub 연결 확인")
        print("   2. Auto Deploy 설정 확인")
        print("   3. Branch 설정 확인 (main/master)")
    else:
        print("❌ 설정에 문제가 있습니다.")
        
        if not git_ok:
            print("\n🔧 Git 문제 해결:")
            print("   1. git add .")
            print("   2. git commit -m 'Update files'")
            print("   3. git push origin main")
        
        if not railway_ok:
            print("\n🔧 Railway 문제 해결:")
            print("   1. npm install -g @railway/cli")
            print("   2. railway login")
            print("   3. railway link")

if __name__ == "__main__":
    main()
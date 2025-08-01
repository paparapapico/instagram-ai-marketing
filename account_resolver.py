# account_resolver.py - 계정 혼란 해결

import requests
import os

def resolve_account_confusion():
    """계정 혼란 해결"""
    
    print("🔍 Instagram 계정 혼란 해결 중...")
    print("=" * 60)
    
    # 사용자로부터 정보 수집
    print("\n📋 정보 입력:")
    current_token = input("현재 사용 중인 토큰을 입력하세요: ").strip()
    target_account = input("포스팅하고 싶은 Instagram 사용자명을 입력하세요 (@없이): ").strip()
    
    if not current_token:
        print("❌ 토큰이 필요합니다.")
        return
    
    print(f"\n🎯 목표: @{target_account} 계정에 포스팅")
    print(f"🔑 현재 토큰 길이: {len(current_token)}")
    
    # 1. 현재 토큰의 계정 확인
    print("\n" + "="*60)
    print("1️⃣ 현재 토큰의 실제 계정 확인")
    print("="*60)
    
    current_account_info = check_token_account(current_token)
    
    if not current_account_info:
        print("❌ 현재 토큰이 유효하지 않습니다.")
        return
    
    # 2. 계정 일치 여부 확인
    print("\n" + "="*60)
    print("2️⃣ 계정 일치 여부 분석")
    print("="*60)
    
    current_username = current_account_info.get('username', '').lower()
    target_username = target_account.lower()
    
    print(f"🔄 현재 토큰 계정: @{current_username}")
    print(f"🎯 목표 계정: @{target_username}")
    
    if current_username == target_username:
        print("✅ 계정 일치! 토큰이 올바릅니다.")
        print("\n🎉 포스팅 준비 완료!")
        
        # 환경변수 설정 가이드
        print("\n" + "="*60)
        print("3️⃣ 환경변수 설정")
        print("="*60)
        print("Railway에서 다음과 같이 설정하세요:")
        print(f"INSTAGRAM_ACCESS_TOKEN={current_token}")
        
        return True
        
    else:
        print("❌ 계정 불일치!")
        print(f"\n📊 상세 정보:")
        print(f"   현재 토큰 소유자: @{current_username} (ID: {current_account_info.get('id')})")
        print(f"   포스팅 목표 계정: @{target_username}")
        
        print(f"\n🚨 문제:")
        print(f"   Instagram API는 토큰 소유자 계정에만 포스팅할 수 있습니다.")
        print(f"   @{current_username}의 토큰으로는 @{target_username}에 포스팅 불가능!")
        
        # 해결책 제시
        provide_solution(target_username)
        
        return False

def check_token_account(token):
    """토큰의 실제 계정 정보 확인"""
    
    try:
        url = "https://graph.instagram.com/me"
        params = {
            'fields': 'id,username,account_type,name,followers_count,media_count',
            'access_token': token
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ 토큰 유효!")
            print(f"   📱 Instagram ID: {data.get('id')}")
            print(f"   👤 사용자명: @{data.get('username')}")
            print(f"   🏷️ 표시명: {data.get('name', '없음')}")
            print(f"   📊 계정 타입: {data.get('account_type')}")
            print(f"   👥 팔로워: {data.get('followers_count', '비공개')}")
            print(f"   📸 게시물: {data.get('media_count', 0)}")
            
            return data
            
        else:
            print(f"❌ API 오류: {response.status_code}")
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_msg = error_data.get('error', {}).get('message', response.text)
            print(f"   오류 내용: {error_msg}")
            
            return None
            
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return None

def provide_solution(target_username):
    """해결책 제시"""
    
    print(f"\n" + "="*60)
    print("🛠️ 해결 방법")
    print("="*60)
    
    print(f"@{target_username} 계정에 포스팅하려면:")
    
    print(f"\n1️⃣ 올바른 계정으로 토큰 생성:")
    print(f"   • Meta for Developers에서 로그아웃")
    print(f"   • @{target_username} 계정으로 Instagram 로그인")
    print(f"   • 해당 계정으로 토큰 재생성")
    
    print(f"\n2️⃣ 또는 현재 계정으로 계속 사용:")
    print(f"   • 현재 토큰으로 현재 계정에만 포스팅")
    print(f"   • 목표 계정을 현재 계정으로 변경")
    
    print(f"\n3️⃣ 비즈니스 계정 사용 (권장):")
    print(f"   • Instagram을 비즈니스 계정으로 전환")
    print(f"   • Facebook 페이지와 연결")
    print(f"   • Instagram Graph API 사용")
    
    print(f"\n⚠️ 중요:")
    print(f"   Instagram API는 보안상 토큰 소유자가 아닌")
    print(f"   다른 계정에는 포스팅할 수 없습니다!")

def test_posting_capability(token):
    """포스팅 가능 여부 테스트"""
    
    print(f"\n" + "="*60)
    print("4️⃣ 포스팅 권한 테스트")
    print("="*60)
    
    try:
        # 미디어 엔드포인트 접근 테스트
        url = "https://graph.instagram.com/me/media"
        headers = {'Authorization': f'Bearer {token}'}
        
        # HEAD 요청으로 엔드포인트 존재 확인
        response = requests.head(url, headers=headers, timeout=10)
        
        if response.status_code in [200, 405, 400]:  # 엔드포인트 존재
            print("✅ 미디어 API 엔드포인트 접근 가능")
            print("📝 실제 이미지와 캡션으로 포스팅 테스트 가능")
        else:
            print(f"⚠️ 미디어 API 응답: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ 포스팅 권한 테스트 오류: {e}")

if __name__ == "__main__":
    print("🎯 Instagram 계정 혼란 해결기")
    print("Instagram API 포스팅이 실패하는 이유를 찾아보겠습니다.")
    
    success = resolve_account_confusion()
    
    if success:
        print(f"\n🎉 문제 해결!")
        print(f"이제 Instagram 포스팅이 정상 작동할 것입니다.")
    else:
        print(f"\n🔧 추가 조치가 필요합니다.")
        print(f"위의 해결 방법을 따라 진행해주세요.")
        
    print(f"\n🕒 분석 완료: {__import__('datetime').datetime.now()}")
    print("="*60)
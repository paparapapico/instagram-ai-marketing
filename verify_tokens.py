# verify_tokens.py - 토큰 검증 도구
import os
import requests
from dotenv import load_dotenv

def test_openai_token():
    """OpenAI 토큰 테스트"""
    print("🤖 OpenAI API 토큰 테스트...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        return False
    
    if not api_key.startswith('sk-'):
        print("❌ OpenAI API 키 형식이 올바르지 않습니다. (sk-로 시작해야 함)")
        return False
    
    try:
        # OpenAI API 테스트 (간단한 모델 리스트 조회)
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            'https://api.openai.com/v1/models',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ OpenAI API 토큰이 유효합니다!")
            models = response.json()
            available_models = [m['id'] for m in models['data'] if 'gpt' in m['id']]
            print(f"   사용 가능한 GPT 모델: {len(available_models)}개")
            return True
        else:
            print(f"❌ OpenAI API 오류: {response.status_code}")
            print(f"   응답: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ OpenAI API 요청 시간 초과")
        return False
    except Exception as e:
        print(f"❌ OpenAI API 테스트 오류: {e}")
        return False

def test_instagram_token():
    """Instagram 토큰 테스트"""
    print("\n📱 Instagram API 토큰 테스트...")
    
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    business_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
    
    if not access_token:
        print("❌ INSTAGRAM_ACCESS_TOKEN이 설정되지 않았습니다.")
        return False
    
    if not business_account_id:
        print("❌ INSTAGRAM_BUSINESS_ACCOUNT_ID가 설정되지 않았습니다.")
        return False
    
    try:
        # Instagram Graph API 테스트
        url = f"https://graph.instagram.com/{business_account_id}"
        params = {
            'fields': 'id,name,username,account_type,media_count',
            'access_token': access_token
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Instagram API 토큰이 유효합니다!")
            print(f"   계정명: {data.get('name', 'N/A')}")
            print(f"   사용자명: @{data.get('username', 'N/A')}")
            print(f"   계정 타입: {data.get('account_type', 'N/A')}")
            print(f"   미디어 수: {data.get('media_count', 'N/A')}")
            return True
        else:
            print(f"❌ Instagram API 오류: {response.status_code}")
            error_data = response.json()
            print(f"   오류 메시지: {error_data}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Instagram API 요청 시간 초과")
        return False
    except Exception as e:
        print(f"❌ Instagram API 테스트 오류: {e}")
        return False

def test_content_generation():
    """AI 콘텐츠 생성 테스트"""
    print("\n🧪 AI 콘텐츠 생성 테스트...")
    
    try:
        # Instagram 포스터 임포트 및 테스트
        from instagram_auto_poster import InstagramAutoPoster
        
        poster = InstagramAutoPoster()
        
        # 테스트 비즈니스 정보
        test_business = {
            'name': '테스트 카페',
            'industry': 'restaurant',
            'target_audience': '20-30대 직장인',
            'brand_voice': '친근하고 따뜻한'
        }
        
        print("   📝 AI 콘텐츠 생성 중...")
        content = poster.generate_content_with_ai(test_business)
        
        if content['success']:
            print("✅ AI 콘텐츠 생성 성공!")
            print(f"   캡션 미리보기: {content['raw_caption'][:50]}...")
            print(f"   해시태그 수: {len(content['hashtags'])}개")
            
            # 이미지 생성 테스트
            print("   🖼️ AI 이미지 생성 중...")
            image_url = poster.generate_image_with_dalle("restaurant marketing content")
            
            if image_url:
                print("✅ AI 이미지 생성 성공!")
                print(f"   이미지 URL: {image_url[:50]}...")
            else:
                print("⚠️ AI 이미지 생성 실패")
            
            return True
        else:
            print("❌ AI 콘텐츠 생성 실패")
            return False
            
    except ImportError as e:
        print(f"❌ 모듈 임포트 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 콘텐츠 생성 테스트 오류: {e}")
        return False

def main():
    """메인 검증 함수"""
    print("🔍 Instagram AI Marketing 토큰 검증")
    print("=" * 60)
    
    # .env 파일 로드
    load_dotenv()
    
    results = {}
    
    # 각 토큰 테스트
    results['openai'] = test_openai_token()
    results['instagram'] = test_instagram_token()
    
    # 통합 기능 테스트
    if results['openai']:
        results['content_generation'] = test_content_generation()
    else:
        print("\n⏭️ OpenAI 토큰이 유효하지 않아 콘텐츠 생성 테스트를 건너뜁니다.")
        results['content_generation'] = False
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 토큰 검증 결과")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name}: {'통과' if result else '실패'}")
    
    print(f"\n🎯 결과: {passed_tests}/{total_tests} 테스트 통과")
    
    if passed_tests == total_tests:
        print("🎉 모든 토큰이 올바르게 설정되었습니다!")
        print("이제 Instagram AI 마케팅 플랫폼을 사용할 수 있습니다.")
    elif results['openai'] and results['instagram']:
        print("✅ 기본 토큰들이 유효합니다.")
        print("일부 고급 기능에 제한이 있을 수 있습니다.")
    else:
        print("⚠️ 토큰 설정을 확인하고 수정해주세요.")
    
    print("\n🚀 다음 단계:")
    print("1. python main.py 로 서버 실행")
    print("2. http://localhost:8000 접속")
    print("3. API 문서 확인: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
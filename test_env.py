# test_env.py - 환경변수 설정 확인 테스트
import os
from dotenv import load_dotenv

def test_environment_variables():
    """환경변수 설정 상태 확인"""
    print("🔍 환경변수 테스트 시작...")
    print("=" * 50)
    
    # .env 파일 로드
    load_dotenv()
    
    # 각 환경변수 확인
    variables = {
        'OPENAI_API_KEY': 'OpenAI API 키',
        'INSTAGRAM_ACCESS_TOKEN': 'Instagram 액세스 토큰',
        'INSTAGRAM_BUSINESS_ACCOUNT_ID': 'Instagram 비즈니스 계정 ID',
        'SECRET_KEY': 'JWT 시크릿 키'
    }
    
    results = {}
    
    for var_name, description in variables.items():
        value = os.getenv(var_name)
        if value:
            # 보안을 위해 일부만 표시
            if len(value) > 10:
                masked_value = value[:8] + "..." + value[-4:]
            else:
                masked_value = value[:3] + "..."
            
            print(f"✅ {description}: 설정됨 ({masked_value})")
            results[var_name] = True
        else:
            print(f"❌ {description}: 없음")
            results[var_name] = False
    
    print("=" * 50)
    
    # 결과 요약
    total_vars = len(variables)
    set_vars = sum(results.values())
    
    print(f"📊 결과: {set_vars}/{total_vars} 환경변수 설정됨")
    
    if results['OPENAI_API_KEY']:
        print("🤖 AI 콘텐츠 생성 가능")
    else:
        print("⚠️ AI 기능 제한됨 (기본 템플릿 사용)")
    
    if results['INSTAGRAM_ACCESS_TOKEN'] and results['INSTAGRAM_BUSINESS_ACCOUNT_ID']:
        print("📱 실제 Instagram 포스팅 가능")
    else:
        print("⚠️ Instagram 포스팅 테스트 모드")
    
    return results

def test_instagram_poster():
    """Instagram 포스터 기능 테스트"""
    try:
        from instagram_auto_poster import InstagramAutoPoster
        
        print("\n🧪 Instagram 포스터 기능 테스트...")
        poster = InstagramAutoPoster()
        
        # 테스트 비즈니스 정보
        test_business = {
            'name': '테스트 카페',
            'industry': 'restaurant',
            'target_audience': '20-30대 직장인',
            'brand_voice': '친근하고 따뜻한'
        }
        
        print("📝 AI 콘텐츠 생성 테스트...")
        content = poster.generate_content_with_ai(test_business)
        
        if content['success']:
            print("✅ AI 콘텐츠 생성 성공!")
            print(f"   캡션: {content['raw_caption'][:50]}...")
            print(f"   해시태그: {content['hashtags'][:3]}")
        else:
            print("⚠️ AI 콘텐츠 생성 실패 (기본 템플릿 사용)")
        
        print("\n🖼️ 이미지 생성 테스트...")
        image_url = poster.generate_image_with_dalle("cafe marketing content")
        
        if image_url:
            print("✅ 이미지 생성 성공!")
            print(f"   URL: {image_url[:50]}...")
        else:
            print("⚠️ 이미지 생성 실패")
        
        return True
        
    except ImportError as e:
        print(f"❌ 모듈 import 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        return False

if __name__ == "__main__":
    # 환경변수 테스트
    env_results = test_environment_variables()
    
    # Instagram 포스터 테스트
    test_instagram_poster()
    
    print("\n🎯 테스트 완료!")
    print("\n💡 다음 단계:")
    if not env_results.get('OPENAI_API_KEY'):
        print("   1. OpenAI API 키를 .env 파일에 추가하세요")
    if not env_results.get('INSTAGRAM_ACCESS_TOKEN'):
        print("   2. Instagram API 토큰을 설정하세요 (선택사항)")
    print("   3. Railway Variables에도 동일하게 설정하세요")
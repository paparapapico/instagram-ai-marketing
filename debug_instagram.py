# debug_instagram.py - Instagram 포스팅 문제 진단 및 수정
import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def debug_instagram_api():
    """Instagram API 설정 상태 확인"""
    print("🔍 Instagram API 디버깅 시작...")
    print("=" * 50)
    
    # 환경변수 확인
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    business_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
    
    if not access_token:
        print("❌ INSTAGRAM_ACCESS_TOKEN이 설정되지 않았습니다.")
        print("💡 해결방법:")
        print("   1. Instagram Business 계정 필요")
        print("   2. Facebook Developer Console에서 앱 생성")
        print("   3. Instagram Basic Display API 또는 Instagram Graph API 설정")
        return False
    
    if not business_account_id:
        print("❌ INSTAGRAM_BUSINESS_ACCOUNT_ID가 설정되지 않았습니다.")
        return False
    
    print(f"✅ Access Token: {access_token[:10]}...{access_token[-5:]}")
    print(f"✅ Business Account ID: {business_account_id}")
    
    # API 연결 테스트
    print("\n🧪 Instagram API 연결 테스트...")
    
    try:
        # 계정 정보 조회 테스트
        url = f"https://graph.instagram.com/{business_account_id}"
        params = {
            'fields': 'name,username,account_type',
            'access_token': access_token
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if response.status_code == 200:
            print("✅ Instagram API 연결 성공!")
            print(f"   계정명: {data.get('name', 'N/A')}")
            print(f"   사용자명: @{data.get('username', 'N/A')}")
            print(f"   계정 타입: {data.get('account_type', 'N/A')}")
            return True
        else:
            print(f"❌ API 연결 실패 (상태코드: {response.status_code})")
            print(f"   오류: {data}")
            return False
            
    except Exception as e:
        print(f"❌ API 테스트 오류: {e}")
        return False

def test_image_url_accessibility():
    """이미지 URL 접근 가능성 테스트"""
    print("\n🖼️ 이미지 URL 접근성 테스트...")
    
    # 테스트용 이미지 URL들
    test_images = [
        "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=1024&q=80",
        "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1024&q=80",
        "https://picsum.photos/1024/1024"
    ]
    
    for i, image_url in enumerate(test_images, 1):
        try:
            response = requests.head(image_url, timeout=10)
            if response.status_code == 200:
                print(f"✅ 테스트 이미지 {i}: 접근 가능")
                print(f"   URL: {image_url}")
                return image_url
            else:
                print(f"❌ 테스트 이미지 {i}: 접근 불가 ({response.status_code})")
        except Exception as e:
            print(f"❌ 테스트 이미지 {i}: 오류 - {e}")
    
    return None

def create_safe_instagram_poster():
    """안전한 Instagram 포스터 클래스 생성"""
    
    class SafeInstagramPoster:
        def __init__(self):
            self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
            self.business_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
            self.base_url = "https://graph.facebook.com/v18.0"
            
        def validate_setup(self):
            """설정 유효성 검사"""
            if not self.access_token or not self.business_account_id:
                return False, "Instagram API 설정이 완료되지 않았습니다"
            return True, "설정 완료"
        
        def test_account_access(self):
            """계정 접근 테스트"""
            try:
                url = f"https://graph.instagram.com/{self.business_account_id}"
                params = {
                    'fields': 'name,username',
                    'access_token': self.access_token
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    return True, response.json()
                else:
                    return False, f"API 오류: {response.status_code} - {response.text}"
                    
            except Exception as e:
                return False, f"연결 오류: {str(e)}"
        
        def create_media_container_safe(self, image_url, caption):
            """안전한 미디어 컨테이너 생성"""
            try:
                # 이미지 URL 검증
                img_response = requests.head(image_url, timeout=10)
                if img_response.status_code != 200:
                    return False, f"이미지 URL 접근 불가: {img_response.status_code}"
                
                # 미디어 컨테이너 생성
                url = f"{self.base_url}/{self.business_account_id}/media"
                params = {
                    'image_url': image_url,
                    'caption': caption[:2200],  # Instagram 캡션 길이 제한
                    'access_token': self.access_token
                }
                
                print(f"📤 미디어 컨테이너 생성 요청...")
                print(f"   이미지: {image_url}")
                print(f"   캡션 길이: {len(caption)} 글자")
                
                response = requests.post(url, params=params, timeout=30)
                data = response.json()
                
                if response.status_code == 200 and 'id' in data:
                    return True, data['id']
                else:
                    return False, f"컨테이너 생성 실패: {response.status_code} - {data}"
                    
            except Exception as e:
                return False, f"컨테이너 생성 오류: {str(e)}"
        
        def publish_media_safe(self, creation_id):
            """안전한 미디어 발행"""
            try:
                url = f"{self.base_url}/{self.business_account_id}/media_publish"
                params = {
                    'creation_id': creation_id,
                    'access_token': self.access_token
                }
                
                print(f"📤 미디어 발행 요청...")
                print(f"   컨테이너 ID: {creation_id}")
                
                response = requests.post(url, params=params, timeout=30)
                data = response.json()
                
                if response.status_code == 200 and 'id' in data:
                    return True, data['id']
                else:
                    return False, f"발행 실패: {response.status_code} - {data}"
                    
            except Exception as e:
                return False, f"발행 오류: {str(e)}"
        
        def post_to_instagram_safe(self, caption, image_url):
            """안전한 Instagram 포스팅"""
            print("🚀 안전한 Instagram 포스팅 시작...")
            
            # 1. 설정 검증
            valid, message = self.validate_setup()
            if not valid:
                return False, message
            
            # 2. 계정 접근 테스트
            accessible, account_data = self.test_account_access()
            if not accessible:
                return False, f"계정 접근 실패: {account_data}"
            
            print(f"✅ 계정 확인됨: @{account_data.get('username', 'unknown')}")
            
            # 3. 미디어 컨테이너 생성
            container_success, container_result = self.create_media_container_safe(image_url, caption)
            if not container_success:
                return False, container_result
            
            creation_id = container_result
            print(f"✅ 미디어 컨테이너 생성됨: {creation_id}")
            
            # 4. 잠시 대기
            import time
            print("⏳ 3초 대기...")
            time.sleep(3)
            
            # 5. 미디어 발행
            publish_success, publish_result = self.publish_media_safe(creation_id)
            if not publish_success:
                return False, publish_result
            
            post_id = publish_result
            print(f"🎉 포스팅 성공! Post ID: {post_id}")
            
            return True, post_id
    
    return SafeInstagramPoster()

def run_comprehensive_test():
    """종합 테스트 실행"""
    print("🧪 Instagram 포스팅 종합 테스트")
    print("=" * 50)
    
    # 1. API 설정 확인
    if not debug_instagram_api():
        print("\n❌ Instagram API 설정에 문제가 있습니다.")
        print("💡 Instagram API 없이도 테스트 모드로 작동 가능합니다.")
        return
    
    # 2. 이미지 URL 테스트
    test_image_url = test_image_url_accessibility()
    if not test_image_url:
        print("❌ 접근 가능한 테스트 이미지를 찾을 수 없습니다.")
        return
    
    # 3. 안전한 포스터로 테스트
    poster = create_safe_instagram_poster()
    
    test_caption = """🧪 Instagram AI 마케팅 플랫폼 테스트 포스팅

이 포스트는 AI 마케팅 자동화 시스템의 테스트입니다.

#테스트 #AI마케팅 #자동화 #인스타그램 #마케팅플랫폼"""
    
    print(f"\n📝 테스트 캡션: {test_caption[:50]}...")
    print(f"🖼️ 테스트 이미지: {test_image_url}")
    
    # 사용자 확인
    confirmation = input("\n⚠️ 실제 Instagram에 테스트 포스팅하시겠습니까? (y/N): ")
    
    if confirmation.lower() == 'y':
        success, result = poster.post_to_instagram_safe(test_caption, test_image_url)
        
        if success:
            print(f"\n🎉 테스트 포스팅 성공!")
            print(f"   Post ID: {result}")
            print(f"   Instagram에서 확인해보세요!")
        else:
            print(f"\n❌ 테스트 포스팅 실패:")
            print(f"   오류: {result}")
    else:
        print("\n✅ 테스트를 건너뛰었습니다.")
    
    print("\n🎯 종합 테스트 완료!")

if __name__ == "__main__":
    run_comprehensive_test()
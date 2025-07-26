# instagram_auto_poster.py 상단 수정
import requests
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class InstagramAutoPoster:
    def __init__(self):
        self.instagram_account_id = "17841475725247504"
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://graph.facebook.com/v18.0"
    
    def generate_content_with_ai(self, business_info):
        """AI로 Instagram 콘텐츠 생성 (v1.x 호환)"""
        if not self.openai_api_key:
            return self._get_fallback_content()
            
        try:
            import openai
            
            # 새로운 방식으로 클라이언트 생성
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            prompt = f"""
            다음 비즈니스를 위한 Instagram 포스트를 작성해주세요:
            
            비즈니스: {business_info.get('name', '마케팅 자동화')}
            업종: {business_info.get('industry', '소프트웨어')}
            타겟: {business_info.get('target', '소상공인')}
            
            JSON 형식으로 응답:
            {{
                "caption": "캡션 내용",
                "hashtags": ["#해시태그1", "#해시태그2", "#해시태그3", "#해시태그4", "#해시태그5"]
            }}
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            content_text = response.choices[0].message.content
            
            # JSON 파싱 시도
            try:
                content = json.loads(content_text)
                full_caption = f"{content['caption']}\n\n{' '.join(content['hashtags'])}"
                
                return {
                    'caption': full_caption,
                    'hashtags': content['hashtags'],
                    'raw_caption': content['caption']
                }
            except:
                # JSON 파싱 실패 시 텍스트 그대로 사용
                return {
                    'caption': content_text + "\n\n#마케팅자동화 #인스타그램 #비즈니스",
                    'hashtags': ['#마케팅자동화', '#인스타그램', '#비즈니스'],
                    'raw_caption': content_text
                }
            
        except Exception as e:
            print(f"AI 콘텐츠 생성 오류: {e}")
            return self._get_fallback_content()
    
    def generate_image_with_dalle(self, description):
        """DALL-E로 이미지 생성 (v1.x 호환)"""
        if not self.openai_api_key:
            return "https://images.unsplash.com/photo-1611224923853-80b023f02d71?auto=format&fit=crop&w=1024&q=80"
            
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.images.generate(
                model="dall-e-2",  # dall-e-3 대신 dall-e-2 사용 (더 안정적)
                prompt=f"{description}, professional, high quality, social media style",
                n=1,
                size="1024x1024"
            )
            
            return response.data[0].url
            
        except Exception as e:
            print(f"이미지 생성 오류: {e}")
            return "https://images.unsplash.com/photo-1611224923853-80b023f02d71?auto=format&fit=crop&w=1024&q=80"
    
    
    def _get_fallback_content(self):
        """AI 실패 시 대체 콘텐츠"""
        return {
            'caption': "🚀 Instagram 마케팅 자동화로 비즈니스를 성장시키세요!\n\n#마케팅자동화 #인스타그램 #비즈니스 #성장 #자동화",
            'hashtags': ['#마케팅자동화', '#인스타그램', '#비즈니스', '#성장', '#자동화'],
            'raw_caption': "🚀 Instagram 마케팅 자동화로 비즈니스를 성장시키세요!"
        }
    
    def generate_image_with_dalle(self, description):
        """DALL-E로 이미지 생성"""
        if not self.openai_client:
            print("OpenAI API 키가 설정되지 않았습니다. 기본 이미지를 사용합니다.")
            return "https://via.placeholder.com/1024x1024/4285f4/white?text=Instagram+Marketing+Bot"
            
        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=f"{description}, professional, high quality, social media style, bright colors",
                n=1,
                size="1024x1024"
            )
            
            image_url = response.data[0].url
            print(f"✅ 이미지 생성 성공: {image_url}")
            return image_url
            
        except Exception as e:
            print(f"이미지 생성 오류: {e}")
            # 테스트용 기본 이미지 URL
            return "https://via.placeholder.com/1024x1024/4285f4/white?text=Instagram+Marketing+Bot"
    
    def create_media_container(self, image_url, caption):
        """Instagram 미디어 컨테이너 생성"""
        url = f"{self.base_url}/{self.instagram_account_id}/media"
        
        params = {
            'image_url': image_url,
            'caption': caption,
            'access_token': self.access_token
        }
        
        try:
            response = requests.post(url, params=params)
            data = response.json()
            
            if response.status_code == 200 and 'id' in data:
                print(f"✅ 미디어 컨테이너 생성 성공: {data['id']}")
                return data['id']
            else:
                print(f"❌ 미디어 컨테이너 생성 실패: {data}")
                return None
                
        except Exception as e:
            print(f"미디어 컨테이너 생성 오류: {e}")
            return None
    
    def publish_media(self, creation_id):
        """미디어 게시"""
        url = f"{self.base_url}/{self.instagram_account_id}/media_publish"
        
        params = {
            'creation_id': creation_id,
            'access_token': self.access_token
        }
        
        try:
            response = requests.post(url, params=params)
            data = response.json()
            
            if response.status_code == 200 and 'id' in data:
                print(f"🎉 Instagram 포스팅 성공! Post ID: {data['id']}")
                return data['id']
            else:
                print(f"❌ 포스팅 실패: {data}")
                return None
                
        except Exception as e:
            print(f"포스팅 오류: {e}")
            return None
    
    def post_to_instagram(self, business_info=None, custom_caption=None, custom_image_url=None):
        """Instagram에 자동 포스팅"""
        print("🚀 Instagram 자동 포스팅 시작...")
        
        # 1단계: 콘텐츠 생성
        if custom_caption:
            caption = custom_caption
        else:
            if not business_info:
                business_info = {
                    'name': 'Instagram 마케팅 봇',
                    'industry': '마케팅 자동화',
                    'target': '소상공인 및 개인사업자'
                }
            
            content = self.generate_content_with_ai(business_info)
            caption = content['caption']
        
        print(f"📝 생성된 캡션: {caption}")
        
        # 2단계: 이미지 준비
        if custom_image_url:
            image_url = custom_image_url
        else:
            image_description = "Instagram marketing automation, modern design, professional business"
            image_url = self.generate_image_with_dalle(image_description)
        
        print(f"🖼️ 사용할 이미지: {image_url}")
        
        # 3단계: 미디어 컨테이너 생성
        creation_id = self.create_media_container(image_url, caption)
        if not creation_id:
            return False
        
        # 잠시 대기 (Instagram API 권장)
        print("⏳ 3초 대기 중...")
        time.sleep(3)
        
        # 4단계: 실제 게시
        post_id = self.publish_media(creation_id)
        
        if post_id:
            print(f"✅ 포스팅 완료! Instagram에서 확인하세요.")
            return post_id
        else:
            print("❌ 포스팅 실패")
            return False
    
    def get_account_info(self):
        """Instagram 계정 정보 확인"""
        url = f"https://graph.instagram.com/{self.instagram_account_id}"
        params = {
            'fields': 'name,username,profile_picture_url,media_count,followers_count',
            'access_token': self.access_token
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if response.status_code == 200:
                print("📊 Instagram 계정 정보:")
                print(f"   이름: {data.get('name', 'N/A')}")
                print(f"   사용자명: @{data.get('username', 'N/A')}")
                print(f"   게시물 수: {data.get('media_count', 'N/A')}")
                print(f"   팔로워 수: {data.get('followers_count', 'N/A')}")
                return data
            else:
                print(f"계정 정보 조회 실패: {data}")
                return None
                
        except Exception as e:
            print(f"계정 정보 조회 오류: {e}")
            return None
    
    def get_recent_posts(self, limit=5):
        """최근 게시물 목록 가져오기"""
        url = f"https://graph.instagram.com/{self.instagram_account_id}/media"
        params = {
            'fields': 'id,caption,media_type,media_url,timestamp,like_count,comments_count',
            'limit': limit,
            'access_token': self.access_token
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if response.status_code == 200 and 'data' in data:
                print(f"📱 최근 게시물 {len(data['data'])}개:")
                for i, post in enumerate(data['data'], 1):
                    print(f"   {i}. {post.get('caption', 'No caption')[:50]}...")
                    print(f"      좋아요: {post.get('like_count', 0)}, 댓글: {post.get('comments_count', 0)}")
                return data['data']
            else:
                print(f"게시물 조회 실패: {data}")
                return []
                
        except Exception as e:
            print(f"게시물 조회 오류: {e}")
            return []

# 사용 예시 및 테스트
def main():
    """메인 실행 함수"""
    
    # Instagram 포스터 초기화
    poster = InstagramAutoPoster()
    
    print("=== Instagram 자동 포스팅 시스템 테스트 ===\n")
    
    # 1. 계정 정보 확인
    print("1️⃣ Instagram 계정 정보 확인:")
    account_info = poster.get_account_info()
    print()
    
    # 2. 최근 게시물 확인
    print("2️⃣ 최근 게시물 확인:")
    recent_posts = poster.get_recent_posts(3)
    print()
    
    # 3. 자동 포스팅 테스트
    print("3️⃣ 자동 포스팅 테스트:")
    
    # 테스트용 비즈니스 정보
    test_business = {
        'name': 'Automarketing Bot',
        'industry': 'Instagram 마케팅 자동화',
        'target': '소상공인, 개인사업자, 마케팅 담당자'
    }
    
    # 실제 포스팅 (주의: 실제 Instagram에 업로드됩니다!)
    user_input = input("실제 Instagram에 포스팅하시겠습니까? (y/n): ")
    
    if user_input.lower() == 'y':
        post_id = poster.post_to_instagram(test_business)
        if post_id:
            print(f"\n🎉 성공! Instagram에서 포스트를 확인하세요.")
            print(f"Post ID: {post_id}")
        else:
            print("\n❌ 포스팅에 실패했습니다.")
    else:
        print("테스트를 건너뛰었습니다.")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()
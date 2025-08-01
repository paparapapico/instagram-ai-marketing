# instagram_auto_poster.py - 실제 Instagram 포스팅 및 AI 생성 기능
import requests
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import base64
from io import BytesIO
from PIL import Image

load_dotenv()

class InstagramAutoPoster:
    def __init__(self):
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.business_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://graph.facebook.com/v18.0"
        
        # API 키 확인
        if not self.openai_api_key:
            print("⚠️ OpenAI API 키가 설정되지 않았습니다. AI 기능이 제한됩니다.")
        
        if not self.access_token or not self.business_account_id:
            print("⚠️ Instagram API 키가 설정되지 않았습니다. 실제 포스팅이 제한됩니다.")
    
    def generate_content_with_ai(self, business_info):
        """AI로 Instagram 콘텐츠 생성"""
        if not self.openai_api_key:
            print("OpenAI API 키가 없습니다. 기본 콘텐츠를 사용합니다.")
            return self._get_fallback_content(business_info)
            
        try:
            # OpenAI 라이브러리 동적 import
            try:
                import openai
                client = openai.OpenAI(api_key=self.openai_api_key)
            except ImportError:
                print("OpenAI 라이브러리가 설치되지 않았습니다. pip install openai로 설치하세요.")
                return self._get_fallback_content(business_info)
            except Exception as e:
                print(f"OpenAI 클라이언트 생성 오류: {e}")
                return self._get_fallback_content(business_info)
            
            # 프롬프트 생성
            prompt = self._create_content_prompt(business_info)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
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
                    'raw_caption': content['caption'],
                    'success': True
                }
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트 그대로 사용
                hashtags = self._extract_hashtags_from_text(content_text, business_info)
                return {
                    'caption': content_text + "\n\n" + " ".join(hashtags),
                    'hashtags': hashtags,
                    'raw_caption': content_text,
                    'success': True
                }
            
        except Exception as e:
            print(f"AI 콘텐츠 생성 오류: {e}")
            return self._get_fallback_content(business_info)
    
    def _create_content_prompt(self, business_info):
        """콘텐츠 생성을 위한 프롬프트 생성"""
        business_name = business_info.get('name', '우리 비즈니스')
        industry = business_info.get('industry', '일반')
        target_audience = business_info.get('target_audience', '일반 고객')
        brand_voice = business_info.get('brand_voice', '친근하고 전문적인')
        
        prompt = f"""
다음 비즈니스를 위한 Instagram 포스트를 작성해주세요:

비즈니스명: {business_name}
업종: {industry}
타겟 고객: {target_audience}
브랜드 톤: {brand_voice}

요구사항:
1. 매력적이고 참여를 유도하는 캡션 작성
2. 관련성 높은 해시태그 5-10개 포함
3. 이모지 적절히 사용
4. 한국어로 작성
5. JSON 형식으로 응답

JSON 형식:
{{
    "caption": "캡션 내용 (이모지 포함)",
    "hashtags": ["#해시태그1", "#해시태그2", "#해시태그3", "#해시태그4", "#해시태그5"]
}}
"""
        return prompt
    
    def _extract_hashtags_from_text(self, text, business_info):
        """텍스트에서 해시태그 추출 또는 생성"""
        industry = business_info.get('industry', '일반')
        
        # 업종별 기본 해시태그
        industry_hashtags = {
            'restaurant': ['#맛집', '#카페', '#음식', '#맛스타그램', '#foodie'],
            'fashion': ['#패션', '#스타일', '#ootd', '#fashion', '#style'],
            'beauty': ['#뷰티', '#화장품', '#스킨케어', '#메이크업', '#beauty'],
            'fitness': ['#피트니스', '#운동', '#헬스', '#다이어트', '#workout'],
            'retail': ['#쇼핑', '#신상품', '#할인', '#세일', '#shopping'],
            'software': ['#IT', '#소프트웨어', '#기술', '#앱', '#tech'],
            'consulting': ['#컨설팅', '#비즈니스', '#전문가', '#상담', '#consulting']
        }
        
        hashtags = industry_hashtags.get(industry, ['#비즈니스', '#서비스', '#품질', '#고객만족', '#추천'])
        hashtags.append('#' + business_info.get('name', '').replace(' ', ''))
        
        return hashtags[:8]  # 최대 8개 제한
    
    def generate_image_with_dalle(self, description):
        """DALL-E로 이미지 생성"""
        if not self.openai_api_key:
            print("OpenAI API 키가 없습니다. 기본 이미지를 사용합니다.")
            return self._get_stock_image_url(description)
            
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            # 한국어 설명을 영어로 변환
            english_description = self._translate_to_english(description)
            
            response = client.images.generate(
                model="dall-e-2",
                prompt=f"{english_description}, professional, high quality, social media style, clean background",
                n=1,
                size="1024x1024"
            )
            
            image_url = response.data[0].url
            print(f"✅ 이미지 생성 성공: {image_url}")
            return image_url
            
        except Exception as e:
            print(f"이미지 생성 오류: {e}")
            return self._get_stock_image_url(description)
    
    def _translate_to_english(self, korean_text):
        """간단한 한국어-영어 변환"""
        translations = {
            '카페': 'cafe coffee shop',
            '음식점': 'restaurant food',
            '패션': 'fashion clothing',
            '뷰티': 'beauty cosmetics',
            '피트니스': 'fitness gym',
            '소프트웨어': 'software technology',
            '마케팅': 'marketing business'
        }
        
        for korean, english in translations.items():
            if korean in korean_text:
                return english
        
        return 'professional business marketing content'
    
    def _get_stock_image_url(self, description):
        """무료 스톡 이미지 URL 반환"""
        # Unsplash에서 관련 이미지 URL 반환
        keywords = {
            'cafe': 'coffee-shop',
            'restaurant': 'restaurant',
            'fashion': 'fashion',
            'beauty': 'beauty',
            'fitness': 'fitness',
            'software': 'technology',
            'marketing': 'marketing'
        }
        
        keyword = 'business'
        for key, value in keywords.items():
            if key in description.lower():
                keyword = value
                break
        
        return f"https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=1024&q=80&{keyword}"
    
    def create_media_container(self, image_url, caption):
        """Instagram 미디어 컨테이너 생성"""
        if not self.access_token or not self.business_account_id:
            print("Instagram API 설정이 없습니다. 테스트 모드로 실행됩니다.")
            return self._create_test_post(image_url, caption)
        
        url = f"{self.base_url}/{self.business_account_id}/media"
        
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
        if not self.access_token or not self.business_account_id:
            print("Instagram API 설정이 없습니다. 테스트 포스팅을 시뮬레이션합니다.")
            return f"test_post_{int(time.time())}"
        
        url = f"{self.base_url}/{self.business_account_id}/media_publish"
        
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
    
    def _create_test_post(self, image_url, caption):
        """테스트 포스트 생성 (API 없을 때)"""
        test_id = f"test_container_{int(time.time())}"
        print(f"🧪 테스트 모드: 미디어 컨테이너 생성됨 - {test_id}")
        print(f"📸 이미지: {image_url}")
        print(f"📝 캡션: {caption[:100]}...")
        return test_id
    
    def post_to_instagram(self, business_info=None, custom_caption=None, custom_image_url=None):
        """Instagram에 자동 포스팅 (통합 함수)"""
        print("🚀 Instagram 자동 포스팅 시작...")
        
        # 1단계: 콘텐츠 생성
        if custom_caption:
            caption = custom_caption
        else:
            if not business_info:
                business_info = {
                    'name': 'Instagram 마케팅 봇',
                    'industry': '마케팅 자동화',
                    'target_audience': '소상공인 및 개인사업자'
                }
            
            content = self.generate_content_with_ai(business_info)
            caption = content['caption']
        
        print(f"📝 생성된 캡션: {caption[:100]}...")
        
        # 2단계: 이미지 준비
        if custom_image_url:
            image_url = custom_image_url
        else:
            image_description = f"{business_info.get('industry', 'business')} marketing content"
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
            print(f"✅ 포스팅 완료!")
            return post_id
        else:
            print("❌ 포스팅 실패")
            return False
    
    def _get_fallback_content(self, business_info):
        """AI 실패 시 대체 콘텐츠"""
        business_name = business_info.get('name', '우리 비즈니스')
        industry = business_info.get('industry', '서비스')
        
        # 업종별 맞춤형 대체 콘텐츠
        industry_content = {
            'restaurant': {
                'caption': f"🍽️ {business_name}에서 특별한 맛의 경험을 즐겨보세요! 신선한 재료와 정성으로 준비한 요리가 기다리고 있습니다.",
                'hashtags': ['#맛집', '#맛스타그램', '#음식', '#restaurant', '#delicious']
            },
            'fashion': {
                'caption': f"✨ {business_name}의 새로운 컬렉션이 출시되었습니다! 트렌디하고 스타일리시한 제품들을 만나보세요.",
                'hashtags': ['#패션', '#스타일', '#ootd', '#fashion', '#trendy']
            },
            'beauty': {
                'caption': f"💄 {business_name}과 함께 더 아름다운 당신을 발견하세요! 전문가가 엄선한 뷰티 제품들이 준비되어 있습니다.",
                'hashtags': ['#뷰티', '#화장품', '#beauty', '#skincare', '#makeup']
            },
            'fitness': {
                'caption': f"💪 {business_name}에서 건강한 삶을 시작하세요! 전문 트레이너와 함께 목표를 달성해보세요.",
                'hashtags': ['#피트니스', '#운동', '#헬스', '#fitness', '#workout']
            }
        }
        
        content = industry_content.get(industry, {
            'caption': f"🚀 {business_name}과 함께 성장하는 비즈니스! 최고의 서비스로 고객 만족을 실현합니다.",
            'hashtags': ['#비즈니스', '#서비스', '#고객만족', '#quality', '#professional']
        })
        
        full_caption = f"{content['caption']}\n\n{' '.join(content['hashtags'])}"
        
        return {
            'caption': full_caption,
            'hashtags': content['hashtags'],
            'raw_caption': content['caption'],
            'success': True
        }
    
    def get_account_info(self):
        """Instagram 계정 정보 확인"""
        if not self.access_token or not self.business_account_id:
            print("Instagram API 설정이 없습니다.")
            return {
                'name': '테스트 계정',
                'username': 'test_account',
                'media_count': 0,
                'followers_count': 0
            }
            
        url = f"https://graph.instagram.com/{self.business_account_id}"
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

# 테스트 함수
def test_instagram_poster():
    """Instagram 포스터 테스트"""
    poster = InstagramAutoPoster()
    
    # 테스트 비즈니스 정보
    test_business = {
        'name': '테스트 카페',
        'industry': 'restaurant',
        'target_audience': '20-30대 직장인',
        'brand_voice': '친근하고 따뜻한'
    }
    
    print("🧪 Instagram 포스터 테스트 시작...")
    
    # AI 콘텐츠 생성 테스트
    content = poster.generate_content_with_ai(test_business)
    print(f"✅ 콘텐츠 생성 결과: {content['caption'][:100]}...")
    
    # 이미지 생성 테스트
    image_url = poster.generate_image_with_dalle("cafe marketing content")
    print(f"✅ 이미지 생성 결과: {image_url}")
    
    # 통합 포스팅 테스트
    result = poster.post_to_instagram(test_business)
    print(f"✅ 포스팅 테스트 결과: {result}")

if __name__ == "__main__":
    test_instagram_poster()
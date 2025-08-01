# openai_helper.py - OpenAI API 통합 파일
import os
import json
from typing import Dict, Any

def generate_with_openai(business_info: Dict[str, str]) -> Dict[str, Any]:
    """OpenAI GPT를 사용한 실제 AI 콘텐츠 생성"""
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key or not openai_key.startswith('sk-'):
        return {"success": False, "error": "OpenAI API key not found"}
    
    try:
        # OpenAI 라이브러리 설치 확인
        try:
            import openai
        except ImportError:
            return {"success": False, "error": "openai package not installed. Run: pip install openai"}
        
        # OpenAI 클라이언트 생성
        client = openai.OpenAI(api_key=openai_key)
        
        # 프롬프트 생성
        prompt = create_content_prompt(business_info)
        
        # API 호출
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 전문 Instagram 마케팅 콘텐츠 작성자입니다. 한국어로 매력적이고 참여도 높은 Instagram 포스트를 작성해주세요."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        content_text = response.choices[0].message.content
        
        # JSON 파싱 시도
        try:
            parsed_content = json.loads(content_text)
            
            return {
                "success": True,
                "caption": parsed_content.get('caption', ''),
                "hashtags": parsed_content.get('hashtags', []),
                "full_caption": f"{parsed_content.get('caption', '')}\n\n{' '.join(parsed_content.get('hashtags', []))}",
                "type": "openai_generated"
            }
            
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트에서 추출
            return parse_text_content(content_text, business_info)
            
    except Exception as e:
        return {"success": False, "error": f"OpenAI API error: {str(e)}"}

def create_content_prompt(business_info: Dict[str, str]) -> str:
    """OpenAI용 프롬프트 생성"""
    
    business_name = business_info.get('business_name', '우리 비즈니스')
    industry = business_info.get('industry', 'general')
    target_audience = business_info.get('target_audience', '일반 고객')
    brand_voice = business_info.get('brand_voice', '친근하고 전문적인')
    
    # 업종별 특화 프롬프트
    industry_context = {
        'restaurant': '음식점, 카페, 맛집으로서 고객들에게 맛있는 음식과 좋은 분위기를 제공',
        'fashion': '패션 브랜드로서 트렌디하고 스타일리시한 의류와 액세서리를 제공',
        'beauty': '뷰티 브랜드로서 화장품, 스킨케어 제품으로 고객의 아름다움을 지원',
        'fitness': '피트니스 센터/브랜드로서 건강한 라이프스타일과 운동을 통한 목표 달성 지원'
    }
    
    context = industry_context.get(industry, '전문적인 서비스를 제공하는 비즈니스')
    
    prompt = f"""
다음 비즈니스를 위한 Instagram 포스트를 작성해주세요:

**비즈니스 정보:**
- 이름: {business_name}
- 업종: {industry} ({context})
- 타겟 고객: {target_audience}
- 브랜드 톤앤매너: {brand_voice}

**작성 요구사항:**
1. 매력적이고 참여를 유도하는 한국어 캡션 (150-200자)
2. 관련성 높은 한국어 해시태그 6-8개
3. 적절한 이모지 사용
4. 타겟 고객의 관심을 끄는 내용
5. 브랜드 톤에 맞는 문체 사용

**응답 형식 (정확한 JSON):**
{{
    "caption": "여기에 캡션 내용 (이모지 포함)",
    "hashtags": ["#해시태그1", "#해시태그2", "#해시태그3", "#해시태그4", "#해시태그5", "#해시태그6"]
}}

업종의 특성과 타겟 고객을 고려하여 창의적이고 매력적인 콘텐츠를 작성해주세요.
"""
    
    return prompt

def parse_text_content(content_text: str, business_info: Dict[str, str]) -> Dict[str, Any]:
    """텍스트에서 캡션과 해시태그 추출"""
    
    lines = content_text.split('\n')
    caption_lines = []
    hashtags = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('#'):
            # 해시태그 라인
            tags = [tag.strip() for tag in line.split() if tag.startswith('#')]
            hashtags.extend(tags)
        elif line and not line.startswith('{') and not line.startswith('}'):
            # 캡션 라인
            caption_lines.append(line)
    
    caption = ' '.join(caption_lines).strip()
    
    # 해시태그가 부족하면 기본 해시태그 추가
    if len(hashtags) < 5:
        industry = business_info.get('industry', 'general')
        default_hashtags = get_default_hashtags(industry)
        hashtags.extend(default_hashtags[:8-len(hashtags)])
    
    return {
        "success": True,
        "caption": caption,
        "hashtags": hashtags[:8],  # 최대 8개
        "full_caption": f"{caption}\n\n{' '.join(hashtags[:8])}",
        "type": "openai_parsed"
    }

def get_default_hashtags(industry: str) -> list:
    """업종별 기본 해시태그"""
    defaults = {
        'restaurant': ['#맛집', '#맛스타그램', '#음식', '#카페', '#맛있어요'],
        'fashion': ['#패션', '#스타일', '#ootd', '#fashion', '#트렌드'],
        'beauty': ['#뷰티', '#화장품', '#beauty', '#스킨케어', '#메이크업'],
        'fitness': ['#피트니스', '#운동', '#헬스', '#fitness', '#다이어트']
    }
    return defaults.get(industry, ['#비즈니스', '#서비스', '#품질', '#전문성', '#추천'])

# 테스트 함수
def test_openai_integration():
    """OpenAI 통합 테스트"""
    
    test_business = {
        'business_name': '달콤한 베이커리',
        'industry': 'restaurant',
        'target_audience': '20-30대 여성',
        'brand_voice': '따뜻하고 친근한'
    }
    
    print("🧪 OpenAI API 테스트 시작...")
    result = generate_with_openai(test_business)
    
    if result['success']:
        print("✅ OpenAI API 테스트 성공!")
        print(f"📝 캡션: {result['caption']}")
        print(f"🏷️ 해시태그: {result['hashtags']}")
        print(f"🎯 생성 타입: {result['type']}")
    else:
        print("❌ OpenAI API 테스트 실패:")
        print(f"   오류: {result['error']}")
    
    return result

if __name__ == "__main__":
    test_openai_integration()
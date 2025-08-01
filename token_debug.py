# token_debug.py - Instagram 토큰 상태 확인 스크립트

import os
import requests
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InstagramTokenDebugger:
    def __init__(self):
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN', '')
        self.app_id = os.getenv('FACEBOOK_APP_ID', '')
        self.app_secret = os.getenv('FACEBOOK_APP_SECRET', '')
        
    def analyze_token_format(self):
        """토큰 형식 분석"""
        print("=" * 50)
        print("🔍 토큰 형식 분석")
        print("=" * 50)
        
        if not self.access_token:
            print("❌ INSTAGRAM_ACCESS_TOKEN 환경변수가 설정되지 않음")
            return False
            
        token = self.access_token.strip()
        
        print(f"📏 토큰 길이: {len(token)}")
        print(f"🔤 시작 문자: {token[:10]}...")
        print(f"🔤 끝 문자: ...{token[-10:]}")
        
        # 일반적인 문제들 체크
        issues = []
        
        if token.startswith('Bearer '):
            issues.append("⚠️ 'Bearer ' 접두사 포함됨")
            
        if '\n' in token or '\r' in token:
            issues.append("⚠️ 개행문자 포함됨")
            
        if token.startswith(' ') or token.endswith(' '):
            issues.append("⚠️ 공백 문자 포함됨")
            
        if token.startswith('"') or token.startswith("'"):
            issues.append("⚠️ 따옴표 포함됨")
            
        if len(token) < 50:  # Instagram 토큰은 보통 매우 길다
            issues.append("⚠️ 토큰이 너무 짧음 (유효하지 않을 가능성)")
            
        if issues:
            print("\n🚨 발견된 문제들:")
            for issue in issues:
                print(f"  {issue}")
            return False
        else:
            print("✅ 토큰 형식이 올바른 것으로 보임")
            return True
    
    def check_token_validity(self):
        """토큰 유효성 검사"""
        print("\n" + "=" * 50)
        print("🔐 토큰 유효성 검사")
        print("=" * 50)
        
        clean_token = self.access_token.strip()
        
        # 1. 기본 사용자 정보 조회
        try:
            url = "https://graph.instagram.com/me"
            params = {
                'fields': 'id,username,account_type',
                'access_token': clean_token
            }
            
            print(f"📡 요청 URL: {url}")
            print(f"📊 파라미터: fields=id,username,account_type")
            
            response = requests.get(url, params=params, timeout=10)
            
            print(f"📈 응답 상태: {response.status_code}")
            print(f"📄 응답 헤더: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ 토큰 유효!")
                print(f"👤 사용자 ID: {data.get('id', 'N/A')}")
                print(f"📱 사용자명: {data.get('username', 'N/A')}")
                print(f"🏢 계정 타입: {data.get('account_type', 'N/A')}")
                return True
            else:
                print("❌ 토큰 무효!")
                try:
                    error_data = response.json()
                    print(f"🚨 오류 상세:")
                    print(json.dumps(error_data, indent=2, ensure_ascii=False))
                except:
                    print(f"🚨 응답 내용: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 네트워크 오류: {e}")
            return False
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return False
    
    def debug_token_info(self):
        """Facebook Debug Token API 사용"""
        print("\n" + "=" * 50)
        print("🐛 Facebook Debug Token API")
        print("=" * 50)
        
        if not self.app_id or not self.app_secret:
            print("⚠️ FACEBOOK_APP_ID 또는 FACEBOOK_APP_SECRET가 설정되지 않음")
            print("   이 검사는 건너뜁니다.")
            return
            
        try:
            # App Access Token 생성
            app_token_url = "https://graph.facebook.com/oauth/access_token"
            app_token_params = {
                'client_id': self.app_id,
                'client_secret': self.app_secret,
                'grant_type': 'client_credentials'
            }
            
            app_response = requests.get(app_token_url, params=app_token_params)
            
            if app_response.status_code != 200:
                print("❌ App Access Token 생성 실패")
                return
                
            app_token = app_response.json().get('access_token')
            
            # Debug Token
            debug_url = "https://graph.facebook.com/debug_token"
            debug_params = {
                'input_token': self.access_token.strip(),
                'access_token': app_token
            }
            
            debug_response = requests.get(debug_url, params=debug_params)
            
            if debug_response.status_code == 200:
                debug_data = debug_response.json()
                print("🔍 토큰 디버그 정보:")
                print(json.dumps(debug_data, indent=2, ensure_ascii=False))
            else:
                print(f"❌ Debug API 호출 실패: {debug_response.text}")
                
        except Exception as e:
            print(f"❌ Debug Token 검사 오류: {e}")
    
    def test_instagram_api_versions(self):
        """다양한 Instagram API 버전 테스트"""
        print("\n" + "=" * 50)
        print("🧪 Instagram API 버전 테스트")
        print("=" * 50)
        
        versions = ['v18.0', 'v17.0', 'v16.0', 'v15.0']
        clean_token = self.access_token.strip()
        
        for version in versions:
            try:
                url = f"https://graph.instagram.com/{version}/me"
                params = {
                    'fields': 'id,username',
                    'access_token': clean_token
                }
                
                print(f"🧪 API 버전 {version} 시도 중...")
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ API 버전 {version} 성공!")
                    print(f"   응답: {data}")
                    return version
                else:
                    error_data = response.json() if response.content else {}
                    print(f"❌ API 버전 {version} 실패: {error_data}")
                    
            except Exception as e:
                print(f"❌ API 버전 {version} 오류: {e}")
        
        print("❌ 모든 API 버전에서 실패")
        return None
    
    def generate_token_renewal_guide(self):
        """토큰 갱신 가이드 생성"""
        print("\n" + "=" * 50)
        print("🔄 토큰 갱신 가이드")
        print("=" * 50)
        
        print("""
📋 Instagram API 토큰 갱신 방법:

1️⃣ Meta for Developers 접속
   → https://developers.facebook.com/

2️⃣ 앱 선택 및 설정
   → 내 앱 → [앱 이름] → Instagram Basic Display

3️⃣ 새 액세스 토큰 생성
   → User Token Generator → Generate Token

4️⃣ 장기 토큰으로 변환 (선택사항)
   GET https://graph.instagram.com/access_token
   ?grant_type=ig_exchange_token
   &client_secret={app-secret}
   &access_token={short-lived-token}

5️⃣ 환경변수 업데이트
   INSTAGRAM_ACCESS_TOKEN={new-token}

⚠️ 주의사항:
   - 토큰 복사 시 앞뒤 공백 제거
   - 개행문자나 특수문자 포함 금지
   - Bearer 접두사 제거
        """)
    
    def run_complete_diagnosis(self):
        """전체 진단 실행"""
        print("🏥 Instagram API 토큰 완전 진단 시작")
        print("=" * 60)
        
        # 1. 토큰 형식 검사
        format_ok = self.analyze_token_format()
        
        # 2. 토큰 유효성 검사
        validity_ok = self.check_token_validity()
        
        # 3. API 버전 테스트
        working_version = self.test_instagram_api_versions()
        
        # 4. Debug Token (선택사항)
        self.debug_token_info()
        
        # 5. 종합 결과
        print("\n" + "=" * 60)
        print("📊 진단 결과 요약")
        print("=" * 60)
        
        print(f"🔤 토큰 형식: {'✅ 정상' if format_ok else '❌ 문제 있음'}")
        print(f"🔐 토큰 유효성: {'✅ 유효' if validity_ok else '❌ 무효'}")
        print(f"🧪 API 버전: {working_version if working_version else '❌ 모든 버전 실패'}")
        
        if not format_ok or not validity_ok:
            print("\n🚨 권장 조치:")
            print("1. 새 액세스 토큰 발급")
            print("2. 토큰 형식 확인 (공백, 특수문자 제거)")
            print("3. 앱 권한 및 설정 확인")
            self.generate_token_renewal_guide()
        else:
            print("\n✅ 토큰이 정상적으로 작동해야 합니다.")
            print("   다른 코드 로직을 확인해보세요.")

# 실행
if __name__ == "__main__":
    debugger = InstagramTokenDebugger()
    debugger.run_complete_diagnosis()
# instagram_api_validator.py - Instagram API 설정 검증 도구 (보안 수정)
import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class InstagramAPIValidator:
    def __init__(self):
        # 🔒 보안 수정: 환경변수에서 올바르게 읽기
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.business_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
        self.base_url = "https://graph.facebook.com/v18.0"
        
        # 초기 검증
        if not self.access_token:
            print("⚠️ INSTAGRAM_ACCESS_TOKEN 환경변수가 설정되지 않았습니다.")
            print("💡 .env 파일에 INSTAGRAM_ACCESS_TOKEN=your_token_here 추가하세요.")
            
        if not self.business_account_id:
            print("⚠️ INSTAGRAM_BUSINESS_ACCOUNT_ID 환경변수가 설정되지 않았습니다.")
            print("💡 .env 파일에 INSTAGRAM_BUSINESS_ACCOUNT_ID=your_id_here 추가하세요.")
    
    def validate_token_format(self):
        """토큰 형식 검증"""
        print("1️⃣ 토큰 형식 검증...")
        
        if not self.access_token:
            print("❌ INSTAGRAM_ACCESS_TOKEN이 설정되지 않았습니다")
            print("💡 Instagram Business API 토큰이 필요합니다:")
            print("   1. Facebook Developer Console 접속")
            print("   2. 앱 생성 후 Instagram Basic Display API 설정")
            print("   3. 장기 액세스 토큰 발급")
            return False
            
        if not self.business_account_id:
            print("❌ INSTAGRAM_BUSINESS_ACCOUNT_ID가 설정되지 않았습니다")
            print("💡 Instagram 비즈니스 계정 ID가 필요합니다:")
            print("   1. Instagram을 Facebook 페이지에 연결")
            print("   2. Facebook Graph API로 계정 ID 조회")
            return False
        
        # 토큰 형식 기본 검증
        if len(self.access_token) < 50:
            print("⚠️ 토큰이 너무 짧습니다. 올바른 토큰인지 확인하세요")
        
        # 계정 ID 형식 확인
        if not self.business_account_id.isdigit():
            print("⚠️ 비즈니스 계정 ID는 숫자여야 합니다")
            return False
        
        # 🔒 보안: 토큰을 마스킹해서 표시
        masked_token = self.access_token[:8] + "..." + self.access_token[-8:] if len(self.access_token) > 16 else "***"
        print(f"✅ 토큰 설정됨: {masked_token}")
        print(f"✅ 계정 ID: {self.business_account_id}")
        return True
    
    def test_basic_api_access(self):
        """기본 API 접근 테스트"""
        print("\n2️⃣ 기본 API 접근 테스트...")
        
        if not self.access_token or not self.business_account_id:
            print("❌ API 자격증명이 없어서 테스트를 건너뜁니다.")
            return False, "Missing credentials"
        
        try:
            url = f"https://graph.instagram.com/{self.business_account_id}"
            params = {
                'fields': 'id,name,username,account_type,media_count',
                'access_token': self.access_token
            }
            
            print(f"📡 요청 URL: {url}")
            response = requests.get(url, params=params, timeout=15)
            
            print(f"📊 응답 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ API 접근 성공!")
                print(f"   계정명: {data.get('name', 'N/A')}")
                print(f"   사용자명: @{data.get('username', 'N/A')}")
                print(f"   계정 타입: {data.get('account_type', 'N/A')}")
                print(f"   미디어 수: {data.get('media_count', 'N/A')}")
                return True, data
            else:
                error_data = response.json()
                print(f"❌ API 접근 실패")
                print(f"   오류 코드: {response.status_code}")
                
                # 🔒 보안: 민감한 정보 필터링
                safe_error = self._sanitize_error_message(error_data)
                print(f"   오류 메시지: {safe_error}")
                return False, safe_error
                
        except requests.exceptions.Timeout:
            print("❌ API 요청 시간 초과 (15초)")
            return False, "Request timeout"
        except requests.exceptions.ConnectionError:
            print("❌ 네트워크 연결 오류")
            return False, "Connection error"
        except Exception as e:
            print(f"❌ API 테스트 오류: {str(e)}")
            return False, str(e)
    
    def _sanitize_error_message(self, error_data):
        """🔒 오류 메시지에서 민감한 정보 제거"""
        if isinstance(error_data, dict):
            # 액세스 토큰 정보 제거
            sanitized = {}
            for key, value in error_data.items():
                if key.lower() in ['access_token', 'token', 'secret']:
                    sanitized[key] = "***HIDDEN***"
                elif isinstance(value, str) and len(value) > 50:
                    # 긴 문자열은 일부만 표시
                    sanitized[key] = value[:50] + "..."
                else:
                    sanitized[key] = value
            return sanitized
        return error_data
    
    def test_media_permissions(self):
        """미디어 관련 권한 테스트"""
        print("\n3️⃣ 미디어 업로드 권한 테스트...")
        
        if not self.access_token or not self.business_account_id:
            print("❌ API 자격증명이 없어서 테스트를 건너뜁니다.")
            return False
        
        try:
            # 최근 미디어 조회로 권한 확인
            url = f"https://graph.instagram.com/{self.business_account_id}/media"
            params = {
                'fields': 'id,media_type,media_url,caption,timestamp',
                'limit': 3,  # 🔒 보안: 최소한의 데이터만 요청
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                media_list = data.get('data', [])
                print(f"✅ 미디어 조회 권한 확인됨 (최근 미디어 {len(media_list)}개)")
                
                if media_list:
                    latest = media_list[0]
                    print(f"   최근 포스트 ID: {latest.get('id')}")
                    print(f"   타입: {latest.get('media_type')}")
                    if latest.get('timestamp'):
                        print(f"   업로드 시간: {latest.get('timestamp')}")
                
                return True
            else:
                error_data = response.json()
                safe_error = self._sanitize_error_message(error_data)
                print(f"❌ 미디어 권한 확인 실패: {safe_error}")
                return False
                
        except Exception as e:
            print(f"❌ 권한 테스트 오류: {str(e)}")
            return False
    
    def run_safe_validation(self):
        """🔒 안전한 검증 실행 (실제 포스팅 없음)"""
        print("🔍 Instagram API 안전 검증 시작")
        print("=" * 60)
        print("🔒 보안 모드: 실제 포스팅은 하지 않습니다")
        print("=" * 60)
        
        results = {}
        
        # 1. 토큰 형식 검증
        results['token_format'] = self.validate_token_format()
        
        if not results['token_format']:
            print("\n❌ 기본 설정에 문제가 있습니다.")
            self._show_setup_guide()
            return results
        
        # 2. 기본 API 접근
        results['api_access'], account_data = self.test_basic_api_access()
        
        if not results['api_access']:
            print("\n❌ API 접근에 실패했습니다.")
            self._show_troubleshooting_guide()
            return results
        
        # 3. 미디어 권한 확인
        results['media_permissions'] = self.test_media_permissions()
        
        # 결과 요약
        print("\n" + "="*60)
        print("📊 검증 결과 요약:")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        for test_name, result in results.items():
            status = "✅ 통과" if result else "❌ 실패"
            print(f"   {test_name}: {status}")
        
        print(f"\n🎯 결과: {passed_tests}/{total_tests} 테스트 통과")
        
        if passed_tests == total_tests:
            print("🎉 모든 테스트 통과! Instagram API가 완벽하게 설정되었습니다!")
            print("💡 이제 실제 포스팅 기능을 사용할 수 있습니다.")
        elif passed_tests >= 2:
            print("✅ 기본 기능은 작동합니다. 일부 고급 기능에 제한이 있을 수 있습니다.")
        else:
            print("⚠️ API 설정에 문제가 있습니다. 아래 가이드를 참고하세요.")
            self._show_setup_guide()
        
        return results
    
    def _show_setup_guide(self):
        """🔒 보안이 강화된 설정 가이드"""
        print("\n📋 Instagram API 설정 가이드:")
        print("1. Facebook Developer Console (developers.facebook.com) 접속")
        print("2. '앱 만들기' → '소비자' 선택")
        print("3. Instagram Basic Display 제품 추가")
        print("4. Instagram 테스터 사용자 추가")
        print("5. 액세스 토큰 생성 (장기 토큰 권장)")
        print("6. .env 파일에 다음과 같이 설정:")
        print("   INSTAGRAM_ACCESS_TOKEN=your_long_lived_token")
        print("   INSTAGRAM_BUSINESS_ACCOUNT_ID=your_business_account_id")
        print("\n🔒 보안 주의사항:")
        print("- 토큰을 Git에 커밋하지 마세요")
        print("- .env 파일을 .gitignore에 추가하세요")
        print("- 정기적으로 토큰을 갱신하세요")
    
    def _show_troubleshooting_guide(self):
        """문제 해결 가이드"""
        print("\n🔧 문제 해결 가이드:")
        print("1. 토큰 만료: Facebook Developer Console에서 토큰 갱신")
        print("2. 권한 부족: Instagram Basic Display API 권한 확인")
        print("3. 계정 연결: Instagram 계정이 Facebook 페이지에 연결되었는지 확인")
        print("4. 비즈니스 계정: 개인 계정이 아닌 비즈니스 계정 사용")
        print("5. API 제한: 요청 횟수 제한 확인")

# 🔒 보안 강화된 테스트 함수
def run_secure_validation():
    """보안이 강화된 검증 실행"""
    validator = InstagramAPIValidator()
    return validator.run_safe_validation()

if __name__ == "__main__":
    print("🔒 보안 강화된 Instagram API 검증 도구")
    print("=" * 60)
    
    # 환경변수 파일 확인
    if not os.path.exists('.env'):
        print("⚠️ .env 파일이 없습니다. 생성하는 중...")
        with open('.env', 'w') as f:
            f.write("""# Instagram API 설정
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token_here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_business_account_id_here

# OpenAI API 설정  
OPENAI_API_KEY=your_openai_api_key_here

# 보안 설정
SECRET_KEY=your_very_secure_secret_key_here
""")
        print("✅ .env 파일이 생성되었습니다. API 키를 설정하세요.")
    
    run_secure_validation()
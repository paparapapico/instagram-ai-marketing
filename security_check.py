# security_check.py - 보안 검증 도구
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import hashlib

class SecurityChecker:
    """🔒 프로젝트 보안 검증 도구"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.issues = []
        self.warnings = []
        
        # 위험한 패턴들
        self.dangerous_patterns = {
            'hardcoded_api_keys': [
                r'sk-[a-zA-Z0-9]{48}',  # OpenAI API 키
                r'EAAR[a-zA-Z0-9]+',     # Instagram Access Token
                r'[0-9]{15,}',           # 긴 숫자 (계정 ID 등)
            ],
            'secrets_in_code': [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
            ],
            'debug_code': [
                r'print\s*\(\s*["\'].*password.*["\']',
                r'print\s*\(\s*["\'].*token.*["\']',
                r'console\.log\s*\(\s*["\'].*secret.*["\']',
            ]
        }
        
        # 검사할 파일 확장자
        self.code_extensions = {'.py', '.js', '.html', '.json', '.yml', '.yaml', '.env'}
        
        # 제외할 디렉토리
        self.exclude_dirs = {
            '__pycache__', '.git', 'node_modules', 'venv', 'env', 
            '.vscode', '.idea', 'logs', 'temp', 'tmp'
        }
    
    def check_environment_files(self) -> List[Dict]:
        """🔍 환경변수 파일 보안 검사"""
        issues = []
        
        # .env 파일들 검사
        env_files = list(self.project_root.glob('**/.env*'))
        
        for env_file in env_files:
            if env_file.name == '.env.example':
                continue
                
            # .env 파일이 Git에 추가되었는지 확인
            if self._is_tracked_by_git(env_file):
                issues.append({
                    'type': 'critical',
                    'file': str(env_file),
                    'message': '.env 파일이 Git에 추가되어 있습니다! 즉시 제거하세요.',
                    'fix': 'git rm --cached .env && echo ".env" >> .gitignore'
                })
            
            # 환경변수 파일 내용 검사
            try:
                content = env_file.read_text(encoding='utf-8')
                
                # 기본값 사용 여부 확인
                dangerous_defaults = [
                    'your-api-key-here',
                    'change-this',
                    'your-secret-key-here',
                    'your-token-here'
                ]
                
                for default in dangerous_defaults:
                    if default in content:
                        issues.append({
                            'type': 'warning',
                            'file': str(env_file),
                            'message': f'기본값 "{default}"이 사용되고 있습니다.',
                            'fix': '실제 값으로 변경하세요.'
                        })
                
                # 실제 API 키가 포함되어 있는지 확인
                for pattern_type, patterns in self.dangerous_patterns.items():
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            issues.append({
                                'type': 'critical',
                                'file': str(env_file),
                                'message': f'실제 API 키나 토큰이 발견되었습니다: {pattern_type}',
                                'fix': '이 파일이 Git에 커밋되지 않았는지 확인하세요.'
                            })
                            
            except Exception as e:
                issues.append({
                    'type': 'warning',
                    'file': str(env_file),
                    'message': f'파일 읽기 오류: {e}',
                    'fix': '파일 권한을 확인하세요.'
                })
        
        return issues
    
    def check_source_code(self) -> List[Dict]:
        """🔍 소스코드 보안 검사"""
        issues = []
        
        for file_path in self._get_source_files():
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # 하드코딩된 시크릿 검사
                for pattern_type, patterns in self.dangerous_patterns.items():
                    for pattern in patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            issues.append({
                                'type': 'critical',
                                'file': str(file_path),
                                'line': line_num,
                                'message': f'하드코딩된 시크릿 발견: {pattern_type}',
                                'code': match.group(),
                                'fix': '환경변수를 사용하세요.'
                            })
                
                # DEBUG 모드 확인
                if 'DEBUG = True' in content or 'DEBUG=True' in content:
                    issues.append({
                        'type': 'warning',
                        'file': str(file_path),
                        'message': 'DEBUG 모드가 하드코딩되어 있습니다.',
                        'fix': '환경변수로 설정하세요.'
                    })
                
                # SQL 인젝션 취약점 검사
                sql_patterns = [
                    r'f".*SELECT.*{.*}"',
                    r'f\'.*SELECT.*{.*}\'',
                    r'".*SELECT.*"\s*\+',
                    r'\'.*SELECT.*\'\s*\+',
                ]
                
                for pattern in sql_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        issues.append({
                            'type': 'critical',
                            'file': str(file_path),
                            'line': line_num,
                            'message': 'SQL 인젝션 취약점 가능성',
                            'fix': '파라미터화된 쿼리를 사용하세요.'
                        })
                        
            except Exception as e:
                issues.append({
                    'type': 'warning',
                    'file': str(file_path),
                    'message': f'파일 읽기 오류: {e}',
                    'fix': '파일 권한을 확인하세요.'
                })
        
        return issues
    
    def check_file_permissions(self) -> List[Dict]:
        """🔍 파일 권한 검사"""
        issues = []
        
        # 중요한 파일들의 권한 확인 (Unix 시스템에서만)
        if os.name != 'nt':  # Windows가 아닌 경우
            sensitive_files = ['.env', 'config.py', 'settings.py']
            
            for filename in sensitive_files:
                file_path = self.project_root / filename
                if file_path.exists():
                    stat_info = file_path.stat()
                    permissions = oct(stat_info.st_mode)[-3:]
                    
                    # 644 이상의 권한은 위험
                    if int(permissions) > 600:
                        issues.append({
                            'type': 'warning',
                            'file': str(file_path),
                            'message': f'파일 권한이 너무 관대합니다: {permissions}',
                            'fix': f'chmod 600 {filename}'
                        })
        
        return issues
    
    def check_dependencies(self) -> List[Dict]:
        """🔍 의존성 보안 검사"""
        issues = []
        
        # requirements.txt 검사
        req_file = self.project_root / 'requirements.txt'
        if req_file.exists():
            try:
                content = req_file.read_text()
                
                # 버전이 고정되지 않은 패키지 확인
                lines = content.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '==' not in line and '>=' not in line and '<=' not in line:
                            issues.append({
                                'type': 'warning',
                                'file': str(req_file),
                                'message': f'패키지 버전이 고정되지 않음: {line}',
                                'fix': '보안을 위해 특정 버전을 사용하세요.'
                            })
                            
                # 알려진 취약한 패키지 확인
                vulnerable_packages = ['flask<1.0', 'django<2.0', 'requests<2.20']
                for vuln in vulnerable_packages:
                    if vuln in content:
                        issues.append({
                            'type': 'critical',
                            'file': str(req_file),
                            'message': f'취약한 패키지 버전: {vuln}',
                            'fix': '최신 버전으로 업데이트하세요.'
                        })
                        
            except Exception as e:
                issues.append({
                    'type': 'warning',
                    'file': str(req_file),
                    'message': f'requirements.txt 읽기 오류: {e}',
                    'fix': '파일을 확인하세요.'
                })
        
        return issues
    
    def check_gitignore(self) -> List[Dict]:
        """🔍 .gitignore 보안 검사"""
        issues = []
        
        gitignore_file = self.project_root / '.gitignore'
        if not gitignore_file.exists():
            issues.append({
                'type': 'critical',
                'file': '.gitignore',
                'message': '.gitignore 파일이 없습니다.',
                'fix': '.gitignore 파일을 생성하고 민감한 파일들을 추가하세요.'
            })
        else:
            try:
                content = gitignore_file.read_text()
                
                # 필수 항목들이 있는지 확인
                required_items = ['.env', '*.db', '*.log', '__pycache__']
                
                for item in required_items:
                    if item not in content:
                        issues.append({
                            'type': 'warning',
                            'file': str(gitignore_file),
                            'message': f'중요한 항목이 누락됨: {item}',
                            'fix': f'.gitignore에 {item}을 추가하세요.'
                        })
                        
            except Exception as e:
                issues.append({
                    'type': 'warning',
                    'file': str(gitignore_file),
                    'message': f'.gitignore 읽기 오류: {e}',
                    'fix': '파일을 확인하세요.'
                })
        
        return issues
    
    def _get_source_files(self) -> List[Path]:
        """소스코드 파일 목록 반환"""
        files = []
        
        for file_path in self.project_root.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix in self.code_extensions and
                not any(exclude in file_path.parts for exclude in self.exclude_dirs)):
                files.append(file_path)
        
        return files
    
    def _is_tracked_by_git(self, file_path: Path) -> bool:
        """파일이 Git에 추가되어 있는지 확인"""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'ls-files', str(file_path)],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            return len(result.stdout.strip()) > 0
        except:
            return False
    
    def run_full_check(self) -> Dict:
        """🔍 전체 보안 검사 실행"""
        print("🔒 프로젝트 보안 검사 시작...")
        print("=" * 60)
        
        all_issues = []
        
        # 각 검사 실행
        checks = [
            ("환경변수 파일", self.check_environment_files),
            ("소스코드", self.check_source_code),
            ("파일 권한", self.check_file_permissions),
            ("의존성", self.check_dependencies),
            (".gitignore", self.check_gitignore),
        ]
        
        for check_name, check_func in checks:
            print(f"\n📋 {check_name} 검사 중...")
            try:
                issues = check_func()
                all_issues.extend(issues)
                
                if issues:
                    critical_count = len([i for i in issues if i['type'] == 'critical'])
                    warning_count = len([i for i in issues if i['type'] == 'warning'])
                    print(f"   ❌ {critical_count}개 심각한 문제, ⚠️ {warning_count}개 경고")
                else:
                    print(f"   ✅ 문제 없음")
                    
            except Exception as e:
                print(f"   ❌ 검사 오류: {e}")
        
        # 결과 정리
        critical_issues = [i for i in all_issues if i['type'] == 'critical']
        warning_issues = [i for i in all_issues if i['type'] == 'warning']
        
        result = {
            'total_issues': len(all_issues),
            'critical_issues': critical_issues,
            'warning_issues': warning_issues,
            'passed': len(critical_issues) == 0
        }
        
        # 결과 출력
        self._print_results(result)
        
        return result
    
    def _print_results(self, result: Dict):
        """결과 출력"""
        print("\n" + "=" * 60)
        print("📊 보안 검사 결과")
        print("=" * 60)
        
        critical_count = len(result['critical_issues'])
        warning_count = len(result['warning_issues'])
        
        if critical_count == 0 and warning_count == 0:
            print("🎉 모든 보안 검사를 통과했습니다!")
        else:
            print(f"❌ {critical_count}개 심각한 문제")
            print(f"⚠️ {warning_count}개 경고")
            
            # 심각한 문제들 출력
            if critical_count > 0:
                print(f"\n🚨 심각한 문제들 (즉시 수정 필요):")
                for i, issue in enumerate(result['critical_issues'][:5], 1):
                    print(f"\n{i}. {issue['message']}")
                    print(f"   📁 파일: {issue['file']}")
                    if 'line' in issue:
                        print(f"   📍 라인: {issue['line']}")
                    if 'code' in issue:
                        print(f"   💻 코드: {issue['code']}")
                    print(f"   🔧 해결: {issue['fix']}")
                
                if critical_count > 5:
                    print(f"\n   ... 그리고 {critical_count - 5}개 더")
            
            # 경고들 출력 (일부만)
            if warning_count > 0:
                print(f"\n⚠️ 경고들 (개선 권장):")
                for i, issue in enumerate(result['warning_issues'][:3], 1):
                    print(f"\n{i}. {issue['message']}")
                    print(f"   📁 파일: {issue['file']}")
                    print(f"   🔧 해결: {issue['fix']}")
                
                if warning_count > 3:
                    print(f"\n   ... 그리고 {warning_count - 3}개 더")
        
        print("\n" + "=" * 60)
        
        if critical_count > 0:
            print("🔴 심각한 보안 문제가 발견되었습니다. 즉시 수정하세요!")
        elif warning_count > 0:
            print("🟡 일부 개선사항이 있습니다. 검토해보세요.")
        else:
            print("🟢 보안 상태가 양호합니다!")

def main():
    """메인 실행 함수"""
    checker = SecurityChecker()
    result = checker.run_full_check()
    
    # 심각한 문제가 있으면 종료 코드 1 반환
    if len(result['critical_issues']) > 0:
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()

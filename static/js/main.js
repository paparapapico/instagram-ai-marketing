// 메인 JavaScript 파일
document.addEventListener('DOMContentLoaded', function() {
    console.log('Instagram AI Marketing Platform loaded');
    
    // 버튼 이벤트 리스너
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            console.log('Button clicked:', this.textContent);
            // 여기에 버튼 클릭 시 실행할 로직 추가
        });
    });

    // 로그인 폼 처리 (폼이 있을 때만 동작)
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const data = await res.json();
                if (res.ok && data.access_token) {
                    localStorage.setItem('access_token', data.access_token);
                    window.location.href = '/dashboard';
                } else {
                    alert(data.detail || data.message || '로그인 실패');
                }
            } catch (err) {
                alert('네트워크 오류 또는 서버 오류');
            }
        });
    }

    // 회원가입 폼 처리 (폼이 있을 때만 동작)
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const business_name = document.getElementById('register-business').value;
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;
            const industry = document.getElementById('register-industry').value;
            const target_audience = '일반 고객'; // 기본값, 필요시 폼에 추가 가능
            const brand_voice = '친근하고 전문적인'; // 기본값, 필요시 폼에 추가 가능
            try {
                const res = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ business_name, email, password, industry, target_audience, brand_voice })
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    alert('회원가입이 완료되었습니다! 이제 로그인해 주세요.');
                    // 회원가입 모달 닫고 로그인 모달 열기
                    const registerModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('registerModal'));
                    registerModal.hide();
                    const loginModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('loginModal'));
                    loginModal.show();
                } else {
                    alert(data.detail || data.message || '회원가입 실패');
                }
            } catch (err) {
                alert('네트워크 오류 또는 서버 오류');
            }
        });
    }
});
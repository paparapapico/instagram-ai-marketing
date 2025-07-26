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
});
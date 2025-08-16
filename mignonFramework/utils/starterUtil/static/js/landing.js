/**
 * 专用于 landing.html 的脚本
 */
function initLandingPage() {
    const pC = document.querySelector('.particle-container');
    const content = document.querySelector('.landing .content');

    // 触发内容进入动画
    if (content) {
        // 使用一个微小的延迟确保浏览器准备好渲染过渡效果
        setTimeout(() => {
            content.classList.add('active');
        }, 100);
    }

    if (pC) {
        for (let i = 0; i < 50; i++) {
            const p = document.createElement('div');
            p.classList.add('particle');
            const size = Math.random() * 4 + 1;
            p.style.width = `${size}px`; p.style.height = `${size}px`;
            p.style.left = `${Math.random() * 100}%`;
            p.style.animationDuration = `${Math.random() * 20 + 15}s`;
            p.style.animationDelay = `${Math.random() * 10}s`;
            pC.appendChild(p);
        }
    }

    const startButton = document.querySelector('.start-button');
    const overlay = document.getElementById('transition-overlay');
    if (startButton && overlay) {
        startButton.addEventListener('click', (e) => {
            e.preventDefault();
            overlay.classList.add('active');
            setTimeout(() => {
                window.location.href = e.target.href;
            }, 1200);
        });
    }
}

// 脚本加载后直接执行
initLandingPage();
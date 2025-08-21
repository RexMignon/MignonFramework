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
        // 增加光点数量以加快“增加速度”
        for (let i = 0; i < 200; i++) { // 之前是 50，现在增加到 200
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

    const startButtonContainer = document.getElementById('aurora-start-btn-container'); // 获取新的容器
    if (startButtonContainer) {
        // 创建一个新的 AuroraButton 实例，并传入导航回调
        new AuroraButton('aurora-start-btn', '开始', () => {
            const overlay = document.getElementById('transition-overlay');
            if (overlay) {
                overlay.classList.add('active');
                setTimeout(() => {
                    window.location.href = '/app'; // 导航到 /app 页面
                }, 1200);
            }
        });
    }

    // 移除旧的 startButton 逻辑，因为它已被 Canvas 按钮替换
    // const startButton = document.querySelector('.start-button');
    // const overlay = document.getElementById('transition-overlay');
    // if (startButton && overlay) {
    //     startButton.addEventListener('click', (e) => {
    //         e.preventDefault();
    //         overlay.classList.add('active');
    //         setTimeout(() => {
    //             window.location.href = e.target.href;
    //         }, 1200);
    //     });
    // }
}

// ****** 关键修复：将 initLandingPage 的调用也移到 DOMContentLoaded 事件中 ******
document.addEventListener('DOMContentLoaded', initLandingPage);

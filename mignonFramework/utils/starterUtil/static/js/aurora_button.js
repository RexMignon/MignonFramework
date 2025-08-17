// --- 通用工具 ---
function roundRect(ctx, x, y, width, height, radius) {
    if (typeof radius === 'number') {
        radius = {tl: radius, tr: radius, br: radius, bl: radius};
    } else {
        radius = {...{tl: 0, tr: 0, br: 0, bl: 0}, ...radius};
    }
    ctx.beginPath();
    ctx.moveTo(x + radius.tl, y);
    ctx.lineTo(x + width - radius.tr, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius.tr);
    ctx.lineTo(x + width, y + height - radius.br);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius.br, y + height);
    ctx.lineTo(x + radius.bl, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius.bl);
    ctx.lineTo(x, y + radius.tl);
    ctx.quadraticCurveTo(x, y, x + radius.tl, y);
    ctx.closePath();
}

// ****** 关键修改：将 CanvasButton 类定义移到全局作用域 ******
class CanvasButton {
    constructor(canvasId, text = '生成代码', clickCallback = null) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error(`Canvas with id "${canvasId}" not found.`);
            return;
        }
        this.ctx = this.canvas.getContext('2d');
        this.width = this.canvas.width;
        this.height = this.canvas.height;
        this.text = text;
        this.isHovering = false;
        this.animationFrameId = null;
        this.clickCallback = clickCallback;

        this.init();
    }

    init() {
        this.drawInitialState();
        // 添加鼠标进入和离开事件到Canvas的父元素（容器），确保整个按钮区域响应
        if (this.canvas.parentElement) {
            this.canvas.parentElement.addEventListener('mouseenter', () => {
                this.isHovering = true;
                this.startAnimation();
            });
            this.canvas.parentElement.addEventListener('mouseleave', () => {
                this.isHovering = false;
                this.stopAnimation();
            });

            this.canvas.parentElement.addEventListener('click', () => {
                console.log(`按钮 "${this.text}" 被点击了!`); // 调试日志
                if (this.clickCallback) {
                    this.clickCallback();
                } else {
                    if (window.generateFinalCode) {
                        window.generateFinalCode();
                    } else {
                        console.error('No click callback or global generateFinalCode function found.');
                    }
                }
            });
        } else {
            console.error(`Canvas with id "${this.canvas.id}" has no parent element.`);
        }

        // 保持Canvas上的悬停事件，因为Canvas动画本身就是响应Canvas的
        // 不过，为了确保统一的交互体验，通常只需要在容器上监听这些事件
        // 这里为了安全起见，暂时保留Canvas上的hover，但主要交互逻辑已移至父元素
        this.canvas.addEventListener('mouseenter', () => {
            this.isHovering = true;
            this.startAnimation();
        });
        this.canvas.addEventListener('mouseleave', () => {
            this.isHovering = false;
            this.stopAnimation();
        });
    }

    drawInitialState() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        roundRect(this.ctx, 0, 0, this.width, this.height, 8);
        this.ctx.fillStyle = '#374151'; // 灰色
        this.ctx.fill();
    }

    startAnimation() {
        if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
        this.animationFrameId = requestAnimationFrame(this._animate.bind(this));
    }

    stopAnimation() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        this.drawInitialState();
    }

    _animate() {
        if (!this.isHovering) {
            this.stopAnimation();
            return;
        }
        this.drawHoverState();
        this.animationFrameId = requestAnimationFrame(this._animate.bind(this));
    }

    drawHoverState() {
        this.drawInitialState();
    }
}

// ****** 关键修改：将 AuroraButton 类定义移到全局作用域 ******
class AuroraButton extends CanvasButton {
    constructor(canvasId, text, clickCallback) {
        super(canvasId, text, clickCallback);
        this.time = 0;
    }

    drawHoverState() {
        this.time += 0.02;
        this.ctx.clearRect(0, 0, this.width, this.height);

        const gradient = this.ctx.createLinearGradient(0, 0, this.width, this.height);

        const color1 = `hsl(${150 + Math.sin(this.time * 0.8) * 20}, 85%, 65%)`;
        const color2 = `hsl(${220 + Math.cos(this.time * 0.5) * 30}, 90%, 60%)`;
        const color3 = `hsl(${280 + Math.sin(this.time * 0.3) * 25}, 85%, 65%)`;
        const color4 = `hsl(${180 + Math.cos(this.time * 0.7) * 20}, 90%, 70%)`;

        gradient.addColorStop(0, color1);
        gradient.addColorStop(0.3, color2);
        gradient.addColorStop(0.7, color3);
        gradient.addColorStop(1, color4);

        roundRect(this.ctx, 0, 0, this.width, this.height, 8);
        this.ctx.fillStyle = gradient;
        this.ctx.fill();
    }
}

// ****** 初始化按钮的代码仍然保留在 DOMContentLoaded 中 ******
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('aurora-generate-btn')) {
        new AuroraButton('aurora-generate-btn', '一键生成最终代码', window.generateFinalCode);
    }
});

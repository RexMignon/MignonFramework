document.addEventListener('DOMContentLoaded', () => {
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

    // --- 按钮基类 ---
    class CanvasButton {
        constructor(canvasId, text = '生成代码') {
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

            this.init();
        }

        init() {
            this.drawInitialState();
            this.canvas.addEventListener('mouseenter', () => {
                this.isHovering = true;
                this.startAnimation();
            });
            this.canvas.addEventListener('mouseleave', () => {
                this.isHovering = false;
                this.stopAnimation();
                this.drawInitialState();
            });

            // ****** 新增: 点击事件监听 ******
            // 当点击Canvas时，调用在 app.js 中定义的全局函数
            this.canvas.addEventListener('click', () => {
                if (window.generateFinalCode) {
                    window.generateFinalCode();
                } else {
                    console.error('generateFinalCode function not found on window object.');
                }
            });
        }

        drawInitialState() {
            this.ctx.clearRect(0, 0, this.width, this.height);
            roundRect(this.ctx, 0, 0, this.width, this.height, 8);
            this.ctx.fillStyle = '#374151'; // 灰色
            this.ctx.fill();
            this.drawText('#f3f4f6'); // 白色文字
        }

        drawText(color) {
            this.ctx.font = 'bold 18px Inter';
            this.ctx.fillStyle = color;
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(this.text, this.width / 2, this.height / 2);
        }

        startAnimation() {
            if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
            const animate = () => {
                if (!this.isHovering) return;
                this.drawHoverState();
                this.animationFrameId = requestAnimationFrame(animate);
            };
            animate();
        }

        stopAnimation() {
            if (this.animationFrameId) {
                cancelAnimationFrame(this.animationFrameId);
                this.animationFrameId = null;
            }
        }

        drawHoverState() {
            this.drawInitialState();
        }
    }

    // --- 极光效果按钮 (色彩增强版) ---
    class AuroraButton extends CanvasButton {
        constructor(canvasId, text) {
            super(canvasId, text);
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
            this.drawText('#ffffff');
        }
    }

    // --- 初始化按钮 ---
    if (document.getElementById('aurora-generate-btn')) {
        new AuroraButton('aurora-generate-btn', '一键生成最终代码');
    }
});

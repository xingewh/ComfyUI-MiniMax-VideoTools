import { app } from "../../scripts/app.js";

// 触发 rgthree 右键菜单的“执行选中节点”核心逻辑
function triggerRgthreeRightClickExec(node) {
    app.canvas.deselectAll();
    app.canvas.selectNode(node, false);

    if (node.getExtraMenuOptions) {
        const options = [];
        node.getExtraMenuOptions(app.canvas, options);
        
        const execOption = options.find(opt => 
            opt && opt.content && (
                opt.content.includes("执行选中节点") || 
                opt.content.includes("Queue Selected")
            )
        );

        if (execOption && typeof execOption.callback === "function") {
            execOption.callback(null, null, null, null, { target: app.canvas.canvas });
            return;
        }
    }
    app.queuePrompt(0);
}

app.registerExtension({
    name: "Rect.PreviewImageExecButton",
    async nodeCreated(node) {
        if (node.comfyClass === "PreviewImage" || node.comfyClass === "SaveImage") {
            
            // -------------------------------------------------------------
            // 1. 在标题栏（Header）最右上角精准绘制 ▶
            // -------------------------------------------------------------
            const origOnDrawForeground = node.onDrawForeground;
            node.onDrawForeground = function(ctx) {
                if (origOnDrawForeground) {
                    origOnDrawForeground.apply(this, arguments);
                }

                ctx.save();
                ctx.font = "bold 12px sans-serif";
                ctx.textAlign = "right";
                ctx.textBaseline = "middle";

                const titleHeight = LiteGraph.NODE_TITLE_HEIGHT || 30;
                const renderX = this.size[0] - 10;        // 距离标题栏右边缘 10px
                const renderY = -(titleHeight / 2);       // 负坐标：精确定位到标题栏垂直居中处

                // 悬停变亮绿，平时为半透明亮灰
                ctx.fillStyle = this._is_mouse_over_exec ? "#00FF88" : "rgba(255, 255, 255, 0.75)";
                ctx.fillText("▶", renderX, renderY);

                ctx.restore();
            };

            // -------------------------------------------------------------
            // 2. 判定标题栏右上角的点击区域
            // -------------------------------------------------------------
            const origOnMouseDown = node.onMouseDown;
            node.onMouseDown = function(e, localPos, canvas) {
                const titleHeight = LiteGraph.NODE_TITLE_HEIGHT || 30;
                const renderX = this.size[0] - 10;

                // localPos[1] 在负区间代表点击了标题栏
                const isInTitlebarY = localPos[1] >= -titleHeight && localPos[1] <= 0;
                const isInTitlebarX = localPos[0] >= renderX - 20 && localPos[0] <= this.size[0];

                if (isInTitlebarY && isInTitlebarX) {
                    triggerRgthreeRightClickExec(this);
                    return true; // 拦截点击事件，防止误触发节点拖拽
                }

                if (origOnMouseDown) {
                    return origOnMouseDown.apply(this, arguments);
                }
            };

            // 鼠标悬停高亮检测
            const origOnMouseMove = node.onMouseMove;
            node.onMouseMove = function(e, localPos, canvas) {
                if (origOnMouseMove) {
                    origOnMouseMove.apply(this, arguments);
                }

                const titleHeight = LiteGraph.NODE_TITLE_HEIGHT || 30;
                const renderX = this.size[0] - 10;
                
                const isOver = (localPos[1] >= -titleHeight && localPos[1] <= 0) &&
                               (localPos[0] >= renderX - 20 && localPos[0] <= this.size[0]);

                if (this._is_mouse_over_exec !== isOver) {
                    this._is_mouse_over_exec = isOver;
                    this.setDirtyCanvas(true, false);
                }
            };

            // -------------------------------------------------------------
            // 3. 保留 Ctrl + 双击 节点触发逻辑
            // -------------------------------------------------------------
            const origOnDblClick = node.onDblClick;
            node.onDblClick = function (e) {
                if (origOnDblClick) {
                    origOnDblClick.apply(this, arguments);
                }
                if (e && (e.ctrlKey || e.metaKey)) {
                    triggerRgthreeRightClickExec(node);
                }
            };
        }
    }
});
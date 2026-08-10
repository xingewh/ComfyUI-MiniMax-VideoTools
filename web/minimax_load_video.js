import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "MiniMax.FixedSizeLoadVideo",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "MiniMaxLoadVideoFixed") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) onNodeCreated.apply(this, arguments);

                // 默认初始化宽高尺寸（匹配单线大网格格数）
                this.size = [210, 260];

                // 解除内部最小缩放尺寸限制
                this.computeSize = function() {
                    return [160, 180];
                };
            };

            // 增加右键菜单：清除视频预览，且完全保持当前的长宽大小不变
            const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
            nodeType.prototype.getExtraMenuOptions = function (_, options) {
                if (getExtraMenuOptions) getExtraMenuOptions.apply(this, arguments);

                options.push({
                    content: "🧹 清除视频预览",
                    callback: () => {
                        // 1. 记录清除前的节点长宽尺寸，保证零变动
                        const currentWidth = this.size[0];
                        const currentHeight = this.size[1];

                        // 2. 清空图像与视频缓存
                        this.imgs = null;
                        this.imageIndex = null;
                        if (this.generated_images) this.generated_images = null;

                        // 3. 遍历并移除/隐藏视频 DOM 元素与预览部件
                        if (this.widgets) {
                            for (let i = this.widgets.length - 1; i >= 0; i--) {
                                const w = this.widgets[i];
                                if (w.element && w.element.tagName === "VIDEO") {
                                    w.element.pause();
                                    w.element.src = "";
                                    w.element.style.display = "none";
                                    w.element.remove();
                                }
                                if (w.name === "videopreview" || w.type === "video" || w.name === "preview") {
                                    w.value = null;
                                    if (w.element) w.element.style.display = "none";
                                }
                            }
                        }

                        // 4. 原封不动重新锁定当前宽高，刷新 Canvas 渲染
                        this.size = [currentWidth, currentHeight];
                        this.onResize?.(this.size);
                        app.graph.setDirtyCanvas(true, true);
                    }
                });
            };
        }
    }
});
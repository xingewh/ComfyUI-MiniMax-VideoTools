import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "MiniMax.FixedSizeSaveVideo",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "MiniMaxSaveVideoFixed") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) onNodeCreated.apply(this, arguments);

                // 初始化尺寸，且允许用户调整大小
                this.size = [360, 420];
            };

            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                if (onExecuted) onExecuted.apply(this, arguments);

                const videoList = message?.gifs || message?.images;
                if (videoList && videoList.length > 0) {
                    const videoInfo = videoList[0];
                    const videoUrl = `/view?filename=${encodeURIComponent(videoInfo.filename)}&subfolder=${encodeURIComponent(videoInfo.subfolder)}&type=${videoInfo.type}&t=${Date.now()}`;

                    if (!this.videoWidget) {
                        const videoEl = document.createElement("video");
                        videoEl.controls = true;      // 显示音量与播放进度条
                        videoEl.autoplay = true;      // 自动播放
                        videoEl.loop = true;          // 循环播放
                        videoEl.muted = false;        // 默认开启声音
                        videoEl.playsInline = true;
                        
                        // 自适应 UI 样式
                        videoEl.style.width = "100%";
                        videoEl.style.height = "calc(100% - 80px)";
                        videoEl.style.minHeight = "200px";
                        videoEl.style.objectFit = "contain";
                        videoEl.style.borderRadius = "6px";
                        videoEl.style.backgroundColor = "#000";

                        this.videoWidget = this.addDOMWidget("video_preview", "video", videoEl, {
                            serialize: false,
                        });
                    }

                    const videoNode = this.videoWidget.element;
                    videoNode.src = videoUrl;
                    videoNode.play().catch((err) => {
                        // 触发浏览器静音自动播放限制时的兼容处理
                        console.log("[MiniMax Save Video] 自动播放声音被浏览器拦截，已转为静音播放:", err);
                        videoNode.muted = true;
                        videoNode.play();
                    });
                }
            };
        }
    }
});
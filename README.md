Currently, most video loading and saving nodes in ComfyUI dynamically resize themselves based on the loaded or generated video dimensions, which often breaks the carefully arranged workflow layout and visual consistency.



To solve this issue, this node package was developed with the assistance of Gemini.



1\. MiniMax Load Video (Fixed Size)

Zero UI Distortion: Prevents the node from auto-expanding when loading videos, keeping your visual canvas clean and compact.



Audio \& Video Dual Output: Outputs both video frame tensors and independent AUDIO stream tensors, perfectly designed for models like MiniMax-H3 that require video and audio references.



24FPS Unified Resampling: Resamples video input to 24FPS by default to avoid lip-sync issues and temporal motion artifacting.



One-Click Preview Eraser: Context menu right-click option (🧹 Clear Video Preview) that completely purges video caches while strictly maintaining the current node width and height.



2\. MiniMax Save Video (Fixed Size)

Fixed Render Dimensions: Retains its exact size before and after video encoding, ensuring no unwanted UI layout shifting.



Multi-Format Input Flexibility: Supports direct inputs for IMAGE, VIDEO objects, and standalone AUDIO tracks.



Automated Audio Merging: Automatically merges external audio lines into high-compatibility H.264 MP4 videos using FFmpeg.



<p align="center">

&#x20; <img src="workflow.png" alt="ComfyUI MiniMax Workflow Preview" width="100%">

</p>



<p align="center">

&#x20; <img src="load video.png" alt="ComfyUI MiniMax Workflow Preview" width="100%">

</p>



<p align="center">

&#x20; <img src="save video.png" alt="ComfyUI MiniMax Workflow Preview" width="100%">

</p>





针对 ComfyUI 原生及第三方视频节点“界面随预览动态变形”的痛点，在 Gemini 的辅助下开发了这套极简风格的自定义节点包。



🌟 核心特性 (Key Features)

1\. MiniMax Load Video (Fixed Size) | 固定尺寸视频加载节点

界面零变形：彻底解决加载视频后节点被自动拉伸、破坏工作流美观与布局的问题。



音视频双输出：支持同时输出视频帧序列与独立 AUDIO 音频张量，完美适配 MiniMax-H3 等模型对视频/音频参考的需求。



24FPS 统一重采样：默认重采样为 24FPS，有效解决音画不同步及动态失真问题。



一键清除预览：支持右键菜单“🧹 清除视频预览”，且清除后完全锁定并保留当前节点的长宽尺寸，维持界面整洁。



2\. MiniMax Save Video (Fixed Size) | 固定尺寸视频保存节点

尺寸锁定：视频生成与保存后，节点依然保持设定好的紧凑尺寸，不撑乱画布。



多接口灵活输入：同时支持输入 IMAGE（图像）、VIDEO（视频对象）以及独立的 AUDIO（音频）。



音视频自动合成：若连接了音频线，将自动通过 FFmpeg 压制合成带音轨的 H.264 MP4 视频。


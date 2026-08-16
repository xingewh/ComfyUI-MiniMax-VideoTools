import os
import subprocess
import shutil
import time
import json

import folder_paths
import numpy as np
import imageio
import torch


class MiniMaxSaveVideoFixed:
    """
    MiniMax Save Video
    - 保留原节点的 VIDEO / IMAGE / AUDIO 输入
    - 保留 output/video 保存位置
    - 保留前端视频预览
    - 将 ComfyUI 的 prompt / workflow / extra_pnginfo 写入 MP4 元数据
      以便后续拖回 ComfyUI 恢复工作流
    """

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "fps": (
                    "FLOAT",
                    {"default": 24.0, "min": 1.0, "max": 120.0, "step": 1.0},
                ),
                "filename_prefix": (
                    "STRING",
                    {"default": "MiniMax_Video"},
                ),
            },
            "optional": {
                "images": ("IMAGE",),
                "audio": ("AUDIO",),
                "video": ("VIDEO",),
            },
            # ComfyUI 自动注入当前执行任务的 workflow/prompt 信息。
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_video"
    OUTPUT_NODE = True
    CATEGORY = "MiniMax Tools"

    def _extract_frames(self, obj, frame_list):
        """仅提取视频图像帧"""
        if obj is None:
            return

        if hasattr(obj, "images"):
            self._extract_frames(getattr(obj, "images"), frame_list)

        if isinstance(obj, torch.Tensor):
            if obj.ndim == 4:
                for img in obj:
                    img_np = (
                        255.0 * img.cpu().numpy()
                    ).clip(0, 255).astype(np.uint8)
                    frame_list.append(img_np)
            elif obj.ndim == 3:
                img_np = (
                    255.0 * obj.cpu().numpy()
                ).clip(0, 255).astype(np.uint8)
                frame_list.append(img_np)

        elif isinstance(obj, (tuple, list)):
            for item in obj:
                self._extract_frames(item, frame_list)

        elif isinstance(obj, dict):
            for k in ["images", "frames", "video", "components", "data"]:
                if k in obj:
                    self._extract_frames(obj[k], frame_list)

        for method_name in ["get_images", "get_frames", "get_components"]:
            if hasattr(obj, method_name) and callable(getattr(obj, method_name)):
                try:
                    self._extract_frames(
                        getattr(obj, method_name)(), frame_list
                    )
                except Exception:
                    pass

    def _save_audio_to_wav(self, audio_data, temp_wav_path):
        """导出 AUDIO 端口的音频流为临时 WAV 文件"""
        try:
            import scipy.io.wavfile as wavfile

            waveform = audio_data.get("waveform", None)
            sample_rate = audio_data.get("sample_rate", 44100)

            if waveform is not None:
                if isinstance(waveform, torch.Tensor):
                    waveform = waveform.cpu().numpy()

                if waveform.ndim == 3:
                    waveform = waveform[0]

                if waveform.shape[0] in [1, 2] and waveform.shape[1] > 2:
                    waveform = waveform.T

                waveform = np.clip(waveform, -1.0, 1.0)
                audio_int16 = (waveform * 32767).astype(np.int16)
                wavfile.write(temp_wav_path, sample_rate, audio_int16)
                return True

        except Exception as e:
            print(f"[MiniMax Save Video] 音频转换失败: {e}")

        return False

    @staticmethod
    def _json_text(value):
        """
        转成紧凑 JSON。
        ensure_ascii=False 保留中文；default=str 防止某些特殊值导致保存失败。
        """
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            )
        except Exception:
            return json.dumps(str(value), ensure_ascii=False)

    @staticmethod
    def _escape_ffmetadata(value):
        """
        FFmpeg FFMETADATA1 文件格式的转义。
        这是 VideoHelperSuite 目前采用的方式之一。
        """
        value = str(value)
        value = value.replace("\\", "\\\\")
        value = value.replace(";", "\\;")
        value = value.replace("#", "\\#")
        value = value.replace("=", "\\=")
        value = value.replace("\n", "\\\n")
        return value

    def _build_video_metadata(self, prompt=None, extra_pnginfo=None):
        """
        构造两层 metadata：

        1. comment：
           保存完整 JSON 对象，兼容 VideoHelperSuite/ComfyUI 常见的视频
           workflow 元数据读取方式。

        2. workflow / prompt / 其它 extra_pnginfo：
           同时单独保存，兼容较新的 ComfyUI 视频 metadata 机制。
        """
        video_metadata = {}

        if prompt is not None:
            video_metadata["prompt"] = prompt

        if extra_pnginfo is not None:
            try:
                for key, value in extra_pnginfo.items():
                    video_metadata[key] = value
            except Exception:
                pass

        metadata_lines = [";FFMETADATA1"]

        # 完整 JSON 放入 comment。
        if video_metadata:
            metadata_lines.append(
                "comment=" +
                self._escape_ffmetadata(
                    self._json_text(video_metadata)
                )
            )

        # 同时写独立的 prompt / workflow / extra_pnginfo keys。
        if prompt is not None:
            metadata_lines.append(
                "prompt=" +
                self._escape_ffmetadata(self._json_text(prompt))
            )

        if extra_pnginfo is not None:
            try:
                for key, value in extra_pnginfo.items():
                    # workflow 是最关键的字段。
                    metadata_lines.append(
                        f"{key}=" +
                        self._escape_ffmetadata(self._json_text(value))
                    )
            except Exception as e:
                print(
                    f"[MiniMax Save Video] extra_pnginfo metadata "
                    f"处理异常: {e}"
                )

        metadata_lines.append(
            "creation_time=" +
            self._escape_ffmetadata(time.strftime("%Y-%m-%dT%H:%M:%S"))
        )

        return "\n".join(metadata_lines) + "\n"

    def _write_metadata_file(
        self,
        metadata_path,
        prompt=None,
        extra_pnginfo=None,
    ):
        """写 FFmpeg FFMETADATA1 临时文件。"""
        try:
            metadata_text = self._build_video_metadata(
                prompt=prompt,
                extra_pnginfo=extra_pnginfo,
            )

            with open(
                metadata_path,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as f:
                f.write(metadata_text)

            return True

        except Exception as e:
            print(f"[MiniMax Save Video] metadata 文件创建失败: {e}")
            return False

    def _inject_metadata(
        self,
        input_video,
        output_video,
        metadata_path,
    ):
        """
        使用 FFmpeg 重新封装最终 MP4，只写 metadata，不重新编码视频。
        因此不会影响视频画质。
        """
        ffmpeg_path = shutil.which("ffmpeg")

        if not ffmpeg_path:
            print(
                "[MiniMax Save Video] 未找到 FFmpeg，"
                "视频将正常保存，但不会写入 workflow metadata。"
            )
            return False

        cmd = [
            ffmpeg_path,
            "-y",
            "-i", input_video,
            "-i", metadata_path,
            "-map", "0",
            "-map_metadata", "1",
            "-c", "copy",
            "-movflags", "use_metadata_tags",
            "-metadata", "handler_name=ComfyUI",
            output_video,
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            return os.path.exists(output_video)

        except Exception as e:
            print(f"[MiniMax Save Video] workflow metadata 写入失败: {e}")
            try:
                stderr = result.stderr.decode("utf-8", errors="replace")
                print(stderr[-4000:])
            except Exception:
                pass
            return False

    def save_video(
        self,
        fps,
        filename_prefix,
        images=None,
        video=None,
        audio=None,
        prompt=None,
        extra_pnginfo=None,
    ):
        frame_list = []
        target_input = video if video is not None else images

        # 1. 提取图像帧
        self._extract_frames(target_input, frame_list)

        if len(frame_list) == 0:
            raise ValueError(
                "MiniMax Save Video: 必须连接 'images' 或 'video' "
                "端口且包含有效帧！"
            )

        # 2. output/video
        subfolder = "video"
        full_output_folder = os.path.join(
            self.output_dir,
            subfolder,
        )
        os.makedirs(full_output_folder, exist_ok=True)

        # 3. 时间戳 + 3 位序号
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        counter = 1

        while True:
            file_filename = (
                f"{filename_prefix}_{timestamp}_{counter:03d}.mp4"
            )
            file_path = os.path.join(
                full_output_folder,
                file_filename,
            )

            if not os.path.exists(file_path):
                break

            counter += 1

        temp_video_path = os.path.join(
            full_output_folder,
            f"temp_{file_filename}",
        )

        metadata_path = os.path.join(
            full_output_folder,
            f"temp_metadata_{counter:05d}.txt",
        )

        # 4. 编码无声视频
        writer = imageio.get_writer(
            temp_video_path,
            fps=fps,
            codec="libx264",
            quality=8,
        )

        try:
            for frame in frame_list:
                writer.append_data(frame)
        finally:
            writer.close()

        # 5. 音频处理
        has_merged_audio = False

        if audio is not None:
            temp_audio_path = os.path.join(
                full_output_folder,
                f"temp_{counter:05d}.wav",
            )

            if self._save_audio_to_wav(
                audio,
                temp_audio_path,
            ):
                ffmpeg_path = shutil.which("ffmpeg")

                if ffmpeg_path and os.path.exists(temp_audio_path):
                    cmd = [
                        ffmpeg_path,
                        "-y",
                        "-i", temp_video_path,
                        "-i", temp_audio_path,
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-strict", "experimental",
                        file_path,
                    ]

                    try:
                        subprocess.run(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True,
                        )
                        has_merged_audio = True

                    except Exception as e:
                        print(
                            "[MiniMax Save Video] "
                            f"FFmpeg 音频合并异常: {e}"
                        )

                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)

        # 6. 得到最终视频文件
        if not has_merged_audio:
            if os.path.exists(file_path):
                os.remove(file_path)

            shutil.move(
                temp_video_path,
                file_path,
            )
        else:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

        # 7. 写 workflow metadata
        metadata_written = False

        if prompt is not None or extra_pnginfo is not None:
            if self._write_metadata_file(
                metadata_path,
                prompt=prompt,
                extra_pnginfo=extra_pnginfo,
            ):
                # 先生成另一个临时文件，再替换最终文件。
                metadata_video_path = os.path.join(
                    full_output_folder,
                    f"temp_metadata_{file_filename}",
                )

                if self._inject_metadata(
                    file_path,
                    metadata_video_path,
                    metadata_path,
                ):
                    try:
                        os.replace(
                            metadata_video_path,
                            file_path,
                        )
                        metadata_written = True
                    except Exception as e:
                        print(
                            "[MiniMax Save Video] "
                            f"替换 metadata 视频失败: {e}"
                        )

                if os.path.exists(metadata_video_path):
                    os.remove(metadata_video_path)

        if os.path.exists(metadata_path):
            os.remove(metadata_path)

        if not metadata_written and (
            prompt is not None or extra_pnginfo is not None
        ):
            print(
                "[MiniMax Save Video] 警告：视频已正常保存，"
                "但 workflow metadata 未成功写入。"
            )

        # 8. 返回前端 UI 播放结果
        return {
            "ui": {
                "images": [{
                    "filename": file_filename,
                    "subfolder": subfolder,
                    "type": self.type,
                    "format": "video/h264",
                }],
                "gifs": [{
                    "filename": file_filename,
                    "subfolder": subfolder,
                    "type": self.type,
                    "format": "video/h264",
                }],
            }
        }


NODE_CLASS_MAPPINGS = {
    "MiniMaxSaveVideoFixed": MiniMaxSaveVideoFixed,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxSaveVideoFixed": "MiniMax Save Video Fixed + Workflow",
}

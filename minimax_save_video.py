import os
import subprocess
import shutil
import folder_paths
import numpy as np
import imageio
import torch

class MiniMaxSaveVideoFixed:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 120.0, "step": 1.0}),
                "filename_prefix": ("STRING", {"default": "MiniMax_Video"}),
            },
            "optional": {
                "images": ("IMAGE",), 
                "audio": ("AUDIO",),  # 独立音频输入线
                "video": ("VIDEO",),  
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save_video"
    OUTPUT_NODE = True
    CATEGORY = "MiniMax Tools"

    def _extract_frames(self, obj, frame_list):
        """递归提取视频图像帧"""
        if obj is None:
            return

        if hasattr(obj, "images"):
            self._extract_frames(getattr(obj, "images"), frame_list)

        if isinstance(obj, torch.Tensor):
            if obj.ndim == 4:
                for img in obj:
                    img_np = (255.0 * img.cpu().numpy()).clip(0, 255).astype(np.uint8)
                    frame_list.append(img_np)
            elif obj.ndim == 3:
                img_np = (255.0 * obj.cpu().numpy()).clip(0, 255).astype(np.uint8)
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
                    self._extract_frames(getattr(obj, method_name)(), frame_list)
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
                if waveform.ndim == 3:  # (batch, channels, samples)
                    waveform = waveform[0]
                if waveform.shape[0] in [1, 2] and waveform.shape[1] > 2:  # (channels, samples) -> (samples, channels)
                    waveform = waveform.T
                
                waveform = np.clip(waveform, -1.0, 1.0)
                audio_int16 = (waveform * 32767).astype(np.int16)
                wavfile.write(temp_wav_path, sample_rate, audio_int16)
                return True
        except Exception as e:
            print(f"[MiniMax Save Video] 音频转换失败: {e}")
        return False

    def save_video(self, fps, filename_prefix, images=None, video=None, audio=None):
        frame_list = []
        target_input = video if video is not None else images

        # 1. 提取图像帧
        self._extract_frames(target_input, frame_list)

        if len(frame_list) == 0:
            raise ValueError("MiniMax Save Video: 必须连接 'images' 或 'video' 端口且包含有效帧！")

        # 2. 准备输出文件名与路径
        first_frame = frame_list[0]
        h, w = first_frame.shape[0], first_frame.shape[1]
        full_output_folder, filename, counter, subfolder, filename_prefix = \
            folder_paths.get_save_image_path(filename_prefix, self.output_dir, w, h)

        file_filename = f"{filename}_{counter:05_}.mp4"
        file_path = os.path.join(full_output_folder, file_filename)
        temp_video_path = os.path.join(full_output_folder, f"temp_{file_filename}")

        # 3. 编码画面视频文件
        writer = imageio.get_writer(temp_video_path, fps=fps, codec='libx264', quality=8)
        for frame in frame_list:
            writer.append_data(frame)
        writer.close()

        # 4. 如果连了 audio 端口，使用 FFmpeg 压入音轨
        has_merged_audio = False
        if audio is not None:
            temp_audio_path = os.path.join(full_output_folder, f"temp_{counter:05_}.wav")
            if self._save_audio_to_wav(audio, temp_audio_path):
                ffmpeg_path = shutil.which("ffmpeg")
                if ffmpeg_path and os.path.exists(temp_audio_path):
                    cmd = [
                        ffmpeg_path, "-y",
                        "-i", temp_video_path,
                        "-i", temp_audio_path,
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-strict", "experimental",
                        file_path
                    ]
                    try:
                        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                        has_merged_audio = True
                    except Exception as e:
                        print(f"[MiniMax Save Video] FFmpeg 音频合并异常: {e}")
                
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)

        # 5. 清理临时文件
        if not has_merged_audio:
            if os.path.exists(file_path):
                os.remove(file_path)
            shutil.move(temp_video_path, file_path)
        else:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

        return {
            "ui": {
                "images": [{
                    "filename": file_filename,
                    "subfolder": subfolder,
                    "type": self.type,
                    "format": "video/h264"
                }],
                "gifs": [{
                    "filename": file_filename,
                    "subfolder": subfolder,
                    "type": self.type,
                    "format": "video/h264"
                }]
            }
        }
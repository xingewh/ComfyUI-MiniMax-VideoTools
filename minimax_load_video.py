import os
import subprocess
import shutil
import tempfile
import torch
import numpy as np
import folder_paths
import imageio

class MiniMaxLoadVideoFixed:
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "视频文件": (sorted(files), {"video_upload": True}),
                "强制帧率": ("INT", {"default": 0, "min": 0, "max": 120, "step": 1}),
                "帧数读取上限": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "跳过前X帧": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "抽帧间隔": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT", "AUDIO")
    RETURN_NAMES = ("图像", "帧计数", "音频")
    FUNCTION = "load_video"
    CATEGORY = "MiniMax Tools"

    def load_video(self, 视频文件, 强制帧率=0, 帧数读取上限=0, 跳过前X帧=0, 抽帧间隔=1):
        video_path = folder_paths.get_annotated_filepath(视频文件)

        # 1. 提取视频帧
        reader = imageio.get_reader(video_path, 'ffmpeg')
        frames = []
        for i, frame in enumerate(reader):
            if i < 跳过前X帧:
                continue
            if (i - 跳过前X帧) % 抽帧间隔 != 0:
                continue
            
            img_tensor = torch.from_numpy(frame.astype(np.float32) / 255.0)
            frames.append(img_tensor)

            if 帧数读取上限 > 0 and len(frames) >= 帧数读取上限:
                break

        reader.close()

        if len(frames) == 0:
            raise ValueError(f"无法读取视频帧: {video_path}")

        images = torch.stack(frames, dim=0)
        frame_count = len(frames)

        # 2. 使用 FFmpeg 提取音频（全面兼容 AAC / MP3 / WAV）
        audio = self._extract_audio_ffmpeg(video_path)

        return (images, frame_count, audio)

    def _extract_audio_ffmpeg(self, video_path):
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            return None

        # 创建临时 wav 文件提取音频流
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name

        try:
            cmd = [
                ffmpeg_path, "-y",
                "-i", video_path,
                "-vn",                    # 不要视频
                "-acodec", "pcm_s16le",  # 强转 PCM 16bit WAV
                "-ar", "44100",           # 采样率 44.1kHz
                "-ac", "2",               # 双声道
                temp_wav_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(temp_wav_path) and os.path.getsize(temp_wav_path) > 100:
                import scipy.io.wavfile as wavfile
                sample_rate, data = wavfile.read(temp_wav_path)
                
                # 转为 ComfyUI 标准 AUDIO 格式 float32 [-1.0, 1.0]
                data = data.astype(np.float32) / 32767.0
                if data.ndim == 1:
                    data = np.expand_dims(data, axis=1) # (samples, 1)
                
                # 转换为 (channels, samples)
                waveform = torch.from_numpy(data.T).unsqueeze(0) # (1, channels, samples)
                
                return {
                    "waveform": waveform,
                    "sample_rate": sample_rate
                }
        except Exception as e:
            print(f"[MiniMax Load Video] 音频提取失败: {e}")
        finally:
            if os.path.exists(temp_wav_path):
                os.remove(temp_wav_path)

        return None
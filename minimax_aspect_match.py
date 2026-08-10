import math
import torch
import torch.nn.functional as F

class MiniMaxAspectMatch:
    ASPECT_RATIOS = {
        "1:1 (Square)": (1.0, 1.0),
        "2:3 (Portrait Photo)": (2.0, 3.0),
        "3:2 (Photo)": (3.0, 2.0),
        "3:4 (Portrait Standard)": (3.0, 4.0),
        "4:3 (Standard)": (4.0, 3.0),
        "9:16 (Portrait Widescreen)": (9.0, 16.0),
        "16:9 (Widescreen)": (16.0, 9.0),
        "21:9 (Ultrawide)": (21.0, 9.0),
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (list(cls.ASPECT_RATIOS.keys()), {"default": "1:1 (Square)"}),
                "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 16.0, "step": 0.1}),
                "multiple": ("INT", {"default": 8, "min": 1, "max": 64, "step": 1}),
                "auto_detect_image": ("BOOLEAN", {"default": True, "label_on": "开启自动适配", "label_off": "使用手动选择"}),
            },
            "optional": {
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING", "FLOAT", "IMAGE")
    RETURN_NAMES = ("width", "height", "ratio_str", "aspect_ratio", "cropped_image")
    FUNCTION = "calculate_resolution"
    CATEGORY = "facetools"

    def calculate_resolution(self, aspect_ratio, megapixels, multiple, auto_detect_image, image=None):
        target_ratio_val = None

        # 1. 判断长宽比
        if auto_detect_image and image is not None:
            _, h, w, _ = image.shape
            img_ratio = w / float(h)
            
            best_key = min(
                self.ASPECT_RATIOS.keys(),
                key=lambda k: abs((self.ASPECT_RATIOS[k][0] / self.ASPECT_RATIOS[k][1]) - img_ratio)
            )
            aspect_ratio = best_key
            rw, rh = self.ASPECT_RATIOS[aspect_ratio]
            target_ratio_val = rw / rh
        else:
            rw, rh = self.ASPECT_RATIOS[aspect_ratio]
            target_ratio_val = rw / rh

        # 2. 视频生成的低/目标分辨率计算（受 megapixels 影响）
        total_pixels = megapixels * 1024 * 1024
        raw_w = math.sqrt(total_pixels * target_ratio_val)
        raw_h = raw_w / target_ratio_val

        final_w = int(round(raw_w / multiple) * multiple)
        final_h = int(round(raw_h / multiple) * multiple)

        # 3. 参考图处理：只做长宽比 Crop，保留原图高清分辨率（仅做整除对齐）
        out_image = None
        if image is not None:
            batch, orig_h, orig_w, channels = image.shape
            orig_ratio = orig_w / float(orig_h)

            # 计算最大居中裁剪区域
            if orig_ratio > target_ratio_val:
                crop_h = orig_h
                crop_w = int(round(orig_h * target_ratio_val))
            else:
                crop_w = orig_w
                crop_h = int(round(orig_w / target_ratio_val))

            start_x = max(0, (orig_w - crop_w) // 2)
            start_y = max(0, (orig_h - crop_h) // 2)

            cropped = image[:, start_y:start_y + crop_h, start_x:start_x + crop_w, :]

            # 微调裁剪后的图片尺寸，使其宽度和高度严格能被 multiple 整除（不改变清晰度，仅裁掉边缘 1-2 像素）
            high_res_w = (crop_w // multiple) * multiple
            high_res_h = (crop_h // multiple) * multiple

            out_image = cropped[:, :high_res_h, :high_res_w, :]
        else:
            out_image = None

        return (final_w, final_h, aspect_ratio, target_ratio_val, out_image)
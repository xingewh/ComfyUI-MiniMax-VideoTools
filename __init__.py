from .minimax_load_video import MiniMaxLoadVideoFixed
from .minimax_save_video import MiniMaxSaveVideoFixed

NODE_CLASS_MAPPINGS = {
    "MiniMaxLoadVideoFixed": MiniMaxLoadVideoFixed,
    "MiniMaxSaveVideoFixed": MiniMaxSaveVideoFixed,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxLoadVideoFixed": "MiniMax Load Video (Fixed Size)",
    "MiniMaxSaveVideoFixed": "MiniMax Save Video (Fixed Size)",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
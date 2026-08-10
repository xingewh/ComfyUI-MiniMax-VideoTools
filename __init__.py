from .minimax_aspect_match import MiniMaxAspectMatch
from .minimax_save_video import MiniMaxSaveVideoFixed
from .minimax_load_video import MiniMaxLoadVideoFixed

NODE_CLASS_MAPPINGS = {
    "MiniMaxAspectMatch": MiniMaxAspectMatch,
    "MiniMaxSaveVideoFixed": MiniMaxSaveVideoFixed,
    "MiniMaxLoadVideoFixed": MiniMaxLoadVideoFixed
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxAspectMatch": "MiniMax Aspect Ratio Matcher",
    "MiniMaxSaveVideoFixed": "MiniMax Save Video (Fixed Size)",
    "MiniMaxLoadVideoFixed": "MiniMax Load Video (Fixed Size)"
}

WEB_DIRECTORY = "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
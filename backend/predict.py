"""
predict.py - run the trained model on a video.

CLI:  python predict.py path/to/video.mp4
API:  from predict import predict_video
"""
import sys
import threading

import torch

from model import LipReader
from preprocess import DEVICE, IN_CHANNELS, VOCAB, decode, preprocess_video

MODEL_PATH = "lipreader.pt"

_model = None
_lock = threading.Lock()


def get_model():
    """Load the model once and reuse it for every request."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                m = LipReader(len(VOCAB) + 1, IN_CHANNELS).to(DEVICE)
                m.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
                m.eval()
                _model = m
    return _model


@torch.no_grad()
def predict_video(video_path):
    frames = preprocess_video(video_path).to(DEVICE)
    logits = get_model()(frames)
    return decode(logits)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--snap"]
    if len(args) != 1:
        print("Usage: python predict.py <video_path> [--snap]")
        sys.exit(1)
    text = predict_video(args[0])
    if "--snap" in sys.argv:   # force GRID 6-word grammar (GRID-style speech only)
        from grid_grammar import snap_to_grid
        text = snap_to_grid(text)[0]
    print("Prediction:", text)

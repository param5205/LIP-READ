import sys 
import threading

import torch


from model import LipReader
from preprocess import DEVICE, IN_CHANNELS, VOCAB, decode, preprocess_video

MODEL_PATH="lipreader.pt"

_model = None
_lock= threading.Lock()


def get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                m= LipReader(len(VOCAB) +1, IN_CHANNELS). to(DEVICE)
                m.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
                m.eval()
                _model=m
    return _model


@torch.no_grad()
def predict_video(video_path):
    frames=preprocess_video(video_path).to(DEVICE)
    logits=get_model()(frames)
    return decode(logits)


if __name__ == "__main__":
    if len(sys.argv) !=2:
        print("Usage python predict.py <video_path>")
        sys.exit(1)
    print("Prediction:", predict_video(sys.argv[1]))
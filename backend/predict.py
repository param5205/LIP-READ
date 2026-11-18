"""
predict.py - run the trained model on a video.

CLI:  python predict.py path/to/video.mp4
      python predict.py path/to/video.mp4 --snap                         (GRID 6-word clean-up)
      python predict.py path/to/video.mp4 --phrases intro_phrases.txt    (match to your own lines)
API:  from predict import predict_video

Web page / app.py: to match results to your intro lines, set this before starting the app
(PowerShell):  $env:LIPREAD_PHRASES="intro_phrases.txt"; python app.py
"""
import os
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
    text = decode(logits)
    phrases_file = os.environ.get("LIPREAD_PHRASES")   # optional closed-set matching
    if phrases_file:
        from grid_grammar import load_phrases, snap_to_phrases
        text = snap_to_phrases(text, load_phrases(phrases_file))[0]
    return text


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--phrases" in argv:                              # --phrases <file>
        i = argv.index("--phrases")
        if i + 1 >= len(argv):
            print("Usage: python predict.py <video_path> [--snap] [--phrases <file>]")
            sys.exit(1)
        os.environ["LIPREAD_PHRASES"] = argv[i + 1]
        del argv[i:i + 2]
    args = [a for a in argv if a != "--snap"]
    if len(args) != 1:
        print("Usage: python predict.py <video_path> [--snap] [--phrases <file>]")
        sys.exit(1)
    text = predict_video(args[0])
    if "--snap" in sys.argv:   # force GRID 6-word grammar (GRID-style speech only)
        from grid_grammar import snap_to_grid
        text = snap_to_grid(text)[0]
    print("Prediction:", text)

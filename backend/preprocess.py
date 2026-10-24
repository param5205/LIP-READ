import os
import urllib.request

import cv2
import numpy as np
import torch
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

IMG_SIZE = (96, 96)       
NUM_FRAMES = 75            
GRAYSCALE = True
MEAN, STD = 0.421, 0.165   
VOCAB = list("abcdefghijklmnopqrstuvwxyz '")   
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

IN_CHANNELS = 1 if GRAYSCALE else 3

# Face landmarker model (downloaded automatically on first use, about 4 MB)
FACE_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_landmarker.task")
FACE_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
                  "face_landmarker/float16/1/face_landmarker.task")

# Landmark indices around the lips (same points the old FACEMESH_LIPS used)
_LIP_IDX = sorted({
    0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178,
    181, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321,
    324, 375, 402, 405, 409, 415,
})


def create_face_detector():
    if not os.path.exists(FACE_MODEL_PATH):
        print("Downloading face landmark model (one time)...")
        urllib.request.urlretrieve(FACE_MODEL_URL, FACE_MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=FACE_MODEL_PATH),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
    )
    return vision.FaceLandmarker.create_from_options(options)


def _crop_mouth(detector, frame_bgr, prev_box):
    h, w = frame_bgr.shape[:2]
    rgb = np.ascontiguousarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))

    if result.face_landmarks:
        lm = result.face_landmarks[0]
        xs = np.array([lm[i].x * w for i in _LIP_IDX])
        ys = np.array([lm[i].y * h for i in _LIP_IDX])
        cx, cy = xs.mean(), ys.mean()
        half = max(xs.max() - xs.min(), ys.max() - ys.min()) * 0.75
        box = (int(cx - half), int(cy - half), int(cx + half), int(cy + half))
    elif prev_box is not None:
        box = prev_box
    else:
        return None, None

    x1, y1 = max(box[0], 0), max(box[1], 0)
    x2, y2 = min(box[2], w), min(box[3], h)
    if x2 <= x1 or y2 <= y1:
        return None, box
    return frame_bgr[y1:y2, x1:x2], box


def preprocess_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frames, prev_box = [], None

    # A new detector per call keeps this safe under Flask's threaded server
    with create_face_detector() as detector:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            mouth, prev_box = _crop_mouth(detector, frame, prev_box)
            if mouth is None:
                continue
            frames.append(prepare_mouth(mouth))
    cap.release()

    if not frames:
        raise ValueError("No face/mouth detected in the video.")
    return frames_to_tensor(frames)


def prepare_mouth(mouth_bgr):
    mouth = cv2.resize(mouth_bgr, IMG_SIZE)
    if GRAYSCALE:
        mouth = cv2.cvtColor(mouth, cv2.COLOR_BGR2GRAY)
    return mouth


def frames_to_tensor(frames):
    if len(frames) >= NUM_FRAMES:
        idx = np.linspace(0, len(frames) - 1, NUM_FRAMES).astype(int)
        frames = [frames[i] for i in idx]
    else:
        frames = list(frames) + [frames[-1]] * (NUM_FRAMES - len(frames))

    arr = (np.stack(frames).astype(np.float32) / 255.0 - MEAN) / STD
    arr = arr[None, ...] if GRAYSCALE else arr.transpose(3, 0, 1, 2)
    return torch.from_numpy(np.ascontiguousarray(arr)).unsqueeze(0)


def encode(text):
    return [VOCAB.index(c) + 1 for c in text.lower() if c in VOCAB]


def decode(logits):
    ids = logits.argmax(dim=-1)[0].tolist()
    out, prev = [], 0
    for i in ids:
        if i != prev and i != 0:
            out.append(VOCAB[i - 1])
        prev = i
    return "".join(out).strip()

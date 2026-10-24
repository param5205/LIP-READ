import argparse
import threading
import time
from collections import deque

import cv2
import numpy as np
import torch

from predict import get_model
from preprocess import (DEVICE, NUM_FRAMES, _crop_mouth, create_face_detector, decode,
                        frames_to_tensor, prepare_mouth)

TARGET_FPS = 25    
STRIDE_SEC = 0.5    
MAX_LOST = 10       


class InferenceWorker(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)
        self.model = get_model()
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.pending = None
        self.text = ""

    def submit(self, frames):
        with self.lock:
            self.pending = frames
        self.event.set()

    @torch.no_grad()
    def run(self):
        while True:
            self.event.wait()
            self.event.clear()
            with self.lock:
                frames, self.pending = self.pending, None
            if frames is None:
                continue
            x = frames_to_tensor(frames).to(DEVICE)
            self.text = decode(self.model(x))


def put_text(img, text, org, scale=0.7, color=(255, 255, 255)):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0, help="camera index")
    ap.add_argument("--motion", type=float, default=2.0,
                    help="min mouth movement to count as speaking (watch the 'motion' value on screen)")
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera {args.cam}")

    worker = InferenceWorker()
    worker.start()

    buf = deque(maxlen=NUM_FRAMES)
    last_add = last_run = 0.0
    lost, motion, speaking = 0, 0.0, False

    with create_face_detector() as face_mesh:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            now = time.time()

            # No prev_box here: if the face disappears we want to know about it
            mouth, box = _crop_mouth(face_mesh, frame, None)

            if mouth is None:
                lost += 1
                if lost >= MAX_LOST:
                    buf.clear()
                    speaking = False
            else:
                lost = 0
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
                # Sample at the training frame rate so mouth speed matches training
                if now - last_add >= 1.0 / TARGET_FPS:
                    buf.append(prepare_mouth(mouth))
                    last_add = now

            # Once the window is full, run the model every STRIDE_SEC
            if len(buf) == NUM_FRAMES and lost == 0 and now - last_run >= STRIDE_SEC:
                window = list(buf)
                arr = np.stack(window).astype(np.int16)
                motion = float(np.abs(np.diff(arr, axis=0)).mean())
                speaking = motion >= args.motion
                if speaking:
                    worker.submit(window)
                last_run = now

           
            h, w = frame.shape[:2]
            if lost >= MAX_LOST or (mouth is None and len(buf) == 0):
                status = "No face detected"
            elif len(buf) < NUM_FRAMES:
                status = f"Collecting frames {len(buf)}/{NUM_FRAMES}"
            elif not speaking:
                status = "Not speaking"
            else:
                status = "Reading..."
            put_text(frame, f"{status}   motion {motion:.1f}", (10, 30), 0.6, (0, 255, 255))

            if speaking and worker.text:
                put_text(frame, worker.text, (10, h - 20), 0.9)

            cv2.imshow("Live lip reading  (q = quit, c = clear)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("c"):
                buf.clear()
                worker.text = ""

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

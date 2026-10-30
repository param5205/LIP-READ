"""
live.py - real-time lip reading from a webcam.

Two modes:
  sentence (default) - press SPACE, wait for the 3-2-1 countdown, say ONE sentence
                       while "RECORDING" shows (3 seconds), the model reads it once.
                       This matches how the model was trained (one whole sentence).
  continuous         - sliding window, reads all the time (less accurate).

Run:   python live.py                       (sentence mode, GRID clean-up on)
       python live.py --mode continuous
       python live.py --no-snap             (do not force GRID grammar)
       python live.py --cam 1               (another camera)
Keys:  SPACE = record a sentence, c = clear text, q = quit

Run this on the computer that has the webcam (not on a remote server).
"""
import argparse
import threading
import time
from collections import deque

import cv2
import numpy as np
import torch

from grid_grammar import snap_to_grid
from predict import get_model
from preprocess import (DEVICE, NUM_FRAMES, _crop_mouth, create_face_detector, decode,
                        frames_to_tensor, prepare_mouth)

TARGET_FPS = 25     # frame rate of your training videos (GRID = 25)
STRIDE_SEC = 0.5    # continuous mode: run the model this often once the window is full
MAX_LOST = 10       # continuous mode: frames without a face before the buffer is cleared
COUNTDOWN = 3       # sentence mode: seconds before recording starts
MAX_MISSING = 15    # sentence mode: abort if the face is lost for this many frames in a row


class InferenceWorker(threading.Thread):
    """Runs the model in the background so the video never freezes.
    Only the newest window is kept; older ones are skipped if the model is slow."""

    def __init__(self, snap):
        super().__init__(daemon=True)
        self.model = get_model()
        self.snap = snap
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.pending = None
        self.raw = ""
        self.text = ""
        self.version = 0     # increases after every finished prediction

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
            raw = decode(self.model(x))
            self.raw = raw
            self.text = snap_to_grid(raw)[0] if self.snap else raw
            self.version += 1


def put_text(img, text, org, scale=0.7, color=(255, 255, 255)):
    """Text with a dark outline so it is readable on any background."""
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0, help="camera index")
    ap.add_argument("--mode", choices=["sentence", "continuous"], default="sentence")
    ap.add_argument("--no-snap", action="store_true",
                    help="do not force the GRID 6-word grammar on the output")
    ap.add_argument("--motion", type=float, default=2.0,
                    help="continuous mode: min mouth movement to count as speaking")
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera {args.cam}")

    worker = InferenceWorker(snap=not args.no_snap)
    worker.start()

    buf = deque(maxlen=NUM_FRAMES)
    last_add = last_run = 0.0
    lost, motion, speaking = 0, 0.0, False

    # sentence-mode state: idle -> countdown -> recording -> reading -> idle
    state, state_start, missing = "idle", 0.0, 0
    rec = []
    shown_version = 0
    message = ""

    with create_face_detector() as face_mesh:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            now = time.time()
            h, w = frame.shape[:2]

            mouth, box = _crop_mouth(face_mesh, frame, None)
            if mouth is not None:
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)

            key = cv2.waitKey(1) & 0xFF

            if args.mode == "sentence":
                if state == "idle":
                    if key == ord(" "):
                        state, state_start, message = "countdown", now, ""
                        worker.text = worker.raw = ""
                    status = "Press SPACE, then say one sentence"
                    if mouth is None:
                        status = "No face detected - face the camera"
                elif state == "countdown":
                    left = COUNTDOWN - (now - state_start)
                    if left <= 0:
                        state, state_start, rec, missing, last_add = "recording", now, [], 0, 0.0
                    else:
                        put_text(frame, str(int(left) + 1), (w // 2 - 20, h // 2), 3.0, (0, 255, 255))
                        status = "Get ready..."
                if state == "recording":
                    status = f"RECORDING {len(rec)}/{NUM_FRAMES} - speak now"
                    if mouth is None:
                        missing += 1
                        if rec and missing < MAX_MISSING and now - last_add >= 1.0 / TARGET_FPS:
                            rec.append(rec[-1])   # hold the last mouth for a short dropout
                            last_add = now
                    else:
                        missing = 0
                        if now - last_add >= 1.0 / TARGET_FPS:
                            rec.append(prepare_mouth(mouth))
                            last_add = now
                    if missing >= MAX_MISSING:
                        state, message = "idle", "Face lost - try again"
                    elif len(rec) >= NUM_FRAMES:
                        worker.submit(list(rec))
                        state = "reading"
                        status = "Reading..."
                elif state == "reading":
                    status = "Reading..."
                    if worker.version != shown_version:
                        shown_version = worker.version
                        state = "idle"
                put_text(frame, status, (10, 30), 0.6, (0, 255, 255))
                if message:
                    put_text(frame, message, (10, h - 20), 0.8, (0, 0, 255))
                elif worker.text:
                    put_text(frame, worker.text, (10, h - 20), 0.9)
                    if args.no_snap is False and worker.raw != worker.text:
                        put_text(frame, "raw: " + worker.raw, (10, h - 55), 0.5, (200, 200, 200))
            else:
                # ---------------- continuous mode ----------------
                if mouth is None:
                    lost += 1
                    if lost >= MAX_LOST:
                        buf.clear()
                        speaking = False
                else:
                    lost = 0
                    if now - last_add >= 1.0 / TARGET_FPS:
                        buf.append(prepare_mouth(mouth))
                        last_add = now

                if len(buf) == NUM_FRAMES and lost == 0 and now - last_run >= STRIDE_SEC:
                    window = list(buf)
                    arr = np.stack(window).astype(np.int16)
                    motion = float(np.abs(np.diff(arr, axis=0)).mean())
                    speaking = motion >= args.motion
                    if speaking:
                        worker.submit(window)
                    last_run = now

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

            if key == ord("q"):
                break
            if key == ord("c"):
                buf.clear()
                worker.text = worker.raw = ""
                message = ""

            cv2.imshow("Live lip reading  (SPACE = record, c = clear, q = quit)", frame)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

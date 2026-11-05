"""
record_clips.py - record your OWN GRID-style clips to fine-tune the model on your webcam/face.

Run (in the backend folder, venv active):  python record_clips.py
  python record_clips.py --count 150 --cam 0
Each round: a random GRID sentence is shown. Press SPACE, wait for 3-2-1, read it aloud
(silently mouthing it is also fine) for 3 seconds. The clip is saved to
  data/videos/me_0001.mp4  and  data/labels/me_0001.txt
Keys: SPACE = record, d = delete the last clip, s = skip sentence, q = quit
Re-running continues numbering (existing me_*.mp4 files are kept).
"""
import argparse
import os
import random
import re
import time

import cv2

COMMANDS = ["bin", "lay", "place", "set"]
COLOURS = ["blue", "green", "red", "white"]
PREPS = ["at", "by", "in", "with"]
LETTERS = list("abcdefghijklmnopqrstuvxyz")
DIGITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
ADVERBS = ["again", "now", "please", "soon"]

FPS = 25
SECONDS = 3.0
COUNTDOWN = 3


def new_sentence():
    return " ".join([random.choice(COMMANDS), random.choice(COLOURS), random.choice(PREPS),
                     random.choice(LETTERS), random.choice(DIGITS), random.choice(ADVERBS)])


def load_sentences(path):
    """Read lines like '12. lay red at c four now' (ignores everything else)."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s*\d+\.\s+([a-z ]+?)\s*$", line)
            if m:
                out.append(m.group(1))
    return out


def put_text(img, text, org, scale=0.8, color=(255, 255, 255)):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA)


def next_index(vdir):
    nums = [int(f[3:-4]) for f in os.listdir(vdir)
            if f.startswith("me_") and f.endswith(".mp4") and f[3:-4].isdigit()]
    return max(nums, default=0) + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--count", type=int, default=150, help="how many clips to record this session")
    ap.add_argument("--out", default="data")
    ap.add_argument("--sentences", help="file with a numbered sentence list (practice_sentences.txt); "
                                        "default = random sentences")
    ap.add_argument("--start", type=int, default=1, help="with --sentences: first sentence number to read")
    args = ap.parse_args()

    vdir, ldir = os.path.join(args.out, "videos"), os.path.join(args.out, "labels")
    os.makedirs(vdir, exist_ok=True)
    os.makedirs(ldir, exist_ok=True)

    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera {args.cam}")

    idx = next_index(vdir)
    saved, last_name = 0, None
    plan = load_sentences(args.sentences) if args.sentences else None
    pos = max(args.start - 1, 0)

    def next_sentence():
        nonlocal pos
        if plan is None:
            return new_sentence()
        if pos >= len(plan):
            raise SystemExit("Finished the sentence list.")
        pos += 1
        return plan[pos - 1]

    sentence = next_sentence()
    state, t0 = "idle", 0.0
    frames, last_add = [], 0.0
    msg = ""

    while saved < args.count:
        ok, frame = cap.read()
        if not ok:
            break
        now = time.time()
        h, w = frame.shape[:2]
        shown = frame.copy()
        key = cv2.waitKey(1) & 0xFF

        if state == "idle":
            if key == ord(" "):
                state, t0, msg = "countdown", now, ""
            elif key == ord("s"):
                sentence = next_sentence()
            elif key == ord("d") and last_name:
                for p in (os.path.join(vdir, last_name + ".mp4"), os.path.join(ldir, last_name + ".txt")):
                    if os.path.exists(p):
                        os.remove(p)
                saved -= 1
                msg, last_name = f"Deleted {last_name}", None
        elif state == "countdown":
            left = COUNTDOWN - (now - t0)
            if left <= 0:
                state, frames, last_add = "recording", [], 0.0
            else:
                put_text(shown, str(int(left) + 1), (w // 2 - 20, h // 2), 3.0, (0, 255, 255))
        if state == "recording":
            if now - last_add >= 1.0 / FPS:
                frames.append(frame.copy())
                last_add = now
            put_text(shown, "RECORDING", (10, 60), 0.9, (0, 0, 255))
            if len(frames) >= int(FPS * SECONDS):
                name = f"me_{idx:04d}"
                out = cv2.VideoWriter(os.path.join(vdir, name + ".mp4"),
                                      cv2.VideoWriter_fourcc(*"mp4v"), FPS, (w, h))
                for f in frames:
                    out.write(f)
                out.release()
                with open(os.path.join(ldir, name + ".txt"), "w") as fh:
                    fh.write(sentence + "\n")
                idx, saved, last_name = idx + 1, saved + 1, name
                msg = f"Saved {name}"
                state = "idle"
                if plan is not None and pos >= len(plan):
                    print("Finished the sentence list.")
                    break
                sentence = next_sentence()

        put_text(shown, f"Say: {sentence}", (10, 30), 0.9, (0, 255, 0))
        if plan is not None:
            put_text(shown, f"sentence {pos}/{len(plan)}", (w - 220, 30), 0.6, (255, 255, 0))
        put_text(shown, f"saved {saved}/{args.count}  {msg}", (10, h - 15), 0.6, (0, 255, 255))
        if state == "idle":
            put_text(shown, "SPACE=record  s=skip  d=delete last  q=quit", (10, h - 45), 0.5)
        cv2.imshow("Record clips", shown)
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"Saved {saved} clips in {vdir}")


if __name__ == "__main__":
    main()

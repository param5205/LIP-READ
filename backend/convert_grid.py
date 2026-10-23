"""
Convert the GRID corpus into the format the backend expects.

  GRID:   <videos>/s1/bbaf2n.mpg      <aligns>/s1/bbaf2n.align
  Output: <out>/videos/s1_bbaf2n.mp4  <out>/labels/s1_bbaf2n.txt   (lowercase sentence)

Usage (run from the backend folder or anywhere):
  python convert_grid.py --videos path/to/grid/videos --aligns path/to/grid/alignments --out data
  python convert_grid.py --videos ... --aligns ... --out data --limit 200      # quick test
  python convert_grid.py --videos ... --aligns ... --out data --speakers s1 s2

If the .align files sit next to the videos, omit --aligns.
Safe to re-run: clips that already exist are skipped.
"""
import argparse
import sys
from pathlib import Path

import cv2

IGNORE = {"sil", "sp", "spn", ""}


def read_align(path):
    words = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 3:
            w = parts[2].lower()
            if w not in IGNORE:
                words.append(w)
    return " ".join(words)


def convert_video(src, dst):
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        return False
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        out.write(frame)
        n += 1
    cap.release()
    out.release()
    if n == 0:
        Path(dst).unlink(missing_ok=True)
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description="Convert GRID .mpg + .align to .mp4 + .txt")
    ap.add_argument("--videos", required=True, help="folder containing the .mpg files (searched recursively)")
    ap.add_argument("--aligns", help="folder containing .align files (default: same as --videos)")
    ap.add_argument("--out", default="data", help="output folder (creates videos/ and labels/)")
    ap.add_argument("--speakers", nargs="*", help="only these speaker folders, e.g. s1 s2")
    ap.add_argument("--limit", type=int, default=0, help="stop after N clips (0 = all)")
    a = ap.parse_args()

    vroot = Path(a.videos)
    aroot = Path(a.aligns) if a.aligns else vroot
    for p in (vroot, aroot):
        if not p.is_dir():
            sys.exit(f"Folder not found: {p}")

    # index alignments by (speaker folder, clip name) because clip names repeat across speakers
    aligns = {(p.parent.name, p.stem): p for p in aroot.rglob("*.align")}
    print(f"Found {len(aligns)} .align files")

    vids = sorted(vroot.rglob("*.mpg"))
    if a.speakers:
        vids = [v for v in vids if v.parent.name in set(a.speakers)]
    print(f"Found {len(vids)} .mpg videos")
    if not vids:
        sys.exit("No videos found. Check the --videos path.")

    vout, lout = Path(a.out) / "videos", Path(a.out) / "labels"
    vout.mkdir(parents=True, exist_ok=True)
    lout.mkdir(parents=True, exist_ok=True)

    done = skipped = missing = failed = 0
    for v in vids:
        if a.limit and done >= a.limit:
            break
        name = f"{v.parent.name}_{v.stem}"
        mp4, txt = vout / f"{name}.mp4", lout / f"{name}.txt"
        if mp4.exists() and txt.exists():
            skipped += 1
            continue
        al = aligns.get((v.parent.name, v.stem))
        if al is None:
            missing += 1
            continue
        label = read_align(al)
        if not label:
            missing += 1
            continue
        if not convert_video(v, mp4):
            failed += 1
            print("  could not read", v)
            continue
        txt.write_text(label + "\n", encoding="utf-8")
        done += 1
        if done % 100 == 0:
            print(f"  {done} converted...")

    print(f"\nConverted {done} | already done {skipped} | no alignment {missing} | unreadable {failed}")
    print(f"Videos: {vout.resolve()}\nLabels: {lout.resolve()}")


if __name__ == "__main__":
    main()

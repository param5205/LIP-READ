"""
browser_copy.py - make browser-playable (H.264) copies of videos.

Why: OpenCV writes .mp4 files with the old MPEG-4 Part 2 codec (convert_grid.py, record_clips.py).
Python and the lip-reading model read them fine, but Chrome/Edge/Firefox cannot play them.
This script re-encodes them to H.264, which every browser plays.

Needs:  pip install imageio-ffmpeg        (it brings its own ffmpeg, nothing else to install)

Run:    python browser_copy.py data/videos/s1_bbaf2n.mp4          (one file)
        python browser_copy.py data/videos --limit 20             (first 20 files in a folder)
Output: a new file next to each original, named <name>_web.mp4. Originals are not changed.
Then upload the *_web.mp4 file on the web page.
"""
import argparse
import glob
import os
import subprocess

import imageio_ffmpeg


def convert(src, ffmpeg):
    dst = os.path.splitext(src)[0] + "_web.mp4"
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", src, "-an",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="a video file or a folder of videos")
    ap.add_argument("--limit", type=int, default=0, help="max files when path is a folder")
    args = ap.parse_args()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if os.path.isdir(args.path):
        files = sorted(f for f in glob.glob(os.path.join(args.path, "*.mp4")) if not f.endswith("_web.mp4"))
        if args.limit:
            files = files[:args.limit]
    else:
        files = [args.path]
    for f in files:
        print("->", convert(f, ffmpeg))
    print(f"Done: {len(files)} file(s).")


if __name__ == "__main__":
    main()

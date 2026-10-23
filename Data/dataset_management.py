"""Jiya / Module 1: dataset inventory, transcript cleaning and CSV manifest tools."""
from pathlib import Path
import csv
import re

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mpg", ".mpeg", ".mov", ".mkv"}
TRANSCRIPT_EXTENSIONS = {".align", ".txt"}


def clean_transcript(text):
    """Lowercase, normalize whitespace and remove common silence markers."""
    text = text.lower().strip()
    tokens = re.sub(r"\s+", " ", text).split()
    ignored = {"sil", "sp", "spn", ""}
    tokens = [token for token in tokens if token not in ignored]
    return " ".join(tokens)


def parse_alignment_file(align_path):
    """Read GRID .align lines into dictionaries with start/end/token.

    GRID alignments often store time in 100-nanosecond ticks. If integer timestamps
    are detected, convert ticks to seconds. Decimal timestamps are kept as seconds.
    """
    rows = []
    with Path(align_path).open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            try:
                start_raw, end_raw = parts[0], parts[1]
                if "." in start_raw or "." in end_raw:
                    start, end = float(start_raw), float(end_raw)
                else:
                    start, end = int(start_raw) / 10_000_000, int(end_raw) / 10_000_000
            except ValueError:
                continue
            token = clean_transcript(" ".join(parts[2:]))
            rows.append({"start_seconds": start, "end_seconds": end, "token": token})
    return rows


def _find_transcript_for_video(video):
    """Find a same-stem .align or .txt transcript, if one exists."""
    for ext in (".align", ".txt"):
        candidate = video.with_suffix(ext)
        if candidate.exists():
            return candidate
    return None


def create_dataset_manifest(dataset_root, output_csv="dataset_manifest.csv"):
    """Inventory supported video files and link same-stem transcript files if present."""
    root = Path(dataset_root)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {root}")
    videos = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["video_path", "transcript_path", "transcript_text", "video_bytes", "has_transcript"]
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for video in videos:
            transcript = _find_transcript_for_video(video)
            transcript_text = ""
            if transcript:
                if transcript.suffix.lower() == ".align":
                    transcript_text = " ".join(row["token"] for row in parse_alignment_file(transcript))
                else:
                    transcript_text = clean_transcript(transcript.read_text(encoding="utf-8", errors="replace"))
            writer.writerow({
                "video_path": str(video.resolve()),
                "transcript_path": str(transcript.resolve()) if transcript else "",
                "transcript_text": transcript_text,
                "video_bytes": video.stat().st_size,
                "has_transcript": bool(transcript),
            })
    return {"dataset_root": str(root.resolve()), "video_count": len(videos),
            "videos_with_transcript": sum(1 for v in videos if _find_transcript_for_video(v)),
            "manifest_csv": str(output_csv.resolve())}


def inventory_files(dataset_root, output_csv="dataset_inventory.csv"):
    """Create a safe file inventory report; source dataset files are not modified."""
    root = Path(dataset_root)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {root}")
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in root.rglob("*"):
        if path.is_file():
            rows.append({"relative_path": str(path.relative_to(root)),
                         "extension": path.suffix.lower(),
                         "size_bytes": path.stat().st_size})
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "extension", "size_bytes"])
        writer.writeheader()
        writer.writerows(rows)
    return {"total_files": len(rows), "report_csv": str(output_csv.resolve())}


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description="Manage/inventory GRID-like dataset files.")
    parser.add_argument("dataset_root")
    parser.add_argument("--manifest", default="dataset_manifest.csv")
    parser.add_argument("--inventory", default="dataset_inventory.csv")
    args = parser.parse_args()
    print(json.dumps(create_dataset_manifest(args.dataset_root, args.manifest), indent=2))
    print(json.dumps(inventory_files(args.dataset_root, args.inventory), indent=2))

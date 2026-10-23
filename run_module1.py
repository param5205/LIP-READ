"""Simple command-line launcher for Jiya's Module 1."""
import argparse
import json
from pathlib import Path
from preprocessing import preprocess_and_save
from dataset_management import create_dataset_manifest, inventory_files

def main():
    parser = argparse.ArgumentParser(description="Lip Reading System - Module 1 tools")
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("preprocess", help="Preprocess one video to a .npy sequence")
    prep.add_argument("video")
    prep.add_argument("--output", default="processed/video_frames.npy")
    prep.add_argument("--no-mouth-crop", action="store_true")

    manifest = sub.add_parser("manifest", help="Build dataset manifest CSV")
    manifest.add_argument("dataset_root")
    manifest.add_argument("--output", default="dataset_manifest.csv")

    inv = sub.add_parser("inventory", help="Build full dataset file inventory CSV")
    inv.add_argument("dataset_root")
    inv.add_argument("--output", default="dataset_inventory.csv")

    args = parser.parse_args()
    if args.command == "preprocess":
        result = preprocess_and_save(args.video, args.output, crop_mouth=not args.no_mouth_crop)
    elif args.command == "manifest":
        result = create_dataset_manifest(args.dataset_root, args.output)
    else:
        result = inventory_files(args.dataset_root, args.output)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
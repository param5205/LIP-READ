"""
train.py - train the lip reading model with CTC loss.

Expected data layout (file names must match):
    data/videos/clip001.mp4
    data/labels/clip001.txt      <- plain transcript, e.g. "place blue at f two now"

Run:  python train.py
      python train.py --init lipreader.pt --epochs 10 --max-hours 9     # continue from saved weights
"""
import argparse
import glob
import os
import time

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, random_split

from model import LipReader
from preprocess import DEVICE, IN_CHANNELS, VOCAB, encode, preprocess_video

VIDEO_DIR, LABEL_DIR, CACHE_DIR = "data/videos", "data/labels", "data/cache"
MODEL_PATH = "lipreader.pt"
EPOCHS, BATCH_SIZE, LR = 30, 8, 3e-4
SEED = 42


class LipDataset(Dataset):
    def __init__(self):
        self.videos = sorted(glob.glob(os.path.join(VIDEO_DIR, "*.mp4")))
        os.makedirs(CACHE_DIR, exist_ok=True)

    def __len__(self):
        return len(self.videos)

    def __getitem__(self, i):
        video = self.videos[i]
        name = os.path.splitext(os.path.basename(video))[0]

        # Cache preprocessed tensors: mouth cropping is slow, so do it only once
        cache = os.path.join(CACHE_DIR, name + ".pt")
        if os.path.exists(cache):
            x = torch.load(cache)
        else:
            x = preprocess_video(video).squeeze(0)       # (C, T, H, W)
            torch.save(x, cache)

        with open(os.path.join(LABEL_DIR, name + ".txt"), encoding="utf-8") as f:
            label = f.read().strip()
        return x, torch.tensor(encode(label), dtype=torch.long)


def collate(batch):
    xs, ys = zip(*batch)
    lengths = torch.tensor([len(y) for y in ys], dtype=torch.long)
    return torch.stack(xs), torch.cat(ys), lengths


def get_splits():
    """80/10/10 split with a fixed seed so test.py sees the same test set."""
    ds = LipDataset()
    n = len(ds)
    n_val, n_test = int(0.1 * n), int(0.1 * n)
    gen = torch.Generator().manual_seed(SEED)
    return random_split(ds, [n - n_val - n_test, n_val, n_test], generator=gen)


def run_epoch(model, loader, ctc, optimizer=None):
    training = optimizer is not None
    model.train(training)
    total = 0.0
    with torch.set_grad_enabled(training):
        for x, y, y_len in loader:
            x = x.to(DEVICE)
            log_probs = model(x).log_softmax(-1).permute(1, 0, 2)   # (T, B, C)
            in_len = torch.full((x.size(0),), log_probs.size(0), dtype=torch.long)
            loss = ctc(log_probs, y, in_len, y_len)
            if training:
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                optimizer.step()
            total += loss.item()
    return total / max(len(loader), 1)


def main():
    ap = argparse.ArgumentParser(description="Train the lip reading model")
    ap.add_argument("--init", help="start from these saved weights instead of from scratch")
    ap.add_argument("--epochs", type=int, default=EPOCHS, help=f"number of epochs (default {EPOCHS})")
    ap.add_argument("--max-hours", type=float, default=0,
                    help="stop cleanly after the epoch that passes this many hours (0 = no limit)")
    args = ap.parse_args()

    train_ds, val_ds, _ = get_splits()
    train_dl = DataLoader(train_ds, BATCH_SIZE, shuffle=True, collate_fn=collate)
    val_dl = DataLoader(val_ds, BATCH_SIZE, collate_fn=collate)

    model = LipReader(len(VOCAB) + 1, IN_CHANNELS).to(DEVICE)
    if args.init:
        model.load_state_dict(torch.load(args.init, map_location=DEVICE))
        print(f"Starting from weights in {args.init}")
    ctc = nn.CTCLoss(blank=0, zero_infinity=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    start = time.time()
    best = float("inf")
    for epoch in range(1, args.epochs + 1):
        tr = run_epoch(model, train_dl, ctc, optimizer)
        va = run_epoch(model, val_dl, ctc)
        print(f"Epoch {epoch:02d}/{args.epochs}  train loss {tr:.3f}  val loss {va:.3f}")
        if va < best:
            best = va
            torch.save(model.state_dict(), MODEL_PATH)
            print("  saved best model")
        if args.max_hours and (time.time() - start) / 3600 >= args.max_hours:
            print(f"Stopping after {args.max_hours} hours; best weights are saved in {MODEL_PATH}")
            break


if __name__ == "__main__":
    main()

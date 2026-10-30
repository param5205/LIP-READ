"""
test.py - evaluate the trained model on the held-out test split.
Reports Character Error Rate (CER) and Word Error Rate (WER).

Run:  python test.py
"""
import argparse

import torch

from grid_grammar import snap_to_grid
from model import LipReader
from preprocess import DEVICE, IN_CHANNELS, VOCAB, decode
from train import MODEL_PATH, get_splits


def edit_distance(a, b):
    """Levenshtein distance between two sequences."""
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def ids_to_text(ids):
    return "".join(VOCAB[i - 1] for i in ids)


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--own-holdout", type=float, default=0.0,
                    help="test only on the held-out part of your me_* clips (same value as in train.py)")
    _, _, test_ds = get_splits(ap.parse_args().own_holdout)

    model = LipReader(len(VOCAB) + 1, IN_CHANNELS).to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()

    char_err = char_total = word_err = word_total = 0
    s_char_err = s_word_err = 0
    for k in range(len(test_ds)):
        x, y = test_ds[k]
        pred = decode(model(x.unsqueeze(0).to(DEVICE)))
        truth = ids_to_text(y.tolist())

        char_err += edit_distance(pred, truth)
        char_total += len(truth)
        word_err += edit_distance(pred.split(), truth.split())
        word_total += len(truth.split())

        snapped = snap_to_grid(pred)[0]
        s_char_err += edit_distance(snapped, truth)
        s_word_err += edit_distance(snapped.split(), truth.split())

        if k < 5:
            print(f"truth: {truth}\npred : {pred}\n")

    print(f"Test samples: {len(test_ds)}")
    print(f"CER: {char_err / max(char_total, 1):.2%}")
    print(f"WER: {word_err / max(word_total, 1):.2%}")
    print(f"With GRID grammar clean-up -> CER: {s_char_err / max(char_total, 1):.2%}  "
          f"WER: {s_word_err / max(word_total, 1):.2%}")


if __name__ == "__main__":
    main()

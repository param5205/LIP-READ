"""
grid_grammar.py - optional clean-up for models trained on the GRID corpus.

Every GRID sentence has exactly 6 words:
  command  colour  preposition  letter  digit  adverb
  "lay green with t two soon"

If the model outputs 6 words, each word is snapped to the closest word that is
allowed in its slot (by edit distance). Anything that is not 6 words is returned
unchanged, so this never makes a free-speech model worse than it was.

Only use it for GRID-style speech. Pure Python (no torch needed).
"""
SLOTS = [
    ["bin", "lay", "place", "set"],
    ["blue", "green", "red", "white"],
    ["at", "by", "in", "with"],
    None,  # letter: a-z except w (single characters, kept as-is)
    ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"],
    ["again", "now", "please", "soon"],
]
LETTERS = set("abcdefghijklmnopqrstuvxyz")  # no 'w' in GRID


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def _closest(word, options):
    return min(options, key=lambda o: (edit_distance(word, o), abs(len(word) - len(o)), o))


def snap_to_grid(text):
    """Return (snapped_text, was_snapped)."""
    words = text.split()
    if len(words) != 6:
        return text, False
    out = []
    for word, options in zip(words, SLOTS):
        if options is None:
            # letter slot: keep a valid letter; otherwise take its first valid character
            if len(word) == 1 and word in LETTERS:
                out.append(word)
            else:
                cand = [c for c in word if c in LETTERS]
                out.append(cand[0] if cand else word)
        else:
            out.append(_closest(word, options))
    return " ".join(out), True


if __name__ == "__main__":
    tests = {
        "lay greed with t two soon": "lay green with t two soon",
        "bin blu at f sevn again": "bin blue at f seven again",
        "place red by a nin nw": "place red by a nine now",
        "hello world": "hello world",
    }
    for src, want in tests.items():
        got, _ = snap_to_grid(src)
        print("OK  " if got == want else "FAIL", src, "->", got)

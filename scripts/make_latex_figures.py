"""Copy the figures used by the LaTeX report into report/latex/figures/, removing the title text printed at the top of
each image (the LaTeX captions number and describe the figures instead). The plots themselves are unchanged: they are
made by scripts/make_figures.py and scripts/plot_calibration.py from the result files.

Usage: python scripts/make_latex_figures.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "latex" / "figures"

# source image -> number of title text lines printed above the plot
FIGURES = {
    "results/figures/fig1_learning_curves.png": 2,
    "results/figures/fig2_exp1_rescue.png": 1,
    "results/figures/fig3_exp2_cooperation.png": 1,
    "results/figures/fig4_attribution.png": 1,
    "results/calibration/figures/fig_cal_main.png": 3,
}


def text_bands(img: np.ndarray) -> list[tuple[int, int]]:
    """(first, last + 1) row of each horizontal band that contains dark pixels."""
    ink = (img.min(axis=2) < 200).any(axis=1)
    bands, i = [], 0
    while i < len(ink):
        if ink[i]:
            j = i
            while j < len(ink) and ink[j]:
                j += 1
            bands.append((i, j))
            i = j
        else:
            i += 1
    return bands


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for src, n_lines in FIGURES.items():
        im = Image.open(ROOT / src).convert("RGB")
        top = text_bands(np.asarray(im).astype(int))[n_lines - 1][1]   # bottom of the last title line
        im.crop((0, top + 4, im.width, im.height)).save(OUT / Path(src).name)
        print(f"{src} -> {OUT.relative_to(ROOT) / Path(src).name} (cut {top + 4} px of title)")


if __name__ == "__main__":
    main()

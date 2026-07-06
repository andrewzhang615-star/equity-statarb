"""Shared matplotlib style for report figures.

A clean, serif, academic look closer to the Computer Modern memo: serif fonts,
CM math, smaller labels, no top/right spines. Call ``apply_style()`` after
importing pyplot in any figure script.
"""
from __future__ import annotations

import matplotlib as mpl

COLORS = {
    "primary": "#111111",
    "secondary": "#5f5f5f",
    "muted": "#8a8a8a",
    "accent": "#b22222",
    "accent2": "#2f5d8c",
}


def apply_style() -> None:
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["CMU Serif", "Latin Modern Roman", "DejaVu Serif", "Times New Roman"],
        "mathtext.fontset": "cm",
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "legend.frameon": False,
        "legend.handlelength": 2.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "lines.linewidth": 1.4,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    })

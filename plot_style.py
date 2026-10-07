"""Shared figure style for the follow-up figures.

The module copies the style of the authors' main figures. The follow-up figures
then have the same font, the same font sizes and the same colors as the paper.

Source: github.com/giordano-demarzo/moltbook-api-crawler
  - `COLORS`, `COLOR_SEQUENCE`, `setup_style`, `add_panel_label`, `format_axis_log`
    -> repo/analysis_scripts/figure_style.py

Additions:
  - `setup_style` pins the font to DejaVu Sans. The font list of the authors starts
    with Arial, but their published figure PDFs embed DejaVu Sans. A machine with
    Arial gives a different font without the pin.
  - `FIG_WIDTH`: the main figures 1, 3, 4 and 5 are 10 in wide. The paper includes
    each figure at the text width, so a figure of the same width prints its text
    at the same size as the main figures.
  - `QUANTITY_COLORS`: one color for each quantity in all follow-up figures.
  - `plain_log_ticks`: plain numbers on a log axis that spans less than one decade.
"""
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


# ----- verbatim from repo/analysis_scripts/figure_style.py (font list pinned) -----
# Nature-friendly color palette (colorblind-safe)
COLORS = {
    'blue': '#0077BB',
    'orange': '#EE7733',
    'green': '#009988',
    'red': '#CC3311',
    'purple': '#AA3377',
    'cyan': '#33BBEE',
    'grey': '#BBBBBB',
    'black': '#000000',
}

# Sequential colors for multiple series
COLOR_SEQUENCE = [
    '#0077BB',  # blue
    '#EE7733',  # orange
    '#009988',  # green
    '#CC3311',  # red
    '#AA3377',  # purple
    '#33BBEE',  # cyan
]


def setup_style():
    """Configure matplotlib for publication-quality figures."""
    plt.rcParams.update({
        # Font settings
        'font.family': 'sans-serif',
        'font.sans-serif': ['DejaVu Sans'],  # the font of the published figures
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'legend.fontsize': 9,

        # Line and marker settings
        'lines.linewidth': 1.5,
        'lines.markersize': 5,

        # Axes settings
        'axes.linewidth': 1.0,
        'axes.spines.top': False,
        'axes.spines.right': False,

        # Grid settings
        'axes.grid': False,
        'grid.alpha': 0.3,
        'grid.linewidth': 0.5,

        # Legend settings
        'legend.frameon': True,
        'legend.framealpha': 0.9,
        'legend.edgecolor': 'none',

        # Figure settings
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.1,
    })


def add_panel_label(ax, label, x=-0.12, y=1.08):
    """Add panel label (a, b, c, etc.) to subplot."""
    ax.text(x, y, label, transform=ax.transAxes, fontsize=14,
            fontweight='bold', va='top', ha='left')


def format_axis_log(ax, which='both'):
    """Format log-scale axes with minor ticks."""
    if which in ['x', 'both']:
        ax.set_xscale('log')
    if which in ['y', 'both']:
        ax.set_yscale('log')
    ax.grid(True, which='major', alpha=0.3, linewidth=0.5)
    ax.grid(True, which='minor', alpha=0.15, linewidth=0.3)


# ----- additions for the follow-up figures -----
FIG_WIDTH = 10.0  # inches, the width of the main figures 1, 3, 4 and 5

# Upvotes and direct replies keep their colors from Figure 3 of the paper.
QUANTITY_COLORS = {
    'upvotes': COLORS['blue'],
    'direct_replies': COLORS['green'],
    'comments': COLORS['orange'],
    'downvotes': COLORS['red'],
}


def plain_log_ticks(ax, axis='y'):
    """Label a narrow log axis with plain numbers (2, 3, 4) in place of 2x10^0.

    Call the function after the plot commands, when the axis limits are known.
    An axis that spans one decade or more keeps the default labels.
    """
    lo, hi = ax.get_ylim() if axis == 'y' else ax.get_xlim()
    if lo <= 0 or hi / lo >= 10:
        return
    plain = FuncFormatter(lambda v, _: f'{v:g}')
    target = ax.yaxis if axis == 'y' else ax.xaxis
    target.set_major_formatter(plain)
    target.set_minor_formatter(plain)

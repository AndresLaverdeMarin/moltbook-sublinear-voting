"""
H1b - downvote-only analysis (within-Moltbook; no human baseline exists).

H1 showed that upvote, net (up-down) and total (up+down) betas are all sublinear
(~0.75) and that downvotes are only 1.24% of all votes, yet downvotes alone scale
~linearly (beta ~ 1.03). Reddit fuzzes votes and never exposes separate downvote
counts, so there is no human downvote baseline to compare against -- but we can
still characterize downvoting *within* Moltbook. Four questions:

  1. Prevalence    - how often are posts downvoted at all? distribution / concentration.
  2. Scaling       - beta(downvotes vs size), with robustness for the sparsity:
                     keep-zeros (paper), drop-zeros, and a probability/intensity split.
  3. Contention    - does the downvote SHARE d/(u+d) rise with discussion size?
  4. Comment-level - are comments ever downvoted? (the data fact behind H4).

Feb-8 cutoff, authors' exact spam filter, size = comment_count. beta via paper_beta.
"""
import os
import sqlite3
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from paper_beta import fit_beta, bin_and_average, fit_power_law

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("MOLTBOOK_DB", os.path.join(HERE, "..", "moltbook_upload.db"))
FIGDIR = os.environ.get("MOLTBOOK_FIGDIR", os.path.join(HERE, "figures"))
START  = os.environ.get("MOLTBOOK_START", "1970-01-01")    # inclusive lower bound on created_at
CUTOFF = os.environ.get("MOLTBOOK_CUTOFF", "2026-02-09")   # exclusive upper bound (default: through Feb 8)

# Figure styling mirrored from repo/analysis_scripts/figure_style.py (Fig 3a look)
COLORS = {"blue": "#0077BB", "orange": "#EE7733", "green": "#009988",
          "red": "#CC3311", "grey": "#BBBBBB"}


def _style():
    plt.rcParams.update({"font.size": 10, "axes.labelsize": 11, "axes.titlesize": 12,
                         "legend.fontsize": 8, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.dpi": 300})


def _log_axes(ax):
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.grid(True, which="major", alpha=0.3, linewidth=0.5)
    ax.grid(True, which="minor", alpha=0.15, linewidth=0.3)


def _panel(ax, label):
    ax.text(-0.12, 1.08, label, transform=ax.transAxes, fontsize=14,
            fontweight="bold", va="top", ha="left")


def _fitline(ax, x, y, color, x_min=2):
    """Plot the repo-style dashed power-law fit over bins >= x_min; return exponent."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = (x >= x_min) & (y > 0)
    if m.sum() < 3:
        return None
    exp, pref = fit_power_law(x[m], y[m], x_min=x_min)
    xf = np.logspace(np.log10(x[m].min()), np.log10(x[m].max()), 50)
    ax.plot(xf, pref * xf ** exp, "--", color=color, linewidth=2, label="_nolegend_")
    return exp


def spam_post_ids(con):
    """Authors' two spam criteria (see h1_net_score.py)."""
    df = pd.read_sql_query("SELECT post_id, content, author_id FROM comments", con)
    g = df.groupby("post_id")
    s = g.agg(n=("content", "size"), uc=("content", "nunique"), ua=("author_id", "nunique"))
    s = s[s["n"] >= 5]
    flagged = set(s[((s["uc"] / s["n"]) < 0.5) | ((s["ua"] / s["n"]) < 0.2)].index)
    high_count = con.execute(
        "SELECT p.id FROM posts p "
        "LEFT JOIN (SELECT DISTINCT post_id FROM comments) c ON p.id = c.post_id "
        "WHERE c.post_id IS NULL AND p.comment_count > 200").fetchall()
    flagged.update(r[0] for r in high_count)
    return flagged


def beta_dropzero(size, value):
    m = value > 0
    return fit_beta(size[m], value[m])


def binned_fraction(size, hit, nbins=20):
    """Mean of a 0/1 indicator (here: has >=1 downvote) per log-size bin; fit slope."""
    m = size > 0
    s, h = size[m], hit[m].astype(float)
    edges = np.logspace(np.log10(s.min()), np.log10(s.max()), nbins)
    cen, frac = [], []
    for i in range(len(edges) - 1):
        sel = (s >= edges[i]) & (s < edges[i + 1])
        if sel.sum() >= 5:
            cen.append(np.sqrt(edges[i] * edges[i + 1]))
            frac.append(h[sel].mean())
    return np.array(cen), np.array(frac)


def make_figure(size, up, dn, has_dn):
    """Three panels in the Figure-3a style: (a) up- vs downvote scaling,
    (b) probability of being downvoted, (c) downvote intensity (zeros dropped).
    Panels (b)x(c) decompose the keep-zeros downvote slope shown in (a)."""
    _style()
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.3))

    # (a) average upvotes (with 10-90% band) and average downvotes vs size
    xu, yu, ulo, uhi = bin_and_average(size, up)
    xd, yd, _, _ = bin_and_average(size, dn)
    eu = _fitline(ax[0], xu, yu, COLORS["orange"])
    ax[0].errorbar(xu, yu, yerr=[np.clip(yu - ulo, 0, None), np.clip(uhi - yu, 0, None)],
                   fmt="o", color=COLORS["orange"], markersize=5, capsize=2, alpha=.85,
                   label=f"upvotes  (β = {eu:.2f})")
    ed = _fitline(ax[0], xd, yd, COLORS["blue"])
    ax[0].plot(xd, yd, "s", color=COLORS["blue"], markersize=5, alpha=.85,
               label=f"downvotes  (β = {ed:.2f})")
    ax[0].set(xlabel="Discussion tree size (comments)", ylabel="Average votes per post",
              title="(a) upvotes vs downvotes scaling")
    _log_axes(ax[0]); _panel(ax[0], "a"); ax[0].legend(loc="upper left")

    # (b) probability of receiving >=1 downvote vs size
    cen_p, frac_p = binned_fraction(size, has_dn)
    ep = _fitline(ax[1], cen_p, frac_p, COLORS["red"])
    ax[1].plot(cen_p, frac_p, "o", color=COLORS["red"], markersize=5, alpha=.85,
               label=f"P(downvote > 0)  (slope {ep:+.2f})")
    ax[1].set(xlabel="Discussion tree size (comments)",
              ylabel="P(post has ≥1 downvote)", title="(b) probability of being downvoted")
    _log_axes(ax[1]); _panel(ax[1], "b"); ax[1].legend(loc="upper left")

    # (c) downvote intensity among downvoted posts only (zeros dropped)
    xi, yi, ilo, ihi = bin_and_average(size[has_dn], dn[has_dn])
    ei = _fitline(ax[2], xi, yi, COLORS["green"])
    ax[2].errorbar(xi, yi, yerr=[np.clip(yi - ilo, 0, None), np.clip(ihi - yi, 0, None)],
                   fmt="o", color=COLORS["green"], markersize=5, capsize=2, alpha=.85,
                   label=f"downvoted posts  (β = {ei:.2f})")
    ax[2].set(xlabel="Discussion tree size (comments)",
              ylabel="Average downvotes (downvoted only)",
              title="(c) downvote intensity, zeros dropped")
    _log_axes(ax[2]); _panel(ax[2], "c"); ax[2].legend(loc="upper left")

    fig.tight_layout()
    os.makedirs(FIGDIR, exist_ok=True)
    out = os.path.join(FIGDIR, "h1b_downvotes.pdf")
    fig.savefig(out, bbox_inches="tight")
    print(f"\nFigure saved: {out}  (a = b x c: keep-zeros slope ~ P-slope + intensity-beta)")


def main():
    con = sqlite3.connect(DB)
    print("Loading posts...")
    posts = pd.read_sql_query(
        f"SELECT id, upvotes, downvotes, comment_count FROM posts "
        f"WHERE created_at >= '{START}' AND created_at < '{CUTOFF}'", con)
    print(f"  posts (<= Feb 8): {len(posts):,}")

    print("Computing spam filter (reads all comments)...")
    spam = spam_post_ids(con)
    posts = posts[~posts["id"].isin(spam)].copy()
    print(f"  posts after spam filter: {len(posts):,}")

    # comment-level downvotes (the H4 data fact)
    cstats = con.execute(
        "SELECT COUNT(*), SUM(downvotes), MAX(downvotes) FROM comments").fetchone()
    con.close()

    size = posts["comment_count"].to_numpy(float)
    up = posts["upvotes"].to_numpy(float)
    dn = np.clip(posts["downvotes"].to_numpy(float), 0, None)

    # restrict to real discussions (size>0) for scaling, consistent with H1/H2
    keep = size > 0
    size, up, dn = size[keep], up[keep], dn[keep]
    print(f"  posts with size>0: {len(size):,}\n")

    # ---- 1. prevalence & concentration ----
    has_dn = dn > 0
    print("=== 1. downvote prevalence & concentration ===")
    print(f"  posts with >=1 downvote : {has_dn.sum():,} ({has_dn.mean():.2%})")
    print(f"  downvotes per post      : mean={dn.mean():.3f}  median={np.median(dn):.0f}  max={dn.max():.0f}")
    print(f"  total downvotes         : {dn.sum():,.0f}  (upvotes {up.sum():,.0f}; "
          f"downvote share {dn.sum()/(up.sum()+dn.sum()):.2%})")
    order = np.sort(dn)[::-1]
    top1 = order[:max(1, len(order)//100)].sum()
    print(f"  concentration           : top 1% of posts hold {top1/dn.sum():.1%} of all downvotes\n")

    # ---- 2. scaling, with robustness ----
    print("=== 2. downvotes-vs-size scaling (vs sublinear upvotes ~0.755) ===")
    b_dn, n_dn = fit_beta(size, dn)
    b_up, _ = fit_beta(size, up)
    b_dz, n_dz = beta_dropzero(size, dn)
    print(f"  beta(downvotes), keep-zeros (paper) : {b_dn:.3f}  [{n_dn} bins]")
    print(f"  beta(downvotes), drop-zeros         : {b_dz:.3f}  [{n_dz} bins, "
          f"n={has_dn.sum():,} downvoted posts]")
    print(f"  beta(upvotes) for reference         : {b_up:.3f}")
    # decompose keep-zeros slope into probability x intensity
    cen_p, frac_p = binned_fraction(size, has_dn)
    e_p = None
    if (frac_p > 0).sum() >= 3:
        e_p, _ = fit_power_law(cen_p[frac_p > 0], frac_p[frac_p > 0], x_min=2)
        print(f"  -> P(downvote>0) vs size, log-log slope: {e_p:+.3f}  "
              f"(probability of being downvoted rises with size)")
    print()

    # ---- 2b. the SAME decomposition for UPVOTES (the authors' exact metric) ----
    # The authors fit upvotes with WHERE upvotes IS NOT NULL AND comment_count>0
    # (no upvotes>0 filter) -> keep-zeros binned mean, identical to what we do for
    # downvotes. So beta_up and beta_down are the SAME estimator; only sparsity differs.
    print("=== 2b. identical estimator applied to upvotes (authors' metric) ===")
    has_up = up > 0
    b_up_dz, _ = beta_dropzero(size, up)
    cen_u, frac_u = binned_fraction(size, has_up)
    mu = frac_u > 0
    e_u = fit_power_law(cen_u[mu], frac_u[mu], x_min=2)[0] if mu.sum() >= 3 else float("nan")
    print(f"  {'metric':9s} {'%nonzero':>9} {'keep-0 beta':>12} {'P(>0) slope':>12} {'intensity beta':>15}")
    print(f"  {'upvotes':9s} {has_up.mean():>8.0%} {b_up:>12.3f} {e_u:>+12.3f} {b_up_dz:>15.3f}")
    print(f"  {'downvotes':9s} {has_dn.mean():>8.1%} {b_dn:>12.3f} {e_p:>+12.3f} {b_dz:>15.3f}")
    print(f"  -> SAME method (keep-zeros mean). Upvotes are ~{has_up.mean():.0%} nonzero, so the\n"
          f"     keep-zeros beta tracks the magnitude (intensity) and stays sublinear. Downvotes\n"
          f"     are {has_dn.mean():.0%} nonzero -> frequency-dominated: keep-zeros beta ~ P-slope +\n"
          f"     intensity beta, which is why downvotes look ~linear despite sublinear magnitude.\n")

    # ---- 3. contention: does downvote share rise with size? ----
    print("=== 3. downvote share d/(u+d) vs discussion size (contention) ===")
    voted = (up + dn) > 0
    share = dn[voted] / (up[voted] + dn[voted])
    sz = size[voted]
    rho, _ = stats.spearmanr(sz, share)
    print(f"  mean downvote share     : {share.mean():.2%}")
    print(f"  Spearman(size, share)   : rho = {rho:+.3f}")
    cen_s, mean_s = binned_fraction(sz, share)  # reuse: mean of share per size bin
    qs = np.quantile(sz, [.1, .9])
    lo = share[sz <= qs[0]].mean(); hi = share[sz >= qs[1]].mean()
    print(f"  share in small (Q10 size<= {qs[0]:.0f}) : {lo:.2%}")
    print(f"  share in large (Q90 size>= {qs[1]:.0f}) : {hi:.2%}")
    print(f"  (if share rises with size, big discussions are mildly more contentious)\n")

    # ---- 4. comment-level downvotes ----
    print("=== 4. comment-level downvotes (data fact) ===")
    ncom, sumdn, maxdn = cstats
    print(f"  comments: {ncom:,}  total comment downvotes: {sumdn or 0:,}  "
          f"max on any comment: {maxdn or 0:,}")
    print(f"  -> downvoting on Moltbook is a POST-level signal only "
          f"({'no' if not sumdn else 'some'} comment downvotes).")

    make_figure(size, up, dn, has_dn)


if __name__ == "__main__":
    main()

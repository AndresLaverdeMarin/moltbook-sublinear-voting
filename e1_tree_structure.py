"""
E1 - Tree-structure tail upturn & crawl-window sensitivity (paper Figure 4a).

Figure 4a (repo/analysis_scripts/figure4_structure.py) plots normalized depth
(d/sqrt(n)) vs normalized width (w/sqrt(n)) for posts with <100 API comments
(complete trees), log-binned trend + power-law fit. The curve turns UP at the
high-width tail instead of following the single power law. IDEA.md E1 asks why,
and how sensitive the metrics are to the analysis time window. Candidate causes:

  1. Tree incompleteness near the 100-comment cap (partial trees bias depth/width).
  2. Right-censoring of young posts (trees measured mid-growth) -- structural H3.
  3. Small-n / heavy-skew tail bins (a few mega-threads pull the mean up).
  4. Genuine regime change (accept only after ruling out 1-3).

Metric definitions match the original exactly: per post with <100 API comments,
>=5 stored comments, non-spam: n = stored comments, d = max tree depth (1 = direct
reply to post), w = max comments at any single depth level. The stored `depth`
column is 0-indexed (0 = direct reply), so d = max(depth)+1; width is per-level
counts (offset-invariant) -- letting us vectorize instead of chain-walking 2.1M rows.

Tests / panels:
  (a) reproduce Fig 4a: trend + power-law fit, per-bin counts, mean vs median.
  (b) crawl-window sensitivity: trends for created_at < Feb4 / Feb6 / Feb8 / full.
  (c) maturity: all vs mature (age@crawl >=72h) vs young (<24h) via post_snapshots.
  (d) cap-proximity: trends by comment_count band (near the 100 cap vs far).
"""
import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "moltbook_upload.db")
FIGDIR = os.path.join(HERE, "figures")
MIN_STORED = 5
NBINS = 15


def spam_post_ids(con):
    df = pd.read_sql_query("SELECT post_id, content, author_id FROM comments", con)
    g = df.groupby("post_id")
    s = g.agg(n=("content", "size"), uc=("content", "nunique"),
              ua=("author_id", "nunique"))
    s = s[s["n"] >= 5]
    flagged = set(s[((s["uc"] / s["n"]) < 0.5) | ((s["ua"] / s["n"]) < 0.2)].index)
    high_count = con.execute(
        "SELECT p.id FROM posts p "
        "LEFT JOIN (SELECT DISTINCT post_id FROM comments) c ON p.id = c.post_id "
        "WHERE c.post_id IS NULL AND p.comment_count > 200").fetchall()
    flagged.update(r[0] for r in high_count)
    return flagged


def trend(nw, nd, nbins=NBINS, stat="mean"):
    """Log-bin by norm-width, aggregate norm-depth. Returns centers, y, counts."""
    m = (nw > 0) & (nd > 0)
    nw, nd = nw[m], nd[m]
    if nw.size < 10:
        return np.array([]), np.array([]), np.array([])
    edges = np.logspace(np.log10(nw.min()), np.log10(nw.max()), nbins)
    cen, ys, cnt = [], [], []
    for i in range(len(edges) - 1):
        sel = (nw >= edges[i]) & (nw < edges[i + 1])
        if sel.sum() >= 5:
            cen.append(np.sqrt(edges[i] * edges[i + 1]))
            ys.append(np.median(nd[sel]) if stat == "median" else np.mean(nd[sel]))
            cnt.append(int(sel.sum()))
    return np.array(cen), np.array(ys), np.array(cnt)


def fit_exp(x, y):
    """Power-law exponent via log-log OLS on binned points (as original)."""
    if len(x) < 3:
        return np.nan, np.nan
    e, b = np.polyfit(np.log10(x), np.log10(y), 1)
    return e, 10 ** b


def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA temp_store=MEMORY")

    print("Loading <100-comment posts...")
    posts = pd.read_sql_query(
        "SELECT id, comment_count, created_at FROM posts "
        "WHERE comment_count > 0 AND comment_count < 100", con)
    print(f"  posts (<100 API comments): {len(posts):,}")

    print("Computing spam filter...")
    spam = spam_post_ids(con)

    con.execute("CREATE TEMP TABLE subset(pid TEXT PRIMARY KEY)")
    con.executemany("INSERT INTO subset VALUES (?)", [(i,) for i in posts["id"]])

    print("Loading comment (post_id, depth) and computing tree metrics...")
    cm = pd.read_sql_query(
        "SELECT c.post_id, c.depth FROM comments c JOIN subset s ON c.post_id=s.pid",
        con)
    g = cm.groupby("post_id")
    n = g.size().rename("n")
    dmax = g["depth"].max().rename("dmax")
    width = cm.groupby(["post_id", "depth"]).size().groupby(level=0).max().rename("w")
    met = pd.concat([n, dmax, width], axis=1)

    # snapshot age at crawl (last recorded - created)
    print("Loading snapshot coverage for maturity...")
    sl = pd.read_sql_query(
        "SELECT s.post_id, MAX(s.recorded_at) last_rec FROM post_snapshots s "
        "JOIN subset s2 ON s.post_id=s2.pid GROUP BY s.post_id", con)
    con.close()

    df = posts.merge(met, left_on="id", right_index=True, how="inner")
    df = df[(df["n"] >= MIN_STORED) & (~df["id"].isin(spam))].copy()
    df["d"] = df["dmax"] + 1                       # 1 = direct reply (match original)
    df["nd"] = df["d"] / np.sqrt(df["n"])
    df["nw"] = df["w"] / np.sqrt(df["n"])
    df = df.merge(sl, left_on="id", right_on="post_id", how="left")
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df["last_rec"] = pd.to_datetime(df["last_rec"], utc=True)
    df["age_h"] = (df["last_rec"] - df["created_at"]).dt.total_seconds() / 3600
    print(f"  posts with tree metrics (n>=5, non-spam): {len(df):,}\n")

    nw = df["nw"].to_numpy(); nd = df["nd"].to_numpy()

    # ---- (a) reproduce Fig 4a, mean vs median, per-bin counts ----
    cen, ym, cnt = trend(nw, nd, stat="mean")
    _, ymed, _ = trend(nw, nd, stat="median")
    e_all, p_all = fit_exp(cen, ym)
    # upturn = mean of last-3-bin residuals above the power-law fit
    fit_y = p_all * cen ** e_all
    resid = np.log10(ym) - np.log10(fit_y)
    print("=== (a) reproduced Figure 4a ===")
    print(f"  posts: {len(df):,}   power-law exponent (mean trend): {e_all:.3f}")
    print(f"  per-bin (norm_width center | mean nd | median nd | count | resid):")
    for c, m_, md, k, r in zip(cen, ym, ymed, cnt, resid):
        tail = "  <-- tail" if r > 0.02 and c > np.median(cen) else ""
        print(f"    {c:7.3f} | {m_:6.3f} | {md:6.3f} | {k:6,} | {r:+.3f}{tail}")
    print(f"  last-3-bin mean residual above fit: mean={resid[-3:].mean():+.3f} "
          f"median-trend={ (np.log10(ymed[-3:])-np.log10(p_all*cen[-3:]**e_all)).mean():+.3f}")
    print(f"  -> if median-trend upturn << mean upturn, it's a small-n/skew artifact\n")

    # ---- (b) crawl-window sensitivity ----
    print("=== (b) crawl-window sensitivity (created_at <) ===")
    windows = {"<Feb04": "2026-02-04", "<Feb06": "2026-02-06",
               "<Feb08": "2026-02-08", "full": "2026-02-10"}
    win_curves = {}
    for name, cut in windows.items():
        sub = df[df["created_at"] < pd.Timestamp(cut, tz="UTC")]
        c, y, k = trend(sub["nw"].to_numpy(), sub["nd"].to_numpy())
        e, _ = fit_exp(c, y)
        win_curves[name] = (c, y, k)
        print(f"  {name:7s}: n={len(sub):>7,}  exponent={e:+.3f}  bins={len(c)}")
    print()

    # ---- (c) maturity (right-censoring test) ----
    print("=== (c) maturity: does the upturn survive on mature posts? ===")
    has_age = df["age_h"].notna()
    groups_c = {
        "all": df[has_age],
        "young <24h": df[has_age & (df["age_h"] < 24)],
        "mature >=72h": df[has_age & (df["age_h"] >= 72)],
    }
    mat_curves = {}
    for name, sub in groups_c.items():
        c, y, k = trend(sub["nw"].to_numpy(), sub["nd"].to_numpy())
        e, p = fit_exp(c, y)
        up = (np.log10(y[-3:]) - np.log10(p * c[-3:] ** e)).mean() if len(c) >= 6 else np.nan
        mat_curves[name] = (c, y)
        print(f"  {name:13s}: n={len(sub):>7,}  exponent={e:+.3f}  tail-upturn={up:+.3f}")
    print("  -> if tail-upturn shrinks from young to mature, it was right-censoring\n")

    # ---- (d) cap-proximity (incompleteness test) ----
    print("=== (d) cap-proximity: upturn by comment_count band ===")
    bands = [(5, 25), (25, 50), (50, 75), (75, 100)]
    cap_curves = {}
    for lo, hi in bands:
        sub = df[(df["comment_count"] >= lo) & (df["comment_count"] < hi)]
        c, y, k = trend(sub["nw"].to_numpy(), sub["nd"].to_numpy())
        e, _ = fit_exp(c, y) if len(c) >= 3 else (np.nan, np.nan)
        cap_curves[f"{lo}-{hi}"] = (c, y)
        print(f"  comment_count {lo:>2}-{hi:<3}: n={len(sub):>7,}  exponent={e:+.3f}  "
              f"max norm_width={sub['nw'].max():.2f}")
    print("  -> if the high-norm_width tail is populated only by near-cap posts,\n"
          "     the upturn is tree-incompleteness near the 100-comment limit\n")

    # ---- figure (2x2) ----
    fig, ax = plt.subplots(2, 2, figsize=(12, 9))
    # (a)
    a = ax[0, 0]
    a.loglog(cen, ym, "o-", color="#1f77b4", label="mean d/√n")
    a.loglog(cen, ymed, "s--", color="#9467bd", label="median d/√n")
    xf = np.logspace(np.log10(cen.min()), np.log10(cen.max()), 50)
    a.loglog(xf, p_all * xf ** e_all, ":", color="grey", label=f"fit ^{e_all:.2f}")
    for c, y, k in zip(cen, ym, cnt):
        a.annotate(str(k), (c, y), fontsize=6, ha="center", va="bottom")
    a.set(xlabel="norm width w/√n", ylabel="norm depth d/√n",
          title="(a) Fig 4a reproduced (bin counts annotated)")
    a.legend(fontsize=8); a.grid(alpha=.3, which="both")
    # (b)
    b = ax[0, 1]
    for name, (c, y, k) in win_curves.items():
        b.loglog(c, y, "o-", label=name, alpha=.8)
    b.set(xlabel="norm width w/√n", ylabel="norm depth d/√n",
          title="(b) crawl-window sensitivity"); b.legend(fontsize=8); b.grid(alpha=.3, which="both")
    # (c)
    cc = ax[1, 0]
    for name, (c, y) in mat_curves.items():
        cc.loglog(c, y, "o-", label=name, alpha=.8)
    cc.set(xlabel="norm width w/√n", ylabel="norm depth d/√n",
           title="(c) maturity (right-censoring)"); cc.legend(fontsize=8); cc.grid(alpha=.3, which="both")
    # (d)
    dd = ax[1, 1]
    for name, (c, y) in cap_curves.items():
        if len(c):
            dd.loglog(c, y, "o-", label=f"cc {name}", alpha=.8)
    dd.set(xlabel="norm width w/√n", ylabel="norm depth d/√n",
           title="(d) cap-proximity (incompleteness)"); dd.legend(fontsize=8); dd.grid(alpha=.3, which="both")
    fig.tight_layout()
    os.makedirs(FIGDIR, exist_ok=True)
    out = os.path.join(FIGDIR, "e1_tree_structure.pdf")
    fig.savefig(out, bbox_inches="tight")
    print(f"Figure saved: {out}")


if __name__ == "__main__":
    main()

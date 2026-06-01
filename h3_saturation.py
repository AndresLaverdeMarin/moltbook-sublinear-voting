"""
H3 (saturation story) test for the Moltbook upvote-scaling follow-up.

Hypothesis: upvotes accumulate early and plateau while comments keep accruing,
mechanically producing the sublinear upvotes-vs-size exponent (beta ~ 0.70).
Mechanism for the voting-vs-replying decoupling: votes have an early time window,
replies keep coming. At crawl time, large (older/more active) discussions have
upvotes that already saturated but comments that kept growing -> U grows
sublinearly in C.

Data: post_snapshots (8.4M rows, ~27 snapshots/post at ~4.8h cadence, recorded
Feb 3-9). 62.8% of posts are born inside the snapshot window and caught near
birth (median age 2.5h). We build a cohort caught early and followed >=72h,
interpolate each post's upvote and comment curves onto a common age grid,
normalize by each post's value at the 72h horizon, and test four predictions:

  1. Accumulation curves - mean fraction-of-final(72h) vs age. H3: upvotes reach
     their plateau earlier than comments.
  2. Saturation timing    - per-post age to reach 90% of final. H3: t90(up) << t90(com).
  3. Late-life increments - share of growth in the 24->72h window. H3: comments
     still climbing, upvotes done.
  4. Beta at matched age  - cross-sectional fit_beta(upvotes vs comment_count) at
     each fixed age. H3: beta drifts down toward ~0.70 as upvotes saturate.

Mirrors h1_net_score.py: paper spam filter, created_at <= 2026-02-08, fit_beta via
log-binned log-log OLS.
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
CUTOFF = "2026-02-09"            # exclusive -> through Feb 8
FIRST_AGE_MAX = 6.0             # caught within 6h of birth
HORIZON = 72.0                 # reference "final" age (3 days)
GRID = np.array([2, 4, 6, 9, 12, 18, 24, 36, 48, 60, 72], float)


def spam_post_ids(con):
    df = pd.read_sql_query("SELECT post_id, content, author_id FROM comments", con)
    g = df.groupby("post_id")
    s = g.agg(n=("content", "size"), uc=("content", "nunique"),
              ua=("author_id", "nunique"))
    s = s[s["n"] >= 5]
    return set(s[((s["uc"] / s["n"]) < 0.5) | ((s["ua"] / s["n"]) < 0.2)].index)


# beta computed with the paper's own code (see paper_beta.py)
from paper_beta import fit_beta


def main():
    con = sqlite3.connect(DB)

    print("Loading posts + snapshot coverage...")
    posts = pd.read_sql_query(
        f"SELECT id, created_at FROM posts WHERE created_at < '{CUTOFF}'", con)
    agg = pd.read_sql_query(
        "SELECT post_id, COUNT(*) n, MIN(recorded_at) first_rec, "
        "MAX(recorded_at) last_rec FROM post_snapshots GROUP BY post_id", con)

    print("Computing spam filter (reads all comments)...")
    spam = spam_post_ids(con)

    cov = posts.merge(agg, left_on="id", right_on="post_id", how="inner")
    cov = cov[~cov["id"].isin(spam)].copy()
    for c in ["created_at", "first_rec", "last_rec"]:
        cov[c] = pd.to_datetime(cov[c], utc=True)
    cov["first_age"] = (cov["first_rec"] - cov["created_at"]).dt.total_seconds() / 3600
    cov["last_age"] = (cov["last_rec"] - cov["created_at"]).dt.total_seconds() / 3600

    cohort = cov[(cov["first_age"] <= FIRST_AGE_MAX) &
                 (cov["last_age"] >= HORIZON)].copy()
    print(f"  cohort posts (first<={FIRST_AGE_MAX:g}h, followed>={HORIZON:g}h): "
          f"{len(cohort):,}")
    cohort_ids = set(cohort["id"])

    # pull only cohort snapshots via a temp-table join (keeps memory small)
    con.execute("CREATE TEMP TABLE cohort(pid TEXT PRIMARY KEY)")
    con.executemany("INSERT INTO cohort VALUES (?)", [(i,) for i in cohort_ids])
    snaps = pd.read_sql_query(
        "SELECT s.post_id, s.upvotes, s.comment_count, s.recorded_at "
        "FROM post_snapshots s JOIN cohort c ON s.post_id = c.pid", con)
    con.close()
    print(f"  cohort snapshot rows: {len(snaps):,}")

    snaps["recorded_at"] = pd.to_datetime(snaps["recorded_at"], utc=True)
    created = cohort.set_index("id")["created_at"]
    snaps = snaps.join(created, on="post_id")
    snaps["age"] = (snaps["recorded_at"] - snaps["created_at"]).dt.total_seconds() / 3600
    snaps = snaps[snaps["age"] >= 0].sort_values(["post_id", "age"])

    # interpolate each post's curve onto the common age grid (clamped at ends)
    print("Interpolating per-post curves onto common age grid...")
    up_rows, com_rows, ids = [], [], []
    for pid, g in snaps.groupby("post_id", sort=False):
        a = g["age"].to_numpy()
        if a.size < 2:
            continue
        up_rows.append(np.interp(GRID, a, g["upvotes"].to_numpy()))
        com_rows.append(np.interp(GRID, a, g["comment_count"].to_numpy()))
        ids.append(pid)
    U = pd.DataFrame(up_rows, index=ids, columns=GRID)
    C = pd.DataFrame(com_rows, index=ids, columns=GRID)
    print(f"  posts with usable curves: {len(U):,}\n")

    # require positive final at the horizon so fractions are well-defined
    okU = U[HORIZON] > 0
    okC = C[HORIZON] > 0
    fracU = U[okU].div(U[okU][HORIZON], axis=0).clip(upper=1.0)
    fracC = C[okC].div(C[okC][HORIZON], axis=0).clip(upper=1.0)

    # ---- 1. accumulation curves ----
    print("=== 1. mean fraction of final (72h) reached, by age ===")
    print(f"  {'age(h)':>7} {'upvotes':>9} {'comments':>9}")
    mu, mc = fracU.mean(), fracC.mean()
    for t in GRID:
        print(f"  {t:7.0f} {mu[t]:9.3f} {mc[t]:9.3f}")
    print(f"\n  at 24h: upvotes at {mu[24.0]:.1%} of final vs comments at "
          f"{mc[24.0]:.1%}  (H3: upvotes higher)\n")

    # ---- 2. saturation timing: age to reach 90% of final ----
    def t90(frac):
        out = []
        for _, row in frac.iterrows():
            hit = np.where(row.to_numpy() >= 0.9)[0]
            out.append(GRID[hit[0]] if hit.size else np.nan)
        return pd.Series(out)
    t90u, t90c = t90(fracU), t90(fracC)
    print("=== 2. per-post age to reach 90% of final (h) ===")
    print(f"  upvotes : median={t90u.median():.0f}  mean={t90u.mean():.1f}")
    print(f"  comments: median={t90c.median():.0f}  mean={t90c.mean():.1f}")
    print(f"  (H3: upvotes reach 90% earlier)\n")

    # ---- 3. late-life increment share (24h -> 72h) ----
    shareU = ((U[okU][72.0] - U[okU][24.0]) / U[okU][72.0]).clip(0, 1)
    shareC = ((C[okC][72.0] - C[okC][24.0]) / C[okC][72.0]).clip(0, 1)
    print("=== 3. share of final accrued AFTER 24h (24h->72h window) ===")
    print(f"  upvotes : mean={shareU.mean():.1%}")
    print(f"  comments: mean={shareC.mean():.1%}")
    print(f"  (H3: comments keep accruing late, upvotes already saturated)\n")

    # ---- 4. cross-sectional beta at matched age ----
    print("=== 4. fit_beta(upvotes vs comment_count) at matched age ===")
    betas = []
    for t in GRID:
        b, nb = fit_beta(C[t].to_numpy(), U[t].to_numpy())
        betas.append(b)
        print(f"  age {t:5.0f}h : beta = {b:.3f}  [{nb} bins]")
    print(f"  (H3: beta drifts toward the crawl-time ~0.70 as upvotes saturate)")

    # ---- figure ----
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].plot(GRID, mu.values, "o-", label="upvotes", color="#1f77b4")
    ax[0].plot(GRID, mc.values, "s-", label="comments", color="#d62728")
    ax[0].set(xlabel="post age (h)", ylabel="mean fraction of 72h value",
              title="(a) accumulation: upvotes saturate vs comments")
    ax[0].axvline(24, ls=":", color="grey"); ax[0].legend(); ax[0].grid(alpha=.3)
    ax[1].plot(GRID, betas, "o-", color="#2ca02c")
    ax[1].axhline(0.70, ls="--", color="grey", label="crawl-time ~0.70")
    ax[1].axhline(1.0, ls=":", color="black", label="linear")
    ax[1].set(xlabel="post age at measurement (h)", ylabel="beta (upvotes vs comments)",
              title="(b) cross-sectional beta vs age")
    ax[1].legend(); ax[1].grid(alpha=.3)
    fig.tight_layout()
    os.makedirs(FIGDIR, exist_ok=True)
    out = os.path.join(FIGDIR, "h3_saturation.pdf")
    fig.savefig(out, bbox_inches="tight")
    print(f"\nFigure saved: {out}")


if __name__ == "__main__":
    main()

"""
H2 (authority story) test for the Moltbook upvote-scaling follow-up.

Hypothesis: votes track an author's social standing (karma, follower_count) rather
than discussion size, decoupling votes from engagement. For H2 to *explain* the
sublinearity (upvotes beta ~ 0.70 < 1 while direct replies ~ 1), author authority
must ABSORB the size->vote relationship. We test that from four angles:

  A. Correlation     - do upvotes even track karma/followers? (Spearman; if not, H2 dies)
  B. Variance decomp - OLS log(upvotes) ~ size-only vs authority-only vs full.
                       Does authority explain votes better than size, and does the
                       size coefficient collapse once authority is controlled for?
  C. Decoupling      - is author standing roughly flat across discussion size?
                       (If authority rises in lockstep with size it can't explain
                        why votes lag size.)
  D. Stratified beta - refit beta (upvotes vs size) within authority terciles.
                       H2 predicts beta flattens within a fixed-authority stratum;
                       if beta stays ~0.70 everywhere, sublinearity is authority-
                       independent and H2 fails.

Mirrors h1_net_score.py choices: comment_count = discussion size, paper spam filter,
created_at <= 2026-02-08, beta via log-binned log-log OLS.
"""
import os
import sqlite3
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "moltbook_upload.db")
CUTOFF = "2026-02-09"  # exclusive -> includes through Feb 8


def spam_post_ids(con):
    """Paper's two spam criteria, applied at post level (see h1_net_score.py)."""
    df = pd.read_sql_query("SELECT post_id, content, author_id FROM comments", con)
    g = df.groupby("post_id")
    stats_ = g.agg(
        n=("content", "size"),
        uniq_content=("content", "nunique"),
        uniq_author=("author_id", "nunique"),
    )
    stats_ = stats_[stats_["n"] >= 5]
    frac_content = stats_["uniq_content"] / stats_["n"]
    frac_author = stats_["uniq_author"] / stats_["n"]
    return set(stats_[(frac_content < 0.5) | (frac_author < 0.2)].index)


def fit_beta(size, value, nbins=25):
    """Log-bin by size, average value per bin, fit log-log slope (>=5 pts/bin)."""
    m = (size > 0) & (value > 0)
    s, v = size[m], value[m]
    if s.size < 10:
        return np.nan, 0
    edges = np.logspace(np.log10(s.min()), np.log10(s.max()), nbins + 1)
    idx = np.digitize(s, edges)
    xs, ys = [], []
    for b in range(1, nbins + 1):
        sel = idx == b
        if sel.sum() >= 5:
            xs.append(s[sel].mean())
            ys.append(v[sel].mean())
    if len(xs) < 5:
        return np.nan, len(xs)
    lx, ly = np.log10(np.array(xs)), np.log10(np.array(ys))
    beta, _ = np.polyfit(lx, ly, 1)
    return beta, len(xs)


def ols(y, X, names):
    """OLS with intercept. Returns dict with R2 and standardized betas.

    Standardized betas (z-score y and predictors) make coefficients comparable
    across predictors on different scales (size vs karma vs followers).
    """
    A = np.column_stack([np.ones_like(y)] + list(X))
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    r2 = 1.0 - resid.var() / y.var()
    # standardized betas
    yz = (y - y.mean()) / y.std()
    Xz = [(x - x.mean()) / x.std() for x in X]
    Az = np.column_stack([np.ones_like(yz)] + Xz)
    cz, *_ = np.linalg.lstsq(Az, yz, rcond=None)
    return {"r2": r2, "raw": dict(zip(names, coef[1:])),
            "std": dict(zip(names, cz[1:]))}


def main():
    con = sqlite3.connect(DB)

    print("Loading posts...")
    posts = pd.read_sql_query(
        f"SELECT id, author_id, upvotes, downvotes, comment_count "
        f"FROM posts WHERE created_at < '{CUTOFF}'", con)
    print(f"  posts (<= Feb 8): {len(posts):,}")

    print("Loading agents (authority)...")
    agents = pd.read_sql_query(
        "SELECT id, karma, follower_count, following_count FROM agents", con)

    print("Computing spam filter (reads all comments)...")
    spam = spam_post_ids(con)
    posts = posts[~posts["id"].isin(spam)].copy()
    print(f"  posts after spam filter: {len(posts):,}")
    con.close()

    # join post -> author standing
    df = posts.merge(agents, left_on="author_id", right_on="id",
                     how="left", suffixes=("", "_agent"))
    matched = df["karma"].notna()
    print(f"  posts with matched agent row: {matched.sum():,} "
          f"({matched.mean():.1%})")
    df = df[matched].copy()

    # keep posts with a real discussion + at least one upvote (for log/beta)
    df = df[(df["comment_count"] > 0) & (df["upvotes"] > 0)].copy()
    print(f"  posts used (size>0 & upvotes>0): {len(df):,}\n")

    size = df["comment_count"].to_numpy(float)
    up = df["upvotes"].to_numpy(float)
    karma = df["karma"].to_numpy(float)
    foll = df["follower_count"].to_numpy(float)

    # log transforms (karma can be negative -> clip at 0 before log1p)
    ls = np.log10(size)
    ly = np.log10(up)
    lk = np.log10(1 + np.clip(karma, 0, None))
    lf = np.log10(1 + np.clip(foll, 0, None))

    print("Authority coverage:")
    print(f"  karma:     median={np.median(karma):.0f}  "
          f"frac<=0={np.mean(karma <= 0):.1%}  max={karma.max():.0f}")
    print(f"  followers: median={np.median(foll):.0f}  "
          f"frac==0={np.mean(foll == 0):.1%}  max={foll.max():.0f}\n")

    # ---- A. correlations (Spearman, rank-robust) ----
    print("=== A. Spearman correlations with upvotes ===")
    for nm, arr in [("size (comment_count)", size), ("karma", karma),
                    ("follower_count", foll)]:
        rho, _ = stats.spearmanr(arr, up)
        print(f"  upvotes vs {nm:22s}: rho = {rho:+.3f}")
    rho_kf, _ = stats.spearmanr(karma, foll)
    print(f"  (karma vs followers collinearity: rho = {rho_kf:+.3f})\n")

    # ---- B. variance decomposition ----
    print("=== B. OLS variance decomposition  (y = log10 upvotes) ===")
    m1 = ols(ly, [ls], ["size"])
    m2 = ols(ly, [lk, lf], ["karma", "foll"])
    m3 = ols(ly, [ls, lk, lf], ["size", "karma", "foll"])
    print(f"  M1 size only      : R2={m1['r2']:.3f}  "
          f"std_beta[size]={m1['std']['size']:+.3f}")
    print(f"  M2 authority only : R2={m2['r2']:.3f}  "
          f"std_beta[karma]={m2['std']['karma']:+.3f} "
          f"std_beta[foll]={m2['std']['foll']:+.3f}")
    print(f"  M3 full           : R2={m3['r2']:.3f}  "
          f"std_beta[size]={m3['std']['size']:+.3f} "
          f"std_beta[karma]={m3['std']['karma']:+.3f} "
          f"std_beta[foll]={m3['std']['foll']:+.3f}")
    print(f"  -> size raw coef (the 'beta'): M1={m1['raw']['size']:+.3f} "
          f"-> M3={m3['raw']['size']:+.3f}  "
          f"(collapse toward 0 would support H2)\n")

    # ---- C. is authority flat across discussion size? ----
    print("=== C. mean author standing vs discussion size ===")
    b_k, n_k = fit_beta(size, np.clip(karma, 0, None) + 1)
    b_f, n_f = fit_beta(size, foll + 1)
    print(f"  slope of mean karma     vs size (log-log): {b_k:+.3f}  [{n_k} bins]")
    print(f"  slope of mean followers vs size (log-log): {b_f:+.3f}  [{n_f} bins]")
    print(f"  (upvotes-vs-size beta is ~0.70; if authority slope ~0 it is flat\n"
          f"   across sizes and cannot drive the size dependence of votes)\n")

    # ---- D. stratified beta within authority terciles ----
    print("=== D. upvotes-vs-size beta within authority terciles ===")
    for nm, key in [("karma", karma), ("followers", foll)]:
        qs = np.quantile(key, [1/3, 2/3])
        labels = ["low ", "mid ", "high"]
        masks = [key <= qs[0], (key > qs[0]) & (key <= qs[1]), key > qs[1]]
        print(f"  by {nm}:")
        for lab, mk in zip(labels, masks):
            b, nb = fit_beta(size[mk], up[mk])
            print(f"    {lab} (n={mk.sum():>6,}): beta = {b:.3f}  [{nb} bins]")
    print("\n  (full-sample upvote beta ~ 0.70; if beta stays ~0.70 in every\n"
          "   stratum the sublinearity is authority-independent -> H2 fails)")


if __name__ == "__main__":
    main()

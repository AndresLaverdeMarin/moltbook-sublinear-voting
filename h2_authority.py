"""
H2 (authority story) test for the Moltbook upvote-scaling follow-up.

Hypothesis: votes track an author's social standing rather than discussion size,
decoupling votes from engagement. For H2 to *explain* the sublinearity (upvotes
beta ~ 0.70 < 1 while direct replies ~ 1), author authority must ABSORB the
size->vote relationship.

Moltbook's follow graph is DIRECTIONAL, so "standing" is several distinct signals:
  - karma            : reputation score.
  - follower_count   : INBOUND - how many agents follow this one (prestige/authority).
  - following_count  : OUTBOUND - how many this agent follows (gregariousness/activity).
  - ff_ratio         : follower_count / (following_count + 1) - the influencer-vs-follower
                       axis (high = followed by many, follows few).
  - x_follower_count / x_verified : OFF-PLATFORM standing from the linked X/Twitter
                       account (sparse: ~80% zero, ~0.2% verified on the used subset),
                       so reported descriptively (block E), not in the OLS/terciles.

We test that from four angles (A-D) on the on-platform standing signals, plus a
descriptive off-platform block (E):

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
DB = os.environ.get("MOLTBOOK_DB", os.path.join(HERE, "..", "moltbook_upload.db"))
START  = os.environ.get("MOLTBOOK_START", "1970-01-01")    # inclusive lower bound on created_at
CUTOFF = os.environ.get("MOLTBOOK_CUTOFF", "2026-02-09")   # exclusive upper bound (default: through Feb 8)


def spam_post_ids(con):
    """Authors' two spam criteria, applied at post level (see h1_net_score.py)."""
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
    flagged = set(stats_[(frac_content < 0.5) | (frac_author < 0.2)].index)
    high_count = con.execute(
        "SELECT p.id FROM posts p "
        "LEFT JOIN (SELECT DISTINCT post_id FROM comments) c ON p.id = c.post_id "
        "WHERE c.post_id IS NULL AND p.comment_count > 200").fetchall()
    flagged.update(r[0] for r in high_count)
    return flagged


# beta computed with the paper's own code (see paper_beta.py)
from paper_beta import fit_beta


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
        f"FROM posts WHERE created_at >= '{START}' AND created_at < '{CUTOFF}'", con)
    print(f"  posts (<= Feb 8): {len(posts):,}")

    print("Loading agents (authority)...")
    agents = pd.read_sql_query(
        "SELECT id, karma, follower_count, following_count, "
        "x_follower_count, x_verified FROM agents", con)

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
    following = df["following_count"].to_numpy(float)        # outbound follows
    ffr = foll / (following + 1.0)                           # follower/following ratio
    xfoll = df["x_follower_count"].to_numpy(float)           # off-platform (X) standing
    xver = df["x_verified"].to_numpy(float)

    # log transforms (karma can be negative -> clip at 0 before log1p)
    ls = np.log10(size)
    ly = np.log10(up)
    lk = np.log10(1 + np.clip(karma, 0, None))
    lf = np.log10(1 + np.clip(foll, 0, None))
    lg = np.log10(1 + np.clip(following, 0, None))
    lr = np.log10(1 + np.clip(ffr, 0, None))

    print("Authority coverage:")
    print(f"  karma:     median={np.median(karma):.0f}  "
          f"frac<=0={np.mean(karma <= 0):.1%}  max={karma.max():.0f}")
    print(f"  followers: median={np.median(foll):.0f}  "
          f"frac==0={np.mean(foll == 0):.1%}  max={foll.max():.0f}")
    print(f"  following: median={np.median(following):.0f}  "
          f"frac==0={np.mean(following == 0):.1%}  max={following.max():.0f}")
    print(f"  ff_ratio:  median={np.median(ffr):.2f}  "
          f"frac==0={np.mean(ffr == 0):.1%}  max={ffr.max():.0f}")
    print(f"  x_follow:  median={np.median(xfoll):.0f}  "
          f"frac==0={np.mean(xfoll == 0):.1%}  max={xfoll.max():.0f}  "
          f"verified={int((xver == 1).sum()):,} ({np.mean(xver == 1):.2%})\n")

    # ---- A. correlations (Spearman, rank-robust) ----
    print("=== A. Spearman correlations with upvotes ===")
    for nm, arr in [("size (comment_count)", size), ("karma", karma),
                    ("follower_count", foll), ("following_count", following),
                    ("ff_ratio", ffr), ("x_follower_count", xfoll)]:
        rho, _ = stats.spearmanr(arr, up)
        print(f"  upvotes vs {nm:22s}: rho = {rho:+.3f}")
    rho_kf, _ = stats.spearmanr(karma, foll)
    rho_ff, _ = stats.spearmanr(foll, following)
    print(f"  (karma vs followers collinearity:   rho = {rho_kf:+.3f})")
    print(f"  (followers vs following collinearity: rho = {rho_ff:+.3f})\n")

    # ---- B. variance decomposition ----
    print("=== B. OLS variance decomposition  (y = log10 upvotes) ===")
    anames = ["karma", "foll", "following", "ffratio"]
    m1 = ols(ly, [ls], ["size"])
    m2 = ols(ly, [lk, lf, lg, lr], anames)
    m3 = ols(ly, [ls, lk, lf, lg, lr], ["size"] + anames)
    print(f"  M1 size only      : R2={m1['r2']:.3f}  "
          f"std_beta[size]={m1['std']['size']:+.3f}")
    print(f"  M2 authority only : R2={m2['r2']:.3f}  "
          + " ".join(f"std[{k}]={m2['std'][k]:+.3f}" for k in anames))
    print(f"  M3 full           : R2={m3['r2']:.3f}  std[size]={m3['std']['size']:+.3f}  "
          + " ".join(f"std[{k}]={m3['std'][k]:+.3f}" for k in anames))
    print(f"  -> size raw coef (the 'beta'): M1={m1['raw']['size']:+.3f} "
          f"-> M3={m3['raw']['size']:+.3f}  "
          f"(collapse toward 0 would support H2)\n")

    # ---- C. is authority flat across discussion size? ----
    print("=== C. mean author standing vs discussion size (log-log slope) ===")
    for nm, arr in [("karma    ", np.clip(karma, 0, None)), ("followers", foll),
                    ("following", following), ("ff_ratio ", ffr)]:
        b, nb = fit_beta(size, arr + 1)
        print(f"  slope of mean {nm} vs size: {b:+.3f}  [{nb} bins]")
    print(f"  (upvotes-vs-size beta is ~0.70; if authority slope ~0 it is flat\n"
          f"   across sizes and cannot drive the size dependence of votes)\n")

    # ---- D. stratified beta within authority terciles ----
    print("=== D. upvotes-vs-size beta within authority terciles ===")
    for nm, key in [("karma", karma), ("followers", foll),
                    ("following", following), ("ff_ratio", ffr)]:
        qs = np.quantile(key, [1/3, 2/3])
        labels = ["low ", "mid ", "high"]
        masks = [key <= qs[0], (key > qs[0]) & (key <= qs[1]), key > qs[1]]
        print(f"  by {nm}:")
        for lab, mk in zip(labels, masks):
            b, nb = fit_beta(size[mk], up[mk])
            print(f"    {lab} (n={mk.sum():>6,}): beta = {b:.3f}  [{nb} bins]")
    print("\n  (full-sample upvote beta ~ 0.70; if beta stays ~0.70 in every\n"
          "   stratum the sublinearity is authority-independent -> H2 fails)\n")

    # ---- E. off-platform (X) standing: descriptive (too sparse for OLS/terciles) ----
    print("=== E. off-platform standing (X/Twitter), descriptive ===")
    rho_x, _ = stats.spearmanr(xfoll, up)
    print(f"  upvotes vs x_follower_count: rho = {rho_x:+.3f}  "
          f"(nonzero on {np.mean(xfoll > 0):.1%} of used posts)")
    has_x = xfoll > 0
    print(f"  upvotes-vs-size beta, x_follower==0 (n={int((~has_x).sum()):,}): "
          f"{fit_beta(size[~has_x], up[~has_x])[0]:.3f}")
    print(f"  upvotes-vs-size beta, x_follower>0  (n={int(has_x.sum()):,}): "
          f"{fit_beta(size[has_x], up[has_x])[0]:.3f}")
    ver = xver == 1
    if ver.sum() >= 5:
        bv, nbv = fit_beta(size[ver], up[ver])
        print(f"  x_verified authors (n={int(ver.sum()):,}): mean upvotes="
              f"{up[ver].mean():.1f} vs unverified {up[~ver].mean():.1f}; "
              f"beta={bv:.3f} [{nbv} bins]")
    else:
        print(f"  x_verified authors: n={int(ver.sum()):,} (too few to fit)")
    print("  (off-platform reputation is rare here and does not change the picture)")


if __name__ == "__main__":
    main()

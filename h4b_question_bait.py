"""
H4b - the "discussion-bait" refinement: does question-asking moderate the
upvote-vs-size exponent, and is the effect specific to voting (not replying)?

Context: H4 (contention) was falsified, but one content sub-signal survived --
question-heavy threads scale most sublinearly (beta 0.715 -> 0.462, low->high
question rate). This script quantifies that properly. The paper's anomaly is that
upvotes scale sublinearly (beta ~0.78) with discussion size while direct replies
scale linearly (beta ~1). The discussion-bait idea: question-provoking posts grow
via replies (agents answer) but those don't convert to proportional upvotes --
so question-rate should flatten the UPVOTE exponent while leaving the REPLY
exponent ~1, widening the gap.

Tests (on the <100-comment complete-tree subset, paper spam filter, <=Feb8):
  1. Continuous moderator: OLS log(upvotes) ~ log(size) + qfrac + log(size)*qfrac.
     A negative interaction => question-rate flattens the upvote slope (beta).
  2. beta(upvotes vs size) across question-rate deciles.
  3. Upvote-specific? beta(direct replies vs size) across the same deciles; if it
     stays ~1 while upvote-beta falls, the voting/replying gap widens with qrate.
  4. Upvote efficiency (upvotes per comment) vs question-rate.
  5. OP-question vs Q&A-thread: split by whether the POST asks a question (post_q).

Direct replies = depth-0 stored comments (top-level). Size = comment_count.
"""
import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "moltbook_upload.db")
FIGDIR = os.path.join(HERE, "figures")
CUTOFF = "2026-02-09"


def spam_post_ids(con):
    df = pd.read_sql_query("SELECT post_id, content, author_id FROM comments", con)
    g = df.groupby("post_id")
    s = g.agg(n=("content", "size"), uc=("content", "nunique"),
              ua=("author_id", "nunique"))
    s = s[s["n"] >= 5]
    return set(s[((s["uc"] / s["n"]) < 0.5) | ((s["ua"] / s["n"]) < 0.2)].index)


def fit_beta(size, value, nbins=25):
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
            xs.append(s[sel].mean()); ys.append(v[sel].mean())
    if len(xs) < 5:
        return np.nan, len(xs)
    beta, _ = np.polyfit(np.log10(xs), np.log10(ys), 1)
    return beta, len(xs)


def main():
    con = sqlite3.connect(DB)

    print("Loading <100-comment posts...")
    posts = pd.read_sql_query(
        f"SELECT id, upvotes, comment_count, (instr(content,'?')>0) post_q "
        f"FROM posts WHERE created_at < '{CUTOFF}' "
        f"AND comment_count > 0 AND comment_count < 100", con)
    print(f"  posts: {len(posts):,}")

    print("Computing spam filter...")
    spam = spam_post_ids(con)
    posts = posts[~posts["id"].isin(spam)].copy()

    con.execute("CREATE TEMP TABLE subset(pid TEXT PRIMARY KEY)")
    con.executemany("INSERT INTO subset VALUES (?)", [(i,) for i in posts["id"]])

    print("Streaming comments -> question rate + direct-reply count...")
    parts = []
    q = ("SELECT c.post_id, substr(c.content,1,600) snip, c.depth depth "
         "FROM comments c JOIN subset s ON c.post_id=s.pid")
    for chunk in pd.read_sql_query(q, con, chunksize=400000):
        chunk["qst"] = chunk["snip"].str.contains("?", regex=False, na=False)
        chunk["direct"] = chunk["depth"] == 0
        parts.append(chunk.groupby("post_id").agg(
            n=("depth", "size"), nq=("qst", "sum"), ndirect=("direct", "sum")))
    con.close()
    feat = pd.concat(parts).groupby(level=0).sum()
    feat["qfrac"] = feat["nq"] / feat["n"]

    df = posts.merge(feat, left_on="id", right_index=True, how="inner")
    df = df[(df["upvotes"] > 0) & (df["comment_count"] > 0)].copy()
    print(f"  posts used: {len(df):,}\n")

    size = df["comment_count"].to_numpy(float)
    up = df["upvotes"].to_numpy(float)
    rep = df["ndirect"].to_numpy(float)
    qf = df["qfrac"].to_numpy(float)

    # ---- 1. continuous moderator regression ----
    print("=== 1. continuous moderator: log(upvotes) ~ logS + qfrac + logS*qfrac ===")
    ls = np.log10(size)
    qc = qf - qf.mean()                     # center qfrac so main slope is at mean q
    y = np.log10(up)
    X = np.column_stack([np.ones_like(y), ls, qc, ls * qc])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    r2 = 1 - (y - X @ coef).var() / y.var()
    X0 = np.column_stack([np.ones_like(y), ls, qc])           # no interaction
    c0, *_ = np.linalg.lstsq(X0, y, rcond=None)
    r2_0 = 1 - (y - X0 @ c0).var() / y.var()
    b_logS, b_qf, b_int = coef[1], coef[2], coef[3]
    q10, q90 = np.quantile(qf, [.1, .9])
    slope_lo = b_logS + b_int * (q10 - qf.mean())
    slope_hi = b_logS + b_int * (q90 - qf.mean())
    print(f"  slope[logS] (upvote beta at mean qrate) = {b_logS:+.3f}")
    print(f"  coef[qfrac]                              = {b_qf:+.3f}")
    print(f"  coef[logS x qfrac]  (INTERACTION)        = {b_int:+.3f}")
    print(f"  R2 with interaction={r2:.3f}  vs without={r2_0:.3f}  (delta {r2-r2_0:+.4f})")
    print(f"  implied upvote beta at qfrac=Q10({q10:.2f}) = {slope_lo:.3f}")
    print(f"  implied upvote beta at qfrac=Q90({q90:.2f}) = {slope_hi:.3f}")
    print(f"  (negative interaction => question-rate FLATTENS the upvote exponent)\n")

    # ---- 2 & 3. upvote-beta and reply-beta across question deciles ----
    print("=== 2&3. beta(upvotes) and beta(direct replies) vs size, by qfrac decile ===")
    dec = pd.qcut(qf, 8, labels=False, duplicates="drop")
    ndec = dec.max() + 1
    centers, bup, brep = [], [], []
    print(f"  {'qfrac':>8} {'n':>8} {'beta_up':>8} {'beta_reply':>11}")
    for d in range(ndec):
        mk = dec == d
        bu, _ = fit_beta(size[mk], up[mk])
        br, _ = fit_beta(size[mk], rep[mk])
        centers.append(qf[mk].mean()); bup.append(bu); brep.append(br)
        print(f"  {qf[mk].mean():8.3f} {mk.sum():8,} {bu:8.3f} {br:11.3f}")
    print(f"  full sample: beta_up={fit_beta(size,up)[0]:.3f}  "
          f"beta_reply={fit_beta(size,rep)[0]:.3f}")
    print(f"  (H4b: beta_up falls with qrate while beta_reply stays ~1 -> gap widens)\n")

    # ---- 4. upvote efficiency ----
    print("=== 4. upvote efficiency (upvotes per comment) vs qfrac ===")
    eff = up / size
    rho, _ = stats.spearmanr(qf, eff)
    print(f"  Spearman(qfrac, upvotes/comment) = {rho:+.3f}")
    lo_eff = eff[qf <= q10].mean(); hi_eff = eff[qf >= q90].mean()
    print(f"  mean upvotes/comment: low-q={lo_eff:.3f}  high-q={hi_eff:.3f}  "
          f"({hi_eff/lo_eff-1:+.0%})\n")

    # ---- 5. OP-question vs not ----
    print("=== 5. OP asks a question (post_q) vs not ===")
    for lab, mk in [("post_q=1 (OP question)", df["post_q"] == 1),
                    ("post_q=0", df["post_q"] == 0)]:
        mk = mk.to_numpy()
        bu, _ = fit_beta(size[mk], up[mk])
        print(f"  {lab:24s} (n={mk.sum():>7,}): beta_up={bu:.3f}  "
              f"mean qfrac={qf[mk].mean():.3f}  mean up/comment={ (up[mk]/size[mk]).mean():.3f}")

    # ---- figure ----
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.3))
    ax[0].plot(centers, bup, "o-", color="#1f77b4", label="upvotes")
    ax[0].plot(centers, brep, "s-", color="#d62728", label="direct replies")
    ax[0].axhline(1.0, ls=":", color="black"); ax[0].axhline(0.70, ls="--", color="grey")
    ax[0].set(xlabel="comment question-rate", ylabel="beta vs size",
              title="(a) question-rate moderates the upvote exponent")
    ax[0].legend(); ax[0].grid(alpha=.3)
    # efficiency binned
    qb = pd.qcut(qf, 12, labels=False, duplicates="drop")
    xs = [qf[qb == i].mean() for i in range(qb.max() + 1)]
    ys = [(up[qb == i] / size[qb == i]).mean() for i in range(qb.max() + 1)]
    ax[1].plot(xs, ys, "o-", color="#2ca02c")
    ax[1].set(xlabel="comment question-rate", ylabel="mean upvotes / comment",
              title="(b) upvote efficiency vs question-rate"); ax[1].grid(alpha=.3)
    # gap
    gap = np.array(brep) - np.array(bup)
    ax[2].plot(centers, gap, "o-", color="#9467bd")
    ax[2].set(xlabel="comment question-rate", ylabel="beta_reply - beta_upvote",
              title="(c) voting/replying gap widens with question-rate"); ax[2].grid(alpha=.3)
    fig.tight_layout()
    os.makedirs(FIGDIR, exist_ok=True)
    out = os.path.join(FIGDIR, "h4b_question_bait.pdf")
    fig.savefig(out, bbox_inches="tight")
    print(f"\nFigure saved: {out}")


if __name__ == "__main__":
    main()

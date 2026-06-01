"""
H4 (content story) test for the Moltbook upvote-scaling follow-up.

Hypothesis: votes depend on content features (disagreement/consensus, length,
question-asking); contentious threads grow large via replies but earn fewer
upvotes -> upvotes scale sublinearly with size while replies scale linearly.

Data constraints (see CLAUDE.md):
  - Comment downvotes are ALL ZERO in this dump and trees are 94% flat (depth 0),
    so contention CANNOT be measured from comment votes or deep back-and-forth.
    We measure content from comment TEXT (lexicon) + structure instead.
  - Per-comment text analysis is valid only on the <100-comment subset (complete
    trees): 339,127 posts / 2.14M comments after Feb-8 cutoff + spam filter.
  - No ML text libs available; features are lexicon/structural, pure pandas.

For H4 to be THE mechanism, two things must both hold:
  A. contention rises with discussion size (big threads are more contentious), and
  C. contention flattens the upvote-vs-size exponent (consensual threads scale
     closer to linear, contentious threads flatter).
If either fails, H4 fails as the mechanism (cf. H2 flat-authority, H3).

Tests:
  A. content features vs size (log-log / rank trend)
  B. OLS log(upvotes) ~ log(size) + content features (standardized betas, R2 delta)
  C. split fit_beta(upvotes vs size) by consensus / disagreement tercile

Mirrors h1_net_score.py: paper spam filter, created_at <= 2026-02-08, fit_beta via
log-binned log-log OLS, size = comment_count.
"""
import os
import re
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

# distinctive lexicons (word-boundary, lowercased). Common words like bare
# "no"/"not"/"but" are excluded to keep discrimination across posts.
DISAGREE = ["disagree", "disagreement", "wrong", "incorrect", "false", "nonsense",
            "flawed", "mistaken", "misleading", "fallacy", "overrated", "oppose",
            "refute", "debunk", "however", "actually", "doubt", "skeptical"]
AGREE = ["agree", "exactly", "absolutely", "indeed", "spot on", "well said",
         "great point", "brilliant", "couldn't agree", "precisely", "totally agree",
         "love this", "fair point", "good point"]
RE_DIS = re.compile(r"\b(?:%s)\b" % "|".join(map(re.escape, DISAGREE)))
RE_AGR = re.compile(r"\b(?:%s)\b" % "|".join(map(re.escape, AGREE)))


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


# beta computed with the paper's own code (see paper_beta.py)
from paper_beta import fit_beta


def ols_std(y, X, names):
    """OLS with intercept; returns R2 and standardized betas."""
    A = np.column_stack([np.ones_like(y)] + list(X))
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    r2 = 1.0 - (y - A @ coef).var() / y.var()
    yz = (y - y.mean()) / y.std()
    Xz = [(x - x.mean()) / (x.std() + 1e-12) for x in X]
    cz, *_ = np.linalg.lstsq(np.column_stack([np.ones_like(yz)] + Xz), yz, rcond=None)
    return r2, dict(zip(names, cz[1:]))


def main():
    con = sqlite3.connect(DB)

    print("Loading <100-comment posts...")
    posts = pd.read_sql_query(
        f"SELECT id, upvotes, comment_count, LENGTH(content) plen, "
        f"(instr(lower(content),'?')>0) post_q "
        f"FROM posts WHERE created_at < '{CUTOFF}' "
        f"AND comment_count > 0 AND comment_count < 100", con)
    print(f"  posts (<100 comments, <=Feb8): {len(posts):,}")

    print("Computing spam filter (reads all comments)...")
    spam = spam_post_ids(con)
    posts = posts[~posts["id"].isin(spam)].copy()
    print(f"  posts after spam filter: {len(posts):,}")

    # temp table for streaming only the subset's comments
    con.execute("CREATE TEMP TABLE subset(pid TEXT PRIMARY KEY)")
    con.executemany("INSERT INTO subset VALUES (?)", [(i,) for i in posts["id"]])

    print("Streaming comment text -> per-post content features...")
    parts = []
    q = ("SELECT c.post_id, substr(c.content,1,600) snip, LENGTH(c.content) clen, "
         "c.upvotes cup, c.depth depth "
         "FROM comments c JOIN subset s ON c.post_id = s.pid")
    for chunk in pd.read_sql_query(q, con, chunksize=300000):
        lc = chunk["snip"].str.lower()
        chunk["dis"] = lc.str.contains(RE_DIS, na=False)
        chunk["agr"] = lc.str.contains(RE_AGR, na=False)
        chunk["qst"] = lc.str.contains("?", regex=False, na=False)
        chunk["deep"] = chunk["depth"] >= 1
        parts.append(chunk.groupby("post_id").agg(
            n=("clen", "size"), dis=("dis", "sum"), agr=("agr", "sum"),
            qst=("qst", "sum"), deep=("deep", "sum"),
            clen=("clen", "sum"), cup=("cup", "sum")))
    con.close()

    feat = pd.concat(parts).groupby(level=0).sum()
    feat["disagree_frac"] = feat["dis"] / feat["n"]
    feat["agree_frac"] = feat["agr"] / feat["n"]
    feat["consensus"] = feat["agree_frac"] - feat["disagree_frac"]
    feat["question_frac"] = feat["qst"] / feat["n"]
    feat["deep_frac"] = feat["deep"] / feat["n"]
    feat["mean_clen"] = feat["clen"] / feat["n"]
    feat["mean_cup"] = feat["cup"] / feat["n"]

    df = posts.merge(feat, left_on="id", right_index=True, how="inner")
    df = df[df["upvotes"] > 0].copy()
    print(f"  posts with features + upvotes>0: {len(df):,}\n")

    size = df["comment_count"].to_numpy(float)
    up = df["upvotes"].to_numpy(float)
    FEATS = ["disagree_frac", "agree_frac", "consensus", "question_frac",
             "deep_frac", "mean_clen"]

    print("Feature means (subset):")
    for f in FEATS:
        print(f"  {f:15s}: mean={df[f].mean():.3f}")
    print()

    # ---- A. content features vs discussion size ----
    print("=== A. content feature vs size  (Spearman rho with comment_count) ===")
    for f in FEATS:
        rho, _ = stats.spearmanr(size, df[f].to_numpy())
        flag = "  <- rises with size" if rho > 0.05 else ("  <- falls" if rho < -0.05 else "")
        print(f"  {f:15s}: rho = {rho:+.3f}{flag}")
    print("  (H4 needs DISAGREEMENT/contention to RISE with size)\n")

    # ---- B. do content features suppress upvotes at fixed size? ----
    print("=== B. OLS  y = log10(upvotes)  (standardized betas) ===")
    ls = np.log10(size)
    y = np.log10(up)
    r2_s, _ = ols_std(y, [ls], ["size"])
    Xf = [ls] + [df[f].to_numpy(float) for f in FEATS]
    r2_f, betas = ols_std(y, Xf, ["size"] + FEATS)
    print(f"  size only        : R2={r2_s:.3f}")
    print(f"  size + content   : R2={r2_f:.3f}  (delta {r2_f-r2_s:+.3f})")
    print(f"  std_beta[size]            = {betas['size']:+.3f}")
    for f in FEATS:
        print(f"  std_beta[{f:15s}] = {betas[f]:+.3f}")
    print("  (H4 needs disagreement std_beta < 0: contention suppresses upvotes)\n")

    # ---- C. split-beta by contention tercile ----
    print("=== C. fit_beta(upvotes vs size) split by content ===")
    b_full, _ = fit_beta(size, up)
    print(f"  full subset: beta = {b_full:.3f}\n")
    for split_name, key, lohi in [
        ("consensus (low=contentious)", df["consensus"].to_numpy(), ["contentious", "neutral", "consensual"]),
        ("disagree_frac", df["disagree_frac"].to_numpy(), ["low", "mid", "high"]),
        ("question_frac", df["question_frac"].to_numpy(), ["low", "mid", "high"]),
    ]:
        qs = np.quantile(key, [1/3, 2/3])
        masks = [key <= qs[0], (key > qs[0]) & (key <= qs[1]), key > qs[1]]
        print(f"  by {split_name}:")
        for lab, mk in zip(lohi, masks):
            b, nb = fit_beta(size[mk], up[mk])
            print(f"    {lab:12s} (n={mk.sum():>6,}): beta = {b:.3f}  [{nb} bins]")
        print()
    print("  (H4: consensual/low-disagreement threads scale closer to linear,\n"
          "   contentious/high-disagreement flatter. If beta ~equal -> H4 fails)")

    # ---- figure ----
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    # (a) feature vs size, log-binned means
    edges = np.logspace(0, np.log10(size.max()), 16)
    idx = np.digitize(size, edges)
    xs = [size[idx == b].mean() for b in range(1, 16) if (idx == b).sum() >= 20]
    for f, col in [("disagree_frac", "#d62728"), ("agree_frac", "#2ca02c"),
                   ("question_frac", "#1f77b4")]:
        ys = [df[f].to_numpy()[idx == b].mean() for b in range(1, 16) if (idx == b).sum() >= 20]
        ax[0].plot(xs, ys, "o-", label=f, color=col)
    ax[0].set(xscale="log", xlabel="discussion size (comment_count)",
              ylabel="mean feature", title="(a) content vs size")
    ax[0].legend(); ax[0].grid(alpha=.3)
    # (b) split beta bars
    cons = df["consensus"].to_numpy()
    qs = np.quantile(cons, [1/3, 2/3])
    groups = {"contentious": cons <= qs[0], "neutral": (cons > qs[0]) & (cons <= qs[1]),
              "consensual": cons > qs[1]}
    bs = [fit_beta(size[m], up[m])[0] for m in groups.values()]
    ax[1].bar(list(groups), bs, color=["#d62728", "#999999", "#2ca02c"])
    ax[1].axhline(b_full, ls="--", color="black", label=f"full {b_full:.2f}")
    ax[1].axhline(1.0, ls=":", color="grey", label="linear")
    ax[1].set(ylabel="beta (upvotes vs size)", title="(b) split-beta by consensus")
    ax[1].legend(); ax[1].grid(alpha=.3, axis="y")
    fig.tight_layout()
    os.makedirs(FIGDIR, exist_ok=True)
    out = os.path.join(FIGDIR, "h4_content.pdf")
    fig.savefig(out, bbox_inches="tight")
    print(f"\nFigure saved: {out}")


if __name__ == "__main__":
    main()

"""
H1 (net-score story) test for the Moltbook upvote-scaling follow-up.

Tests whether the sublinear upvote scaling is an artifact of looking at upvotes
alone: refit beta with net score (upvotes - downvotes) and with downvotes alone,
and report the downvote share. The upvote-scaling reproduction itself lives in the
upstream repo/analysis_scripts/; here upvote beta is kept only as the reference the
net-score comparison is made against.

Mirrors the paper's choices where possible:
  - Discussion size = posts.comment_count (total comments as reported by API).
  - Spam filter applied at the post level using stored comments
    (drop posts with <50% unique comment content or <20% unique authors, among posts with >=5 stored comments).
  - Data restricted to created_at <= 2026-02-08 (paper's cutoff).
  - beta fit via log-log linear regression on log-binned averages.
"""
import os
import sqlite3
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "moltbook_upload.db")
CUTOFF = "2026-02-09"  # exclusive upper bound -> includes through Feb 8

def load(con):
    posts = pd.read_sql_query(
        f"SELECT id, author_id, upvotes, downvotes, comment_count, created_at "
        f"FROM posts WHERE created_at < '{CUTOFF}'", con)
    return posts

def spam_post_ids(con):
    """Return set of post ids flagged as spam, per the paper's two criteria."""
    df = pd.read_sql_query(
        "SELECT post_id, content, author_id FROM comments", con)
    g = df.groupby("post_id")
    stats = g.agg(
        n=("content", "size"),
        uniq_content=("content", "nunique"),
        uniq_author=("author_id", "nunique"),
    )
    stats = stats[stats["n"] >= 5]
    frac_content = stats["uniq_content"] / stats["n"]
    frac_author = stats["uniq_author"] / stats["n"]
    flagged = stats[(frac_content < 0.5) | (frac_author < 0.2)].index
    return set(flagged)

def fit_beta(size, value, nbins=25):
    """Log-bin by size, average value per bin, fit log-log slope."""
    m = (size > 0) & (value > 0)
    s, v = size[m], value[m]
    edges = np.logspace(np.log10(s.min()), np.log10(s.max()), nbins + 1)
    idx = np.digitize(s, edges)
    xs, ys = [], []
    for b in range(1, nbins + 1):
        sel = idx == b
        if sel.sum() >= 5:
            xs.append(s[sel].mean())
            ys.append(v[sel].mean())
    xs, ys = np.log10(np.array(xs)), np.log10(np.array(ys))
    beta, intercept = np.polyfit(xs, ys, 1)
    return beta, len(xs)

def main():
    con = sqlite3.connect(DB)
    print("Loading posts...")
    posts = load(con)
    print(f"  posts (<= Feb 8): {len(posts):,}")

    print("Computing spam filter (this reads all comments)...")
    spam = spam_post_ids(con)
    print(f"  spam-flagged posts: {len(spam):,}")
    posts = posts[~posts["id"].isin(spam)].copy()
    print(f"  posts after spam filter: {len(posts):,}")

    size = posts["comment_count"].to_numpy(float)
    up = posts["upvotes"].to_numpy(float)
    down = posts["downvotes"].to_numpy(float)
    net = up - down

    print("\n=== Vote scaling vs discussion size (H1 net-score test) ===")
    b_up, n_up = fit_beta(size, up)
    print(f"  upvotes (reference): beta = {b_up:.3f}   [{n_up} bins]")

    b_net, n_net = fit_beta(size, net)
    print(f"  net (up-down)  : beta = {b_net:.3f}   [{n_net} bins]")

    b_dn, n_dn = fit_beta(size, np.clip(down, 0, None))
    print(f"  downvotes      : beta = {b_dn:.3f}   [{n_dn} bins]")

    print("\n=== Vote summary ===")
    print(f"  total upvotes={up.sum():,.0f}  downvotes={down.sum():,.0f}  "
          f"downvote share={down.sum()/(up.sum()+down.sum()):.3%}")
    con.close()

if __name__ == "__main__":
    main()

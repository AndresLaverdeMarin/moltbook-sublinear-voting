"""H3 review: is the young-age superlinearity in the matched-age beta a genuine
saturation signature, or a zero-inflation artifact of the paper binning keeping
zero-upvote posts (y >= 0)?

Rebuilds the exact h3_saturation.py cohort, then at each grid age compares the
matched-age beta computed three ways and inspects zero-inflation + the actual
per-bin table at young ages.
"""
import os
import sqlite3
import numpy as np
import pandas as pd

from paper_beta import bin_and_average, fit_power_law, fit_beta

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("MOLTBOOK_DB", os.path.join(HERE, "..", "moltbook_upload.db"))
START  = os.environ.get("MOLTBOOK_START", "1970-01-01")    # inclusive lower bound on created_at
CUTOFF = os.environ.get("MOLTBOOK_CUTOFF", "2026-02-09")   # exclusive upper bound (default: through Feb 8)
FIRST_AGE_MAX = 6.0
HORIZON = 72.0
GRID = np.array([2, 4, 6, 9, 12, 18, 24, 36, 48, 60, 72], float)


def spam_post_ids(con):
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
    """Old in-house behaviour: drop value==0 before the paper fit."""
    size = np.asarray(size, float); value = np.asarray(value, float)
    m = value > 0
    return fit_beta(size[m], value[m])


def beta_median(size, value, x_min=2, num_bins=30):
    """Paper bins, but fit the log-log slope of the per-bin MEDIAN (zeros kept)."""
    size = np.asarray(size, float); value = np.asarray(value, float)
    mask = (size > 0) & (value >= 0)
    size, value = size[mask], value[mask]
    if size.size < 10:
        return np.nan, 0
    edges = np.logspace(np.log10(size.min()), np.log10(size.max()), num_bins)
    cen, med = [], []
    for i in range(len(edges) - 1):
        m = (size >= edges[i]) & (size < edges[i + 1])
        if m.sum() >= 5:
            cen.append(np.sqrt(edges[i] * edges[i + 1]))
            med.append(np.median(value[m]))
    cen, med = np.array(cen), np.array(med)
    keep = (cen >= x_min) & (med > 0)          # median==0 bins can't be logged
    if keep.sum() < 3:
        return np.nan, int(keep.sum())
    e, _ = fit_power_law(cen[keep], med[keep])
    return e, int(keep.sum())


def beta_minpop(size, value, min_n=100, x_min=2, num_bins=30):
    """Paper mean-bins, but fit only over bins with >= min_n posts (drop sparse tail)."""
    size = np.asarray(size, float); value = np.asarray(value, float)
    mask = (size > 0) & (value >= 0)
    size, value = size[mask], value[mask]
    if size.size < 10:
        return np.nan, 0
    edges = np.logspace(np.log10(size.min()), np.log10(size.max()), num_bins)
    cen, mean = [], []
    for i in range(len(edges) - 1):
        m = (size >= edges[i]) & (size < edges[i + 1])
        if m.sum() >= min_n:
            cen.append(np.sqrt(edges[i] * edges[i + 1]))
            mean.append(np.mean(value[m]))
    cen, mean = np.array(cen), np.array(mean)
    keep = (cen >= x_min) & (mean > 0)
    if keep.sum() < 3:
        return np.nan, int(keep.sum())
    e, _ = fit_power_law(cen[keep], mean[keep])
    return e, int(keep.sum())


def build_cohort_curves():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA cache_size=-4000000")    # ~4 GB page cache
    con.execute("PRAGMA mmap_size=30000000000")  # 30 GB memory-mapped reads
    con.execute("PRAGMA temp_store=FILE")        # spill GROUP BY sort to SQLITE_TMPDIR (disk)
    print("Loading posts + snapshot coverage...")
    posts = pd.read_sql_query(
        f"SELECT id, created_at FROM posts "
        f"WHERE created_at >= '{START}' AND created_at < '{CUTOFF}'", con)
    agg = pd.read_sql_query(
        "SELECT post_id, COUNT(*) n, MIN(recorded_at) first_rec, "
        "MAX(recorded_at) last_rec FROM post_snapshots NOT INDEXED GROUP BY post_id", con)
    print("Computing spam filter (reads all comments)...")
    spam = spam_post_ids(con)

    cov = posts.merge(agg, left_on="id", right_on="post_id", how="inner")
    cov = cov[~cov["id"].isin(spam)].copy()
    for c in ["created_at", "first_rec", "last_rec"]:
        cov[c] = pd.to_datetime(cov[c], utc=True)
    cov["first_age"] = (cov["first_rec"] - cov["created_at"]).dt.total_seconds() / 3600
    cov["last_age"] = (cov["last_rec"] - cov["created_at"]).dt.total_seconds() / 3600
    cohort = cov[(cov["first_age"] <= FIRST_AGE_MAX) & (cov["last_age"] >= HORIZON)].copy()
    print(f"  cohort posts: {len(cohort):,}")
    cohort_ids = set(cohort["id"])

    # per-post early-life snapshot bound = creation date + 7 days (day-granular recorded_at, so a
    # lexicographic string compare == chronological). Keeps the 72h-grid curves identical for any
    # created_at window while dropping each post's later snapshots.
    cutdate = (cohort["created_at"] + pd.Timedelta(days=7)).dt.strftime("%Y-%m-%d")
    con.execute("CREATE TEMP TABLE cohort(pid TEXT PRIMARY KEY, cutdate TEXT)")
    con.executemany("INSERT INTO cohort VALUES (?,?)", list(zip(cohort["id"], cutdate)))
    snaps = pd.read_sql_query(
        "SELECT s.post_id, s.upvotes, s.comment_count, s.recorded_at "
        "FROM post_snapshots s JOIN cohort c ON s.post_id = c.pid "
        "WHERE s.recorded_at <= c.cutdate", con)
    con.close()

    snaps["recorded_at"] = pd.to_datetime(snaps["recorded_at"], utc=True)
    created = cohort.set_index("id")["created_at"]
    snaps = snaps.join(created, on="post_id")
    snaps["age"] = (snaps["recorded_at"] - snaps["created_at"]).dt.total_seconds() / 3600
    snaps = snaps[snaps["age"] >= 0].sort_values(["post_id", "age"])

    print("Interpolating per-post curves...")
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
    print(f"  posts with curves: {len(U):,}\n")
    return U, C


def main():
    U, C = build_cohort_curves()

    print("=== matched-age beta, several estimators + zero-inflation ===")
    print(f"  {'age':>4} {'paper(y>=0)':>11} {'dropzero':>9} {'median':>8} "
          f"{'n>=100bins':>10} {'fracU=0':>8} {'medU':>6} {'medC':>6}")
    for t in GRID:
        c, u = C[t].to_numpy(), U[t].to_numpy()
        b_paper, _ = fit_beta(c, u)
        b_drop, _ = beta_dropzero(c, u)
        b_med, _ = beta_median(c, u)
        b_pop, npop = beta_minpop(c, u)
        frac0 = float(np.mean(u < 1.0))
        print(f"  {t:4.0f} {b_paper:11.3f} {b_drop:9.3f} {b_med:8.3f} "
              f"{b_pop:6.3f}[{npop:2d}] {frac0:8.1%} {np.median(u):6.1f} {np.median(c):6.1f}")

    # direct look at the per-bin table at two young ages and one mature age
    for t in (2.0, 12.0, 72.0):
        c, u = C[t].to_numpy(), U[t].to_numpy()
        m = (c > 0) & (u >= 0)
        c, u = c[m], u[m]
        edges = np.logspace(np.log10(c.min()), np.log10(c.max()), 30)
        print(f"\n=== per-bin table at age {t:.0f}h "
              f"(comment-count bin -> mean/median upvotes, n, frac upvotes=0) ===")
        print(f"  {'binC':>7} {'n':>7} {'meanU':>7} {'medU':>6} {'frac0':>7}")
        for i in range(len(edges) - 1):
            sel = (c >= edges[i]) & (c < edges[i + 1])
            if sel.sum() >= 5:
                cen = np.sqrt(edges[i] * edges[i + 1])
                print(f"  {cen:7.1f} {sel.sum():7d} {u[sel].mean():7.2f} "
                      f"{np.median(u[sel]):6.1f} {np.mean(u[sel] < 1):7.1%}")


if __name__ == "__main__":
    main()

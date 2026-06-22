# Moltbook sublinear voting — a mechanistic follow-up

A sequence of statistical experiments asking **why average upvotes scale *sublinearly* with discussion
size on Moltbook**, an all-AI-agent social platform. This is a follow-up to:

> Giordano De Marzo & David Garcia, *Collective Behavior of AI Agents: the Case of Moltbook*,
> arXiv 2602.09270v1 (Feb 2026).

## The anomaly

The paper's one genuine human-vs-AI deviation is that **average upvotes scale sublinearly** with
discussion size — exponent **β ≈ 0.78** — whereas on human Reddit the same quantity scales roughly
linearly (β ≈ 1). Crucially, **direct replies on the same threads still scale linearly** (β ≈ 1). So
the anomaly is specific to *voting*, not to conversational threading.

The real question is therefore not "why are upvotes sublinear?" but:

> **Why does *voting* decouple from *replying* as a discussion grows?**

The paper leaves this a black box ("AI agents may be less inclined to upvote") and never examines the
four dataset dimensions that could explain it: downvotes, the author social graph, vote accumulation
over time, and post/comment text. This study tests one candidate mechanism per dimension.

## Hypotheses and verdicts

Each hypothesis maps 1:1 to a dimension the paper ignored. **All four are falsified** within the
dataset — the sublinearity is a robust baseline property of AI-agent voting itself.

| H | Dimension | Mechanism tested | Verdict |
|---|---|---|---|
| **H1** net-score | downvotes | large threads attract more downvotes; sublinearity is an upvote-only artifact | **FALSIFIED** — net β = upvote β; downvotes are only 1.24% of votes |
| **H2** authority | karma / follow graph (followers, following, ratio) + X owner standing | votes track author standing, not discussion size | **FALSIFIED** — no standing signal (inbound, outbound, ratio, or off-platform X) absorbs the size effect; explains ≤~10% of upvote variance |
| **H3** saturation | vote timing | upvotes plateau early while comments keep accruing | **FALSIFIED** — saturation asymmetry is tiny (both ~97% complete by 24h); the matched-age "superlinear-early" reading was a sparse-bin/viral mean artifact (see `h3_review.py`) |
| **H4** content | comment text | contentious threads grow via replies but earn fewer upvotes | **FALSIFIED** — contention doesn't suppress upvotes; consensual threads are if anything *flatter* |

### Headline numbers

- **Baseline reproduced.** Upvotes vs size β ≈ **0.755** (paper's ≈ 0.78) — clearly sublinear; matches the
  authors' own code run on this dataset, the residual gap being the Feb-8 window plus log-binned OLS here
  vs. the paper's MLE fit.
- **H1.** Net (up − down) β = 0.743 vs upvote β = 0.755; downvotes scale ~linearly (β = 1.03) but are only
  **1.24%** of all votes. Sublinearity is a property of *positive* voting, not hidden contention.
- **H2.** Spearman ρ(upvotes, size) = 0.50 vs ρ(upvotes, karma/followers) = 0.13–0.15; authority explains
  ~3% of upvote variance and the ~0.62–0.76 sublinearity survives within every authority tercile.
- **H3.** Both upvotes and comments are ~97% complete within 24h (<4% accrues after); under robust binning
  the matched-age β is sublinear within hours. The dramatic "superlinear-early" mean reading was a
  sparse-bin/viral artifact — the sublinearity is a final-state property, not a timing effect.
- **H4.** Disagreement *and* agreement both rise with size (net consensus flat, ρ = +0.03); disagreement's
  effect on upvotes is positive, not negative; every content stratum stays sublinear (full subset β = 0.692).

### Refinements (not new mechanisms)

- **H4b — question / discussion-bait.** The decoupling concentrates in Q&A threads: as comment
  question-rate rises, β(upvotes) collapses **0.83 → 0.34** while β(direct replies) stays ~1, so the
  voting/replying gap widens 0.18 → 0.55. The locus is the *discussion*, not the OP (β identical
  whether or not the OP asks a question). A partial moderator — even the lowest-question threads are
  sublinear (β ≈ 0.83 < 1).
- **E1 — tree-structure tail upturn.** The up-turn at the high-width end of the paper's Figure 4a is
  an **artifact**, not a regime change: it appears in the *mean* but not the *median*, and is driven by
  small-n + near-cap tree incompleteness. The structure exponent (≈ −0.96) is robust to crawl window
  and post maturity — confirming crawl-time/completeness artifacts don't contaminate size-dependent
  metrics (including the baseline β).

## Robustness across datasets and time windows

The baseline sublinearity and the H1–H4 verdicts were re-checked on three slices of the data:

- **upload (Feb-9)** — the paper-snapshot DB (`moltbook_upload.db`), where Feb posts were crawled
  ~0–2 days old;
- **total (Feb-9)** — the full ~53 GB crawl restricted to the paper window: the *same* posts observed at
  full maturity;
- **window (≥Feb-27)** — the full crawl excluding the first month of collection (a later, disjoint
  temporal slice; ~1 M posts).

| H | metric | upload | total (Feb-9) | **window (≥Feb-27)** |
|---|---|---|---|---|
| **H1** | posts (after spam) | 379,878 | 379,852 | **1,006,389** |
| | β up / net / total / down | 0.755 / .743 / .766 / 1.032 | 0.873 / .847 / .893 / 1.240 | **0.844 / .844 / .844 / 0.799** |
| | upvotes / downvotes / share | 888,784 / 11,114 / 1.24% | 927,947 / 11,242 / 1.20% | **3,058,790 / 11,736 / 0.38%** |
| **H1b** | posts downvoted (%) / top-1% conc. | 2.01% / 68.7% | 2.02% / 68.6% | **1.15% / 89.6%** |
| | keep-0 = P(>0) × intensity | 1.032=.532+.460 | 1.240=.538+.571 | **0.799=.693+.089** |
| | max downvotes on a post | 655 | 655 | **8** |
| **H2** | posts used | 252,946 | 253,595 | **411,103** |
| | ρ(up,size) / ρ(up,karma) | 0.499 / 0.128 | 0.501 / 0.133 | **0.397 / 0.187** |
| | authority R² / size coef M1→M3 | 0.028 / +.424→+.427 | 0.029 / +.428→+.430 | **0.037 / +.506→+.507** |
| | β within karma terciles (lo/mid/hi) | 0.67/0.75/0.76 | 0.73/0.84/0.83 | **0.93/0.87/0.79** |
| **H3** | cohort posts (usable curves) | 68,429 | 164,871 | **632,242 (474,914)** |
| | % of final by 24 h (up / com) | 98.1 / 96.3 | 98.8 / 98.2 | **99.8 / 99.0** |
| | matched-age β, **mean** (2 h → 72 h) | 2.45 → 0.77 | 2.41 → 0.93 | **0.92 → 0.86** (no spike) |
| | matched-age β, **median** (2 h → 72 h) | ~0.98 → 0.69 | ~0.91 → 0.93 | **~0.98 → 0.91** |
| **H4** | posts w/ features | 247,115 | 247,803 | **408,375** |
| | disagree ρ↑size / disagree OLS β | +0.315 / +0.029 | +0.316 / +0.029 | **+0.351 / +0.020** |
| | OLS R² size → size+content | 0.250→0.261 | 0.253→0.263 | **0.194→0.223** |
| | β split: consensual / contentious | 0.605 / 0.749 | 0.637 / 0.741 | **0.908 / 0.913** |
| | β split: question lo / mid / hi | 0.802/.706/.497 | 0.786/.636/.538 | **0.374/.902/.889** |
| **H4b** | log(size)×qfrac interaction | −0.045 | −0.045 | **+0.122** |
| | β_up across q-rate (lo → hi decile) | 0.826 → 0.335 | 0.824 → 0.337 | **0.910 → 0.295** |
| | upvotes/comment by q-rate (lo → hi) | −5% | −5% | **+34%** |
| | β_up: OP-question vs not | 0.602 / 0.626 | 0.634 / 0.660 | **0.870 / 0.973** |
| **E1** | posts <100 / w/ tree metrics | 351,475 / 138,216 | 911,868 / 236,613 | **500,393 / 87,107** |
| | tree exponent | −0.959 | −0.949 | **−0.939** |
| | tail upturn: mean / median-trend | +0.022 / −0.090 | +0.017 / −0.085 | **+0.017 / −0.100** |
| | maturity exponent: young / mature | −0.982 / −0.945 | −0.964 / −0.936 | **−0.959 / −0.930** |

**Takeaway:** β rises with observation maturity (0.755 → 0.873 on the *same* posts) but stays sublinear,
and all four falsifications hold on every slice. The only finding that does **not** replicate on the
later window is the H4b question-bait refinement (its continuous interaction flips sign), suggesting it
was specific to the early/paper period.

### June-2026 crawl (`moltbook_jun9.db`, 2.5 M posts, Jan 28 – Jun 9)

A fresh, larger crawl re-run two ways: **all data**, and **excluding the first month** of collection.
Same conclusions as every earlier slice.

| | all data | excl. first month |
|---|---|---|
| posts (after spam) | 2,508,884 | 1,588,356 |
| baseline β (upvotes vs size) | **0.784** | **0.809** |
| H1 — net β / downvote share | 0.783 / 0.42% | 0.809 / 0.36% |
| H2 — authority share of votes / β across terciles | ~5% / 0.74–0.86 | ~10% / 0.74–0.96 |
| H3 — β at matched age (flat across age) | ~0.70 | ~0.70 (same cohort) |
| H4 — does disagreement lower upvotes? | no (+0.01) | no (+0.01) |
| H4b — β(upvotes), few → many questions | 0.82 → 0.48 | 0.84 → 0.74 |
| E1 — tree-shape exponent | −0.87 | −0.86 |

**Result:** upvotes still grow sublinearly with discussion size (β below 1). Dropping the launch month
nudges β up (0.78 → 0.81) because later posts were caught more mature, but it stays sublinear. All four
hypotheses remain falsified; the question-bait refinement (H4b) survives but is weaker once the first
month is excluded. H3 is unchanged between the two windows because the snapshot history only covers the
crawl's last ~6 weeks, so the early-life cohort it needs is the same either way.

**Extended H2 (this crawl).** Moltbook agents can follow each other and can link an X/Twitter account, so
"standing" was widened from karma/followers to the whole picture: people who *follow* the agent (inbound),
people the agent *follows* (outbound), the ratio of the two, and the owner's real X follower count and
verified badge. Upvotes track **none** of them — the only thing votes follow is discussion size, and
controlling for every standing signal leaves that size effect unchanged. The X data barely exists anyway
(only ~17% of agents link an account), so it's reported for completeness, not leaned on. H2 stays falsified
in every direction of the follow graph.

## Scripts

| Script | What it tests | Figure |
|---|---|---|
| `h1_net_score.py` | H1 net-score / downvote decomposition (also the baseline β) | — |
| `h1b_downvotes.py` | H1b within-Moltbook downvote characterization (prevalence, scaling decomposition, contention) | `figures/h1b_downvotes.pdf` |
| `h2_authority.py` | H2 authority (karma / followers) | — |
| `h3_saturation.py` | H3 vote-vs-comment accumulation from snapshots | `figures/h3_saturation.pdf` |
| `h4_content.py` | H4 content / contention from comment text | `figures/h4_content.pdf` |
| `h4b_question_bait.py` | H4b question / discussion-bait refinement | `figures/h4b_question_bait.pdf` |
| `e1_tree_structure.py` | E1 tree-structure tail upturn & crawl-window sensitivity | `figures/e1_tree_structure.pdf` |
| `h3_review.py` | H3 robustness check (matched-age β: mean vs median vs drop-zero) | — |
| `paper_beta.py` | the authors' β-fit code (`bin_and_average` + `fit_power_law`), used by all scripts | — |

## Methodology (kept comparable to the paper)

- **Discussion size** = `posts.comment_count` (the API's total), not the count of stored comments.
- **Spam filter** (post level, the authors' exact `get_spam_post_ids`): drop posts with <50% unique comment
  content OR <20% unique author among posts with ≥5 stored comments; **also** drop high-count posts
  (`comment_count > 200`) that have no stored comments.
- **β fit**: log-bin by size (30 bins), average the metric per bin, fit the log-log slope over bins ≥2
  (≥5 points per bin) — the authors' `bin_and_average` + `fit_power_law`, copied verbatim into
  `paper_beta.py`. Note the mean-per-bin is outlier-sensitive in sparse tail bins (see H3/E1); prefer the
  median there.
- **Paper snapshot**: filter `created_at < '2026-02-09'` (through Feb 8) to reproduce paper numbers.
- **Tree completeness**: comment trees are complete only for posts with <100 comments; per-comment
  text/vote analyses are restricted to that subset (post-level vote analyses are unaffected).
- **Time-dependent claims (H3)** use the `*_snapshots` tables aligned by post age, since vote columns
  on `posts`/`comments` are crawl-time snapshots, not final tallies.
- **Author-standing fields (H2).** The follow graph is *directional*, so "authority" is several distinct
  signals on `agents`: `karma`; `follower_count` (inbound — how many follow the agent); `following_count`
  (outbound — how many it follows); and the influencer ratio `follower_count/(following_count+1)`. These are
  all **Moltbook-native**. Separately, `x_follower_count` / `x_following_count` / `x_verified` (and
  `x_handle`/`x_name`/`x_bio`) are the **original X/Twitter values of the agent's *owner***, copied from X at
  crawl time via the API's `owner {…}` object — *not* Moltbook-internal counts. They exist only for agents
  whose owner has linked an X account: gated by `is_claimed`, which is true for just **~17%** of agents (the
  rest are `0` by schema default, i.e. *unknown*, not genuinely zero). On the H2 used subset the X fields are
  ~80% zero and only ~0.17% verified, so they are reported **descriptively** (block E of `h2_authority.py`),
  not fed into the OLS/terciles. H2 is falsified against every one of these signals — inbound, outbound,
  ratio, and off-platform X — so the voting/replying decoupling is authority-independent in every direction
  of the graph.

## Setup & running

`uv` project, Python ≥ 3.12. Dependencies: numpy, pandas, matplotlib, scipy, powerlaw.

```bash
uv sync                                  # create .venv and install deps
uv run python h3_saturation.py           # run an experiment
```

The scripts read the dataset from `../moltbook_upload.db` — a ~5.1 GB SQLite snapshot of the Moltbook
crawl (HuggingFace `giordano-dm/moltbook-crawl`), not committed here. Figures are written to
`figures/` as PDF.

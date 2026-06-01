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
| **H2** authority | karma / followers | votes track author standing, not discussion size | **FALSIFIED** — authority explains ~3% of upvote variance; doesn't absorb the size effect |
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

See [`../RESULTS.md`](../RESULTS.md) for the full run-by-run log and [`../IDEA.md`](../IDEA.md) for the
research gap and analysis plan.

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

## Setup & running

`uv` project, Python ≥ 3.12. Dependencies: numpy, pandas, matplotlib, scipy, powerlaw.

```bash
uv sync                                  # create .venv and install deps
uv run python h3_saturation.py           # run an experiment
```

The scripts read the dataset from `../moltbook_upload.db` — a ~5.1 GB SQLite snapshot of the Moltbook
crawl (HuggingFace `giordano-dm/moltbook-crawl`), not committed here. Figures are written to
`figures/` as PDF.

# Reddit & Moltbook — terminology and how they work

A companion key to the two figures (`reddit_structure.pdf`, `moltbook_structure.pdf`).
Both platforms are **Reddit-style discussion forums** with the *same* architecture; the headline
difference is *who the participants are* — **humans** on Reddit, **autonomous AI agents (LLMs)** on
Moltbook. This file defines the main terms each platform uses and walks through how a piece of content
moves through the system.

---

## At a glance — the same concepts, two vocabularies

| Concept | Reddit term | Moltbook term | Where it is in the figure |
|---|---|---|---|
| Participant / account | **user** (a person) | **AI agent** (an autonomous LLM) | actor icons, top-left |
| Topical community | **subreddit** — `r/name` | **submolt** — `m/name` | the central rounded card |
| A piece of content | **post** (submission) | **post** | the “post” card inside the community |
| Replies / discussion | **comment** (threaded) | **comment** (threaded) | the “comments” tree under the post |
| Approval signals | **upvote** ▲ (+1) / **downvote** ▼ (−1) | **upvote** ▲ / **downvote** ▼ | green/red triangles |
| Popularity of an item | **score** = upvotes − downvotes | **score** | the ▲ **score** chip on the post |
| Reputation of an account | **karma** (accumulated score) | **karma** (+ **followers**) | — |
| The ranked surface | **feed** / **front page** | **feed** | the “feed — ranked by score” panel |
| Social connections | **subscribe** → a community | **subscribe/join** → a submolt · **follow** → an agent | the social-graph panel |
| Governance | **moderators**, **rules** | **moderators**, **rules** | the community card subtitle |

The vote glyphs (▲ upvote, ▼ downvote), the **score** chip, the actor icon, the action arrows, and the
**reply** connector are spelled out in the **key** (legend) at the bottom of each figure.

---

## How Reddit works

- **User** — a registered, usually pseudonymous *human* account. Acts through the web/app: reads,
  posts, comments, and votes.
- **Subreddit (`r/topic`)** — a topical community a user can **subscribe** to. Each subreddit is run by
  volunteer **moderators** and has its own **rules**.
- **Post** — a submission (a title plus self-text, a link, or an image) made *into* a subreddit.
- **Comment** — a reply attached to a post. A comment can reply to the post *or to another comment*, so
  comments form a **threaded discussion tree** (the “reply-to” relation; replies nest under their
  parent).
- **Upvote / Downvote** — every user can cast **+1** or **−1** on *both posts and comments*.
- **Score & karma** — an item’s **score** is `upvotes − downvotes`. An account’s **karma** is the
  reputation it builds up from the scores of its posts and comments.
- **Feed / front page & ranking** — posts are ordered into feeds (e.g. *Hot · Top · New ·
  Controversial*) by their **score** and **age**. A user’s **front page** is the aggregated feed of the
  subreddits they subscribe to.

**The flow:** a user **posts** into a subreddit → other users **upvote/downvote** the post and **reply**
with threaded comments → the resulting **score** ranks the post in everyone’s **feed**. The social graph
is **community-centric**: people follow *topics* (subscribe to subreddits), not each other.

---

## How Moltbook works

- **AI agent** — an *autonomous LLM* account; there are **no human users**. Agents act **through the
  API**, holding a profile with **karma** and **followers**.
- **Submolt (`m/topic`)** — Moltbook’s name for a topical community (the analogue of a subreddit), with
  **moderators** and **rules**; agents **join** submolts.
- **Post** — content an agent submits to a submolt.
- **Comment** — a threaded reply (tracked by a `parent_id` and a `depth`), exactly like Reddit’s
  reply-to tree: replies nest under their parent.
- **Upvote / Downvote** — agents cast **+1 / −1** on posts and comments.
- **Score & karma** — an item’s **score** is `upvotes − downvotes`; an agent’s **karma** is its
  accumulated reputation.
- **Subscribe (join) & follow** — Moltbook has *two* social mechanisms, used together. Agents
  **subscribe to** (join) **submolts** — topic communities, exactly like Reddit — *and* can **follow**
  other **agents** (a Twitter/X-style account graph; every agent profile carries a `follower_count` and a
  `following_count`). The personalised home feed is built from **subscribed submolts + followed agents**.
  Agents do **not** follow individual threads/posts.
- **Feed & ranking** — posts are ranked by **score** and **age** into the agent’s feed.

**The flow:** an agent **posts** into a submolt → other agents **upvote/downvote** it and **reply** with
threaded comments → the **score** ranks the post in the **feed**. Discovery is mainly **community-centric**
(subscribing to submolts), with agent-to-agent **following** as an additional Twitter-like layer.

---

## Are the two comparable?

**Yes — structurally they are the same kind of platform.** Both pair the same primitives:
accounts → communities → posts → threaded comments → up/down votes → score/karma → a score-ranked feed.
That shared skeleton is why the two figures use an identical layout.

Two genuine differences in *terminology and structure* (not behaviour):

1. **The participants.** Reddit is populated by **humans**; Moltbook entirely by **autonomous AI
   agents**. This is the defining distinction — it is the same forum design driven by a different kind
   of actor.
2. **The social graph.** Reddit is **community-centric**: users *subscribe to subreddits* — they follow
   *communities, not people*. Moltbook is **also** community-centric (agents subscribe to submolts) but it
   *adds* a Twitter/X-style **account follow graph** (agents follow agents), so an agent's reputation shows
   both **karma** and a **follower count**, and the home feed mixes *subscribed submolts + followed agents*.
   (The De Marzo & Garcia paper analyses only the community side and frames discovery as community browsing
   *"rather than social graph propagation"*, so following exists on the platform but is secondary to the
   study.)

So the vocabularies map almost one-to-one (`subreddit ↔ submolt`, `user ↔ agent`, `r/ ↔ m/`), which is
exactly what makes the two platforms directly comparable.

---

## Sources

- **Platform API & docs.** Moltbook exposes both mechanisms: `POST /agents/:id/follow` (follow an agent)
  and `POST /submolts/:name/subscribe` (subscribe to a community), and the home feed `/feed/home` is
  composed of *subscribed submolts + followed agents* — Moltbook API guide,
  <https://apidog.com/blog/moltbook-api-ai-agents/>. Overviews:
  <https://www.datacamp.com/tutorial/moltbook-how-to-get-started> ("agents can follow other agents") ·
  <https://www.digitalocean.com/resources/articles/what-is-moltbook>.
- **Authors' crawler & schema** (`repo/`). Agent profiles carry `follower_count` and `following_count`
  (`repo/README.md`, `repo/maintain_db_v3.py`, snapshotted in `agent_snapshots`); submolts carry
  `subscriber_count` (`submolts`, `submolt_snapshots`).
- **Paper.** De Marzo & Garcia, *Collective Behavior of AI Agents: the Case of Moltbook* (arXiv:2602.09270):
  agents *"subscribe to topic-based communities (called submolts)"* (p.1); content discovery occurs
  *"through community browsing and algorithmic ranking rather than social graph propagation"* (p.6). The
  paper does not analyse the agent-follow graph.

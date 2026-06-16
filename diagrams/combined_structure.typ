// Combined figure: Moltbook (left) and Reddit (right) side by side, one page.
// Both panels come from the shared interaction_fig.typ template, so they are a
// matched pair.
#import "common.typ": pal, human, agent
#import "interaction_fig.typ": interaction_diagram
#set page(width: auto, height: auto, margin: 8mm, fill: white)
#set text(font: "Carlito", size: 9pt, fill: pal.ink)

#let moltbook = interaction_diagram(
  accent: pal.molt, light: pal.moltLt, prefix: "m/", actorfn: agent,
  actor_label: "AI agents", unit_label: "agent",
  community_action: "join", panel_title: "subscribe + follow", social_mode: "accounts",
)
#let reddit = interaction_diagram(
  accent: pal.reddit, light: pal.redditLt, prefix: "r/", actorfn: human,
  actor_label: "users", unit_label: "user",
  community_action: "subscribe", panel_title: "subscribe", social_mode: "communities",
)

#grid(
  columns: (auto, auto),
  column-gutter: 1.4cm,
  align: top,
  moltbook, reddit,
)

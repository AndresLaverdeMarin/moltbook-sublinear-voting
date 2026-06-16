// Reddit — "how members interact" figure.
// Thin wrapper: the shared layout lives in interaction_fig.typ; this file only
// supplies the Reddit parameters. Keeps the figure a pixel-matched pair with
// moltbook_structure.typ (same layout, different params).
#import "common.typ": pal, human, agent
#import "interaction_fig.typ": interaction_diagram
#set page(width: auto, height: auto, margin: 6mm, fill: white)
#set text(font: "Carlito", size: 9pt, fill: pal.ink)

#interaction_diagram(
  accent: pal.reddit,
  light: pal.redditLt,
  prefix: "r/",
  actorfn: human,
  actor_label: "users",
  unit_label: "user",
  community_action: "subscribe",
  panel_title: "subscribe",
  social_mode: "communities",
)

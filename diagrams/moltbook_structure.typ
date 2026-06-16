// Moltbook — "how members interact" figure.
// Thin wrapper: the shared layout lives in interaction_fig.typ; this file only
// supplies the Moltbook parameters. Keeps the figure a pixel-matched pair with
// reddit_structure.typ (same layout, different params).
#import "common.typ": pal, human, agent
#import "interaction_fig.typ": interaction_diagram
#set page(width: auto, height: auto, margin: 6mm, fill: white)
#set text(font: "Carlito", size: 9pt, fill: pal.ink)

#interaction_diagram(
  accent: pal.molt,
  light: pal.moltLt,
  prefix: "m/",
  actorfn: agent,
  actor_label: "AI agents",
  unit_label: "agent",
  community_action: "join",
  panel_title: "subscribe + follow",
  social_mode: "accounts",
)

// Shared "how members interact" interaction diagram.
// Single source of truth for the matched Reddit / Moltbook pair.
// reddit_structure.typ and moltbook_structure.typ are THIN wrappers that import
// this function and call it with their parameters, guaranteeing the two figures
// stay a pixel-matched pair.
//
// common.typ supplies the helpers only (read-only); this module owns the layout.
#import "common.typ": pal, human, agent, tri, card, arr, lbl
#import "@preview/cetz:0.3.4"

#let interaction_diagram(
  accent: pal.reddit,
  light: pal.redditLt,
  prefix: "r/",
  actorfn: human,                // human (people) | agent (AI robots)
  actor_label: "users",
  unit_label: "user",
  community_action: "subscribe", // pill on the community card
  panel_title: "subscribe",      // social-graph panel title
  social_mode: "communities",    // "communities" (user->community) | "accounts" (agent->agent)
) = {
  cetz.canvas(length: 1cm, {
    import cetz.draw: *

    let dotsk = (paint: pal.sub, dash: "dotted", thickness: 0.95pt)
    let act(p, s: 1.0) = actorfn(p, c: accent, s: s)

    let scorechip(x, y, n) = {
      card((x, y), 1.1, 0.46, bg: light, sk: 0.9pt + accent, radius: 0.12)
      tri((x + 0.27, y + 0.23), dir: "up", c: pal.up, s: 0.085)
      lbl((x + 0.72, y + 0.23), n, size: 8.5pt, wt: "bold", col: pal.ink)
    }
    let crow(x, y, w) = {
      card((x, y), w, 0.42, bg: white, sk: 0.8pt + pal.edge, radius: 0.07)
      act((x + 0.21, y + 0.21), s: 0.4)
      line((x + 0.44, y + 0.21), (x + w - 0.66, y + 0.21), stroke: dotsk)
      tri((x + w - 0.46, y + 0.29), dir: "up",   c: pal.up,   s: 0.05)
      tri((x + w - 0.46, y + 0.13), dir: "down", c: pal.down, s: 0.05)
      lbl((x + w - 0.22, y + 0.21), [4], size: 6.5pt, col: pal.sub)
    }
    let elbow(x0, y0, y1, x1) = {
      line((x0, y0), (x0, y1), stroke: 0.9pt + accent.lighten(15%))
      line((x0, y1), (x1, y1), stroke: 0.9pt + accent.lighten(15%))
    }
    let feedrow(x, y, w, s) = {
      line((x - 0.18, y), (x - 0.06, y), stroke: 0.8pt + pal.edge)
      line((x, y), (x + w, y), stroke: dotsk)
      tri((x + w + 0.2, y + 0.02), dir: "up", c: pal.up, s: 0.055)
      lbl((x + w + 0.4, y), s, size: 6.5pt, col: pal.sub, anch: "west")
    }

    // ---- header band REMOVED (no title / no subtitle) -------------------

    // ---- (A) ACTORS — actor column pulled toward the community card -----
    act((2.0, 8.5), s: 0.85); act((2.55, 8.45), s: 1.0); act((3.1, 8.5), s: 0.85)
    lbl((2.55, 7.78), actor_label, wt: "bold", size: 10pt, col: accent)

    act((2.55, 6.7), s: 0.85)
    lbl((2.55, 6.15), "author", size: 7pt, col: pal.sub)
    // post arrow: verb label sits clear ABOVE the arrow line (no glyph crossed)
    arr((3.2, 6.95), (3.95, 7.25), sk: 1.0pt + pal.edge, sc: 0.42)
    lbl((3.5, 7.52), "post", size: 7pt, col: pal.sub)

    // ---- (B) POST inside a COMMUNITY container --------------------------
    card((3.9, 3.95), 5.6, 4.7, bg: white, sk: 1.3pt + accent, radius: 0.16)
    lbl((4.25, 8.25), prefix + "gaming", col: accent, wt: "bold", size: 12.5pt, anch: "west")
    lbl((4.25, 7.9), "community", size: 7.5pt, col: pal.sub, anch: "west")
    // community action pill
    card((8.1, 8.05), 1.1, 0.42, bg: light, sk: 0.8pt + accent, radius: 0.21)
    lbl((8.65, 8.26), community_action, size: 6.5pt, col: accent, wt: "bold")

    card((4.25, 6.9), 4.9, 0.85, bg: light, sk: 1.0pt + accent, radius: 0.1)
    lbl((4.5, 7.5), "post", wt: "bold", size: 9.5pt, anch: "west")
    line((4.5, 7.18), (6.35, 7.18), stroke: dotsk)
    scorechip(7.85, 7.1, "128")

    // ---- (C) VOTING — voter cluster sits above the score chip; the arrow
    //          drops straight down onto the chip top, crossing no text -----
    act((7.7, 9.05), s: 0.62); act((8.2, 9.05), s: 0.62)
    tri((7.7, 8.78), dir: "up",   c: pal.up,   s: 0.07)
    tri((8.2, 8.78), dir: "down", c: pal.down, s: 0.07)
    arr((7.95, 8.62), (7.95, 7.52), sk: 0.9pt + pal.edge, sc: 0.42)
    lbl((7.45, 8.1), "vote", size: 7pt, col: pal.sub, anch: "east")

    // ---- (D) COMMENT / REPLY — threaded tree under the post -------------
    lbl((4.25, 6.62), "comments", size: 8pt, wt: "bold", col: pal.sub, anch: "west")
    elbow(4.45, 6.42, 5.97, 4.65)
    crow(4.65, 5.76, 4.1)
    elbow(5.0, 5.76, 5.27, 5.2)
    crow(5.2, 5.14, 3.55)
    elbow(5.55, 5.14, 4.65, 5.75)
    crow(5.75, 4.53, 3.0)
    elbow(4.45, 4.53, 4.3, 4.65)
    crow(4.65, 4.09, 4.1)
    // reply actor: NO actor-type label (the top cluster names it once); the
    // verb label sits clear ABOVE the arrow line.
    act((3.05, 5.1), s: 0.7)
    arr((3.45, 5.25), (4.55, 5.5), sk: 0.9pt + pal.edge, sc: 0.42)
    lbl((3.4, 5.72), "reply", size: 7pt, col: pal.sub)

    // ---- (E) FEED / RANKING — panel pulled toward the community card ----
    card((10.1, 5.55), 5.65, 3.1, bg: pal.callout, sk: 0.9pt + pal.edge, radius: 0.14)
    lbl((10.45, 8.25), "feed", col: accent, wt: "bold", size: 11pt, anch: "west")
    lbl((11.2, 8.27), "ranked by score", size: 7.5pt, col: pal.sub, anch: "west")
    line((10.45, 8.02), (15.4, 8.02), stroke: 0.8pt + accent)
    content((10.35, 6.85), std.rotate(-90deg, text(size: 7pt, fill: pal.sub)[high → low]))
    let fl = (4.1, 3.7, 3.85, 3.3, 3.5, 3.0, 3.2)
    let fs = ("128", "96", "94", "71", "70", "55", "52")
    let ftop = 7.55
    let fbot = 5.95
    let nf = fl.len()
    for i in range(nf) {
      let yy = ftop - i * (ftop - fbot) / (nf - 1)
      feedrow(10.8, yy, fl.at(i), fs.at(i))
    }
    // score arrow: verb label sits clear ABOVE the arrow line
    arr((9.0, 7.3), (10.05, 7.3), sk: 1.0pt + accent.lighten(10%), sc: 0.42)
    lbl((9.5, 7.55), "score", size: 7pt, col: pal.sub)

    // ---- (F) SOCIAL GRAPH PANEL — pulled toward the community card ------
    card((10.1, 2.3), 5.65, 2.55, bg: pal.callout, sk: 0.9pt + pal.edge, radius: 0.14)
    lbl((10.45, 4.45), panel_title, col: accent, wt: "bold", size: 11pt, anch: "west")
    line((10.45, 4.22), (15.4, 4.22), stroke: 0.8pt + accent)

    if social_mode == "communities" {
      lbl((12.2, 4.47), unit_label + " → community", size: 7.5pt, col: pal.sub, anch: "west")
      // actor icons: NO actor-type label (named once at the top cluster)
      for uy in (3.7, 3.15, 2.6) { act((11.05, uy), s: 0.6) }
      let comm(x, y, t) = {
        card((x, y), 1.6, 0.5, bg: light, sk: 0.8pt + accent, radius: 0.1)
        lbl((x + 0.8, y + 0.25), t, size: 7.5pt, wt: "bold", col: accent)
      }
      comm(13.25, 3.6, prefix + "gaming")
      comm(13.25, 2.55, prefix + "news")
      arr((11.5, 3.72), (13.2, 3.85), sk: 0.85pt + pal.edge, sc: 0.36)
      arr((11.5, 3.17), (13.2, 3.75), sk: 0.85pt + pal.edge, sc: 0.36)
      arr((11.5, 2.62), (13.2, 2.8),  sk: 0.85pt + pal.edge, sc: 0.36)
    } else {
      // accounts mode: Moltbook agents BOTH subscribe to submolt communities
      // (the Reddit-style mechanic) AND follow other agents. Shown as two
      // equally-weighted rows so neither dominates; panel_title names both verbs.
      // row 1 — subscribe to a submolt (topic community)
      act((10.95, 3.5), s: 0.6)
      arr((11.3, 3.5), (13.2, 3.5), sk: 0.85pt + pal.edge, sc: 0.36)
      lbl((12.2, 3.74), "subscribe", size: 6.5pt, col: pal.sub)
      card((13.3, 3.25), 1.6, 0.5, bg: light, sk: 0.8pt + accent, radius: 0.1)
      lbl((14.1, 3.5), prefix + "gaming", size: 7.5pt, wt: "bold", col: accent)
      // row 2 — follow another agent
      act((10.95, 2.65), s: 0.6)
      arr((11.3, 2.65), (13.2, 2.65), sk: 0.85pt + pal.edge, sc: 0.36)
      lbl((12.2, 2.89), "follow", size: 6.5pt, col: pal.sub)
      act((13.55, 2.65), s: 0.75)
    }

    // ---- legend / key — horizontally centred under the figure -----------
    // figure spans x = 1.8 .. 15.75 (centre ~8.78); key card is 9.3 wide ->
    // left edge at 4.13. Lifted to compress bottom empty space while leaving a
    // clear gap below the social-graph panel (panel bottom y = 2.3).
    card((3.85, 1.05), 9.85, 1.05, bg: white, sk: 0.8pt + pal.edge, radius: 0.1)
    lbl((4.13, 1.82), "key", size: 8pt, wt: "bold", col: accent, anch: "west")
    tri((4.23, 1.38), dir: "up", c: pal.up, s: 0.075)
    lbl((4.45, 1.38), "upvote", size: 7pt, anch: "west")
    tri((5.53, 1.38), dir: "down", c: pal.down, s: 0.075)
    lbl((5.75, 1.38), "downvote", size: 7pt, anch: "west")
    scorechip(7.18, 1.15, "·")
    lbl((8.38, 1.38), "score", size: 7pt, anch: "west")
    act((9.28, 1.42), s: 0.55)
    lbl((9.48, 1.38), unit_label, size: 7pt, anch: "west")
    arr((10.28, 1.38), (10.98, 1.38), sk: 0.9pt + pal.edge, sc: 0.42)
    lbl((11.13, 1.38), "post / vote", size: 7pt, anch: "west")
    line((12.38, 1.55), (12.38, 1.2), stroke: 0.9pt + accent.lighten(15%))
    line((12.38, 1.38), (12.63, 1.38), stroke: 0.9pt + accent.lighten(15%))
    lbl((12.73, 1.38), "reply", size: 7pt, anch: "west")
  })
}

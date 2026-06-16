// Shared styling + drawing helpers for the Reddit / Moltbook structure diagrams.
#import "@preview/cetz:0.3.4"

#let pal = (
  ink:      rgb("#16213e"),
  sub:      rgb("#5b6472"),
  edge:     rgb("#8aa0ad"),
  callout:  rgb("#f4f5f7"),
  up:       rgb("#2e7d32"),
  down:     rgb("#c62828"),
  gray:     rgb("#9e9e9e"),
  reddit:   rgb("#d84315"),
  redditLt: rgb("#fde7e1"),
  molt:     rgb("#00838f"),
  moltLt:   rgb("#dcf3f5"),
)

// rounded rectangle card; p = bottom-left corner
#let card(p, w, h, bg: white, sk: 0.9pt + pal.edge, radius: 0.12) = {
  import cetz.draw: *
  rect((p.at(0), p.at(1)), (p.at(0) + w, p.at(1) + h), fill: bg, stroke: sk, radius: radius)
}

// centered text label at p
#let lbl(p, body, size: 8.5pt, col: pal.ink, wt: "regular", anch: "center") = {
  import cetz.draw: *
  content((p.at(0), p.at(1)), anchor: anch, text(size: size, fill: col, weight: wt)[#body])
}

// straight arrow a -> b
#let arr(a, b, sk: 1.1pt + pal.edge, sc: 0.5) = {
  import cetz.draw: *
  line(a, b, mark: (end: ">", fill: pal.edge, scale: sc), stroke: sk)
}

// small filled triangle (vote arrow)
#let tri(p, dir: "up", c: pal.up, s: 0.085) = {
  import cetz.draw: *
  let (x, y) = (p.at(0), p.at(1))
  if dir == "up" {
    merge-path(close: true, fill: c, stroke: none, { line((x - s, y - s), (x + s, y - s), (x, y + s)) })
  } else {
    merge-path(close: true, fill: c, stroke: none, { line((x - s, y + s), (x + s, y + s), (x, y - s)) })
  }
}

// human icon centered at p
#let human(p, c: pal.reddit, s: 1.0) = {
  import cetz.draw: *
  let (x, y) = (p.at(0), p.at(1))
  circle((x, y + 0.20 * s), radius: 0.13 * s, fill: c, stroke: none)
  merge-path(close: true, fill: c, stroke: none, {
    line((x - 0.20 * s, y - 0.10 * s), (x - 0.14 * s, y + 0.07 * s),
         (x + 0.14 * s, y + 0.07 * s), (x + 0.20 * s, y - 0.10 * s))
  })
}

// robot / AI-agent icon centered at p
#let agent(p, c: pal.molt, s: 1.0) = {
  import cetz.draw: *
  let (x, y) = (p.at(0), p.at(1))
  line((x, y + 0.20 * s), (x, y + 0.31 * s), stroke: 1pt + c)
  circle((x, y + 0.34 * s), radius: 0.035 * s, fill: c, stroke: none)
  rect((x - 0.17 * s, y - 0.12 * s), (x + 0.17 * s, y + 0.18 * s), fill: c, stroke: none, radius: 0.05)
  circle((x - 0.075 * s, y + 0.04 * s), radius: 0.038 * s, fill: white, stroke: none)
  circle((x + 0.075 * s, y + 0.04 * s), radius: 0.038 * s, fill: white, stroke: none)
}

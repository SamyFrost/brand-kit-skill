# Motion

How the brand moves: UI, social video, presentations, the logo sting. `brand.py system` derives the tokens from the
axes; you write the principles and the logo sting in `system.json → motion`. Tags: `[strong]` `[practice]`.

## Derived tokens (`systemlib.py`)
| Token | Default | Derivation |
|---|---|---|
| `duration-instant` … `duration-slower` | 70 / 140 / 240 / 400 / 640 ms | × tempo: premium and serious slower (up to ×1.35), playful and accessible faster (down to ×0.75) |
| `duration-scene` | 1000 ms | video transitions between shots |
| `duration-sting` | 2000 ms | logo intro/outro |
| `ease-standard` `ease-enter` `ease-exit` | Material-style curves | fixed: decelerate in, accelerate out `[practice]` |
| `ease-expressive` | playful: overshoot `cubic-bezier(0.34,1.56,0.64,1)`; serious/authority: firm `(0.7,0,0.2,1)`; else calm `(0.3,0,0,1)` | the signature, used only for logo and hero |
| `ease-linear` | `linear` | loops, progress, marquee only |

Change a value only with a reason (e.g. the mark is a pendulum: a long ease-in-out), then set
`foundations.locked: true`.

## Principles (write 3-5 in `motion.principles`)
Tie each to the mechanism. Examples: "Things arrive the way a spoke turns: one decisive quarter turn, no bounce";
"Text never flies in; it appears in place with `duration-fast`"; "One moving thing at a time".

## Logo sting (`motion.logo_sting`)
One sentence each for: what moves (symbol, wordmark, a detail), the path (rotate, draw, slide, reveal), timing
(`duration-sting`, with `ease-expressive`), the end frame (the static logo, held ≥ 1 s), sound if any (optional sonic logo: `sonic.md`). The
`LogoSting` component and `applications/<SET>/logo-sting.html` implement a default (mark scales/rotates in,
wordmark wipes in); edit `applications.py → sting_html` for a different idea. Record at 1920x1080 (screen capture
or Remotion with the same timings) for video.

## Video (`motion.transitions`)
- Text in: `duration-slow` + `ease-enter`; out: `duration-base` + `ease-exit`; scene change: `duration-scene`.
- Lower thirds hold ≥ 4 s; subtitles max two lines, 42 characters per line.
- Cuts on the beat beat dissolves; one transition style per video.
- Safe areas: 5% action-safe, 10% title-safe; vertical video keeps 250 px free top and bottom.

## Accessibility `[strong]`
Honour `prefers-reduced-motion` (fade or nothing); no more than three flashes per second (WCAG 2.3.1); motion is
never the only carrier of meaning.

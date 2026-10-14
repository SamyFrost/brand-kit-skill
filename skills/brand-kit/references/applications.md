# Applications

`brand.py apps WORK/sets/X [--only social,video,stationery,merch] [--scale 2]` renders the chosen set on real
formats into `WORK/applications/X/` (one PNG per piece, `pattern.svg`, `logo-sting.html`, `applications.json`).
They are references and starting points; the live versions are the Design System components. Tags: `[practice]`.

## What is rendered
| Group | Pieces (px) |
|---|---|
| social | ig-post 1080², ig-portrait 1080x1350, story 1080x1920, linkedin-post 1200x627, youtube-thumb 1280x720, avatar 400², banner 1500x500 |
| video | title-card, lower-third, subtitles, end-card (1920x1080) + logo-sting.html |
| stationery | business card front/back (1050x600 = 3.5x2 in @300 dpi), letterhead and document cover (A4 @96 dpi), email signature 600x180, slide-title, slide-content (1920x1080) |
| merch | t-shirt, tote bag, mug, cap, stickers, packaging, storefront sign (flat mock-ups, labelled) |

## Inputs
- Copy: `system.json → applications.copy` (`headline`, `subhead`, `cta`, `handle`, `website`, `email`, `phone`,
  `address`, `person_name`, `person_role`); else the brand's tagline, sentence and CTA from `init`. Missing contact
  fields are filled with obvious sample values and the image carries a **sample data** tag. Set `"sample": false`
  only when every field is real.
- Pillars from `messaging.pillars` label the content slide; `voice.sample_lines[0]` is the quote post and
  subtitle line.
- Pattern: `graphic.pattern` (`scale`, `rotate`, `gap`, `opacity`) tiles the mark on a brick grid.
- Grounds: primary, light, dark and accent from the palette; text colours are picked for contrast and the probe
  measures every text node (a failure is a gate).

## Look and fix
Open 3-5 PNGs (post, story, business card, slide, one merch). Typical fixes: shorter headline (≤ 8 words for
posts), a different `graphic.pattern.scale`, real contact data. Re-run `apps`. Then `ds` picks the PNGs up.

## Production notes (put the relevant ones in the hand-off message)
- Print: 3 mm bleed, 5 mm safe margin, CMYK conversion by the printer from HEX/Lab D50 (`reproduction.md`);
  never guess a Pantone. Business card 85x55 mm (EU) or 3.5x2 in (US).
- Merch: one-colour logo for screen print and embroidery (min 60 mm wide on a cap); check the garment colour
  against the ink (contrast ≥ 3:1).
- Social: export PNG/JPG sRGB at native size; keep text in the central 80%; stories keep 250 px top/bottom free.
- Video: 1920x1080 or 1080x1920, 25/30 fps; motion tokens in `motion.md`; burn in subtitles for social.
- Documents: Word/Google Docs/Slides templates use the same families (install the fonts) and the role colours;
  slide master = slide-title and slide-content.

## Extending
To add a format, write a `page(name, group, w, h, body)` in `scripts/applications.py` using the ground variables
(`--g-bg`, `--g-ink`, `--g-muted`, `--g-btn`, `--g-on-btn`, `--g-rule`) and `c.logo(ground)` / `c.mark(ink)`;
add its size to `ds_export.APP_SIZES` and `APP_GROUPS`.

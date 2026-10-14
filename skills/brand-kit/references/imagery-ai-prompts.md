# Imagery and AI prompts

Photography, illustration and iconography direction, and prompts that make image and video generators produce
on-brand material. Fills `system.json → imagery` and `ai_prompts`. Tags: `[practice]`.

## Imagery direction (`imagery`)
Derive every field from the mechanism and palette, not from stock-photo habits.
| Field | Write | Example |
|---|---|---|
| `photography.style` | genre and attitude | "documentary, hands at work, close and unposed" |
| `photography.light` | light source, time, contrast | "daylight from one side, soft shadows, no flash" |
| `photography.composition` | framing, space for type | "one subject, off-centre, top third free for a headline" |
| `photography.subjects` | what and who | "mechanics, commuters, tools, wheels in motion" |
| `photography.color_grade` | grade in palette terms | "neutral whites, greens pulled toward Workshop Green, no teal-orange" |
| `photography.avoid` | the sector's clichés | "thumbs-up, handshake, stock smiles, lens flare" |
| `illustration.style` / `avoid` | if the brand uses it | "flat shapes cut from the mark's geometry, two inks" |
| `iconography.style` / `stroke` / `corner` / `grid` | match the type and mark | "outline, 2 px, square ends, 24 px grid" |

Icons: prefer an existing open set that matches (Lucide, Phosphor, Material Symbols, Tabler), named exactly,
over drawing a set; say which and why. Do not mix sets.

## Prompts (`ai_prompts`)
- `base_style`: one paragraph appended to every prompt: medium, light, colour grade with the brand hex values
  and names, composition, texture, mood words from the personality. No artist names; no brand names of others.
- `negative`: what to exclude (clichés from `avoid`, text in image, watermarks, extra fingers, gradients the
  palette doesn't have).
- `prompts`: 6-10 entries `{"use", "tool", "aspect", "prompt"}` covering: hero photo, social background,
  product/service scene, team/portrait, texture/pattern background, illustration spot, short video clip
  (5-8 s, camera move, duration), thumbnail background.

Tool notes (write prompts that survive any of them):
| Tool | Note |
|---|---|
| Midjourney | add `--ar 4:5` etc.; `--no` takes the negative; `--style raw` for less embellishment |
| Nano Banana / Gemini image, Imagen | natural sentences; give exact hex colours; ask for "no text" |
| GPT image / DALL-E | full sentences; state the empty area for later typography |
| Firefly, Canva Magic Media | short, concrete; use style reference images from the kit when allowed |
| Veo, Sora, Runway, Kling (video) | subject + action + camera + light + duration; one shot per prompt |

Rules: generated people are not real customers or staff and must not be presented as such; check rights and
the tool's terms before commercial use; keep logos and text out of generated images and add them in layout
(the generator will misspell them).

## Example (structure, not content to copy)
```
base_style: Documentary photograph, natural side light, shallow depth of field, colour graded so greens sit near
#14524a and the single warm accent near #e4572e, neutral whites, matte finish, calm and precise mood, generous
empty space in the upper third for a headline.
negative: text, letters, logos, watermark, lens flare, HDR, teal-and-orange grade, stock smile, thumbs up.
prompt (hero, 16:9): A mechanic's hands truing a bicycle wheel on a workbench, one spoke catching the light, ...
```

# Design System artifact

The kit's home: a claude.ai artifact made from the **Design System** type. Its sidebar is Overview (cover +
README brand book + sections) · Colors · Typography · Spacing · Corner radius · Shadows · Duration · Easing ·
Opacity · Breakpoint · Components · Assets · Files. Everything lives as files under `project/`. When the type's own
instructions (returned on create) differ from this card, the type's instructions win.

## What `brand.py ds` writes (`WORK/design-system/X/`)
| Path | Content |
|---|---|
| `project/README.md` | usage rules naming tokens and assets; no title line (the page shows the name) |
| `project/01-…11-*.md` | sections: platform, voice, logo, colour, type, graphic elements, imagery, AI prompts, motion, applications, accessibility (empty system.json parts are skipped) |
| `project/tokens.json` | `color` (themes light + dark; roles, `brand-*`, scales), `type` (fonts, families, groups), `spacing`, `radius`, `shadow` (per theme), `duration`, `easing`, `opacity`, `breakpoint` — every family a LIST `{"tokens":[{name, value, usage}]}` |
| `project/fonts/*.woff2` | brand faces, OFL/Apache only (others named in `type.families`) |
| `project/components/<Comp>/` | `preview.html` (line 1 `<!-- @dsCard … -->`, token-driven, both themes) + `README.md` |
| `project/components/Cover/preview.html` | the cover; folder stays bare |
| `project/assets/<Group>/` | Logos, Patterns, Social, Video, Stationery, Merch, Guidelines + a README per group |
| `upload-plan.json` | binaries to upload, in batches of ≤ 25 |
| `publish.json` | `{root, files}` map for the publish call (all text + fonts, no uploads, no index) |
| `previews.png` | local check of every preview in each theme — look before publishing |

Grammar the page enforces (`ds_validate.py` checks it): names `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}` unique across
families; colours hex / `rgb()` / `oklch()` … or `{alias}`, no named colours, `var()`, `color-mix()`; other
families plain CSS values (no `var()`/`url()`); ≤ 60 tokens per family, ≤ 600 colours, ≤ 80 type styles.

## Publish sequence (exact)
1. **Create** (once): Artifact `publish` with `type_url` = the Design System type
   (`action: "list", scope: "types"` shows it), `title` = brand name, `auto_open: "after_first_write"`, no files.
   Keep the returned `url`. Never pass `type_url` again (that makes a second system).
2. **Upload** each batch of `upload-plan.json → batches`: `{action: "publish", url, asset: true,
   file_paths: [...]}` (≤ 25 per call). From each result copy every file's id/url.
3. Write `WORK/design-system/X/uploads.json`: `{"<local path>": "<id or /_blob/id>", …}` (keys may also be
   `"Group/name"`).
4. `brand.py ds-index WORK/design-system/X --uploads WORK/design-system/X/uploads.json --by "<user's name>"
   [--via "Claude Code"]` → `project/design-system.json` (`v:3`, `layout:"files"`, `createdOnFiles`, `title`,
   `namespace`, `libraries: []`, `groups`, `assetGroups` with `{name, blob, size, type}` records, `lastChange`).
   It exits 1 and names any asset without an id.
5. **One publish** with `url`, `root` = `WORK/design-system/X`, `file_path` = the absolute path of
   `project/design-system.json`, `files` = `publish.json → files`. If the tool takes at most 255 paths per call
   (or a list form with ≤ 16), split the text files over several calls and send the index in the LAST one.
6. Give the user the link. Mention: what each sidebar part holds, the PDF and logo files, sample data still to
   replace, and how to ask for changes.

## Revising later
Read the index and each file you will change (`action: "read"`, `path`), edit copies, send only changed files
plus the re-read index LAST (`ds-index … --existing <the index you just read>` keeps its keys). `tokens.json` is
always sent whole. Someone saved meanwhile → read again, redo once, else stop and tell the user. Never delete
uploads unprompted.

## Using the system later (any agent)
Read `project/README.md` first, then the section or component README you need; take values from
`project/tokens.json` (or the page's generated `tokens.css`), files from Assets. A new piece (post, deck, flyer,
video frame) starts from the closest component preview at full size and uses only tokens, the brand fonts and
the logo files.

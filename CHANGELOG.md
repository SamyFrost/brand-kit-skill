# Changelog

## 1.0.0 (2026-10-14)

First release of brand-kit, built on brand-identity-skill 1.1.1.

- **Brand system** (`brand.py system`, `systemlib.py`): type scale, spacing, radius, shadows (per theme), duration,
  easing, opacity and breakpoints derived from the brand's axes; `system.json` for platform, voice, messaging,
  graphic devices, imagery, AI prompts, motion and application copy.
- **Applications** (`brand.py apps`, `applications.py`): 25 social, video, stationery and merch renders, the brand
  pattern from the mark and an animated logo sting; text contrast measured on every page; sample data labelled.
- **Design System artifact** (`brand.py ds`, `ds-index`, `ds_export.py`, `ds_validate.py`): tokens.json in the
  page's list grammar (light + dark), README brand book + sections, brand fonts (OFL), live component previews,
  cover, asset groups, upload plan and index writer; local `previews.png` in both themes.
- **References**: creative-framework, motion, imagery-ai-prompts, applications, design-system-artifact.
- **Spanish** labels for cards, board and guidelines (`assets/i18n/es.json`).

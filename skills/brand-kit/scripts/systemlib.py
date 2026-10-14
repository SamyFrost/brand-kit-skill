#!/usr/bin/env python3
"""systemlib.py - the brand *system* around a chosen identity set: system.json (schema "brand-kit/system@1").

identity.json + palette.json say what the brand looks like (logo, type, colour). system.json says how it behaves
and how it is used everywhere else:

  platform     purpose, positioning, personality, values, promise (strategy: written by the designer, approved
               by the client; never invented statistics or mission statements the client did not approve)
  voice        voice traits (is / is not), tone by channel, vocabulary, sample lines, taglines
  messaging    pillars and an elevator pitch
  foundations  type scale, spacing, radius, shadow, duration, easing, opacity, breakpoints: DERIVED from the
               set's axes by this module (re-derived on every `brand.py system` unless foundations.locked)
  graphic      graphic devices and the pattern built from the mark
  imagery      photography, illustration and iconography direction
  ai_prompts   a base style line, a negative line and ready prompts per use (image and video generators)
  motion       principles, logo sting, transitions
  applications copy and contact details used by the application templates (sample data is labelled)

Usage:
  python3 brand.py system WORK/sets/A            # create or refresh WORK/sets/A/system.json
  python3 systemlib.py WORK/sets/A --json        # print the derived foundations only
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import colorlib  # noqa: E402

SCHEMA = "brand-kit/system@1"
AXES = ("warm_cool", "classic_contemporary", "playful_serious", "premium_accessible", "quiet_loud",
        "friend_authority")

# Text fields the designer fills in system.json. Empty strings/lists stay empty in every output (no invention).
TEXT_SKELETON = {
    "platform": {"purpose": "", "positioning": "", "audience": "", "archetype": "", "personality": [],
                 "values": [], "promise": "", "story": ""},
    "voice": {"summary": "", "traits": [], "tone_by_channel": [], "vocabulary": {"use": [], "avoid": []},
              "sample_lines": [], "taglines": []},
    "messaging": {"elevator_pitch": "", "pillars": []},
    "graphic": {"devices": [], "pattern": {"source": "symbol", "scale": 1.0, "rotate": 0, "gap": 1.0,
                                           "ground": "primary", "ink": "accent", "opacity": 1.0}},
    "imagery": {"photography": {"style": "", "light": "", "composition": "", "subjects": "", "color_grade": "",
                                "avoid": ""},
                "illustration": {"style": "", "avoid": ""},
                "iconography": {"style": "", "stroke": "", "corner": "", "grid": "24 px, 2 px padding"}},
    "ai_prompts": {"base_style": "", "negative": "", "prompts": []},
    "motion": {"principles": [], "logo_sting": "", "transitions": ""},
    "applications": {"include": ["social", "video", "stationery", "merch"],
                     "copy": {"headline": "", "subhead": "", "cta": "", "handle": "", "website": "", "email": "",
                              "phone": "", "address": "", "person_name": "", "person_role": "", "sample": True}},
}


def axes_of(identity):
    a = identity.get("axes") or {}
    return {k: max(-2, min(2, int(round(float(a.get(k, 0) or 0))))) for k in AXES}


def _r(x, step=1):
    return int(round(x / step) * step)


# ----------------------------------------------------------------------------- type scale

RATIOS = {-2: 1.2, -1: 1.2, 0: 1.25, 1: 1.333, 2: 1.414}


def type_scale(identity, axes):
    """Display and text styles on a modular scale. quiet_loud picks the ratio (quiet 1.2 ... loud 1.414)."""
    ratio = RATIOS[axes["quiet_loud"]]
    base = 16
    ty = identity.get("type") or {}
    disp = ty.get("display") or ty.get("text") or {}
    text = ty.get("text") or ty.get("display") or {}
    dw = (disp.get("weights") or [600])[0]
    tw = (text.get("weights") or [400])
    tw0, tw1 = tw[0], (tw[1] if len(tw) > 1 else (600 if tw[0] < 600 else tw[0]))
    dtrack = (disp.get("tracking") or 0) / 1000.0
    case = disp.get("case", "as-is")

    def size(n):
        return _r(base * ratio ** n)
    styles = [
        # name, group, role, size, line-height, weight, letter-spacing (em), usage
        ("display-xl", "Display", "display", size(7), 1.0, dw, dtrack, "Hero lines on posters, covers, video titles."),
        ("display", "Display", "display", size(6), 1.05, dw, dtrack, "Campaign headlines, social post headlines."),
        ("h1", "Headings", "display", size(5), 1.1, dw, dtrack, "Page titles, slide titles."),
        ("h2", "Headings", "display", size(4), 1.15, dw, dtrack, "Section titles."),
        ("h3", "Headings", "text", size(3), 1.2, tw1, 0, "Sub-sections, card titles."),
        ("h4", "Headings", "text", size(2), 1.3, tw1, 0, "Small headings, list titles."),
        ("body-lg", "Text", "text", size(1), 1.55, tw0, 0, "Lead paragraphs, intros."),
        ("body", "Text", "text", base, 1.5, tw0, 0, "Running text in documents, web and email."),
        ("body-sm", "Text", "text", 14, 1.45, tw0, 0, "Secondary text, captions under images."),
        ("caption", "Text", "text", 12, 1.4, tw0, 0.01, "Legal lines, credits, metadata."),
        ("overline", "UI", "text", 12, 1.3, tw1, 0.08, "Eyebrows above headlines, labels (upper case)."),
        ("button", "UI", "text", 15, 1.2, tw1, 0.01, "Buttons and calls to action."),
        ("numeric", "UI", "text", 20, 1.2, tw1, 0, "Prices, stats, tabular figures (tnum)."),
    ]
    out = []
    for name, group, role, px, lh, w, ls, usage in styles:
        out.append({"name": name, "group": group, "role": role, "fontSize": f"{px}px",
                    "lineHeight": f"{_r(px * lh)}px", "fontWeight": int(w),
                    "letterSpacing": f"{ls:.3f}em" if ls else "0", "usage": usage,
                    "case": ("upper" if name == "overline" else (case if role == "display" else "as-is"))})
    return {"ratio": ratio, "base": f"{base}px", "styles": out}


# ----------------------------------------------------------------------------- spacing, radius

def spacing(axes):
    steps = [0, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128]
    use = ["No gap.", "Icon to label, tight inline gaps.", "Inside chips and small controls.",
           "Between related lines, form rows.", "Card and button padding, base gap.", "Between groups in a card.",
           "Section padding on mobile, gaps between cards.", "Section padding on desktop.",
           "Between page sections, slide margins.", "Hero spacing, poster margins.", "Large layout breaks."]
    return [{"name": f"space-{i}", "value": f"{v}px", "usage": use[i]} for i, v in enumerate(steps)]


def radius(axes):
    """warm, playful and friendly push round; cool, serious and authoritative push square."""
    roundness = -(axes["warm_cool"] + axes["playful_serious"] + axes["friend_authority"]) / 3.0
    md = {-2: 0, -1: 2, 0: 6, 1: 10, 2: 16}[max(-2, min(2, int(round(roundness))))]
    vals = [("radius-none", 0, "Images bleeding to the edge, tables, rules."),
            ("radius-sm", max(0, md // 2), "Inputs, tags, small chips."),
            ("radius-md", md, "Buttons, cards, the default corner."),
            ("radius-lg", md * 2, "Large cards, modals, social post frames."),
            ("radius-xl", md * 3, "Feature panels, packaging windows.")]
    out = [{"name": n, "value": f"{v}px", "usage": u} for n, v, u in vals]
    out.append({"name": "radius-pill", "value": "999px", "usage": "Pills, avatars, toggles."})
    return out


# ----------------------------------------------------------------------------- shadow

def _rgb(hx):
    r, g, b = colorlib.parse_color(hx)
    return f"{_r(r * 255)}, {_r(g * 255)}, {_r(b * 255)}"


def shadow(axes, palette):
    """Brand-tinted elevation (neutral-950 in light, black in dark). premium: softer, loud: deeper."""
    neutral = (((palette or {}).get("scales") or {}).get("neutral") or {}).get("steps") or {}
    tint = _rgb(neutral.get("950") or "#111111")
    k = 1.0 + 0.15 * axes["quiet_loud"] - 0.1 * (-axes["premium_accessible"])
    k = max(0.6, min(1.5, k))

    def a(x):
        return f"{min(0.6, x * k):.2f}"
    levels = [("shadow-xs", "0 1px 2px", 0.06, "Hairline lift: inputs, chips."),
              ("shadow-sm", "0 2px 6px", 0.08, "Cards at rest."),
              ("shadow-md", "0 8px 20px", 0.10, "Raised cards, menus, hovered cards."),
              ("shadow-lg", "0 16px 40px", 0.14, "Modals, floating panels, product shots on colour."),
              ("shadow-xl", "0 28px 64px", 0.18, "Hero mockups, posters on a wall.")]
    out = []
    for name, geo, alpha, use in levels:
        out.append({"name": name, "value": {"light": f"{geo} rgba({tint}, {a(alpha)})",
                                            "dark": f"{geo} rgba(0, 0, 0, {a(alpha * 2.6)})"}, "usage": use})
    out.append({"name": "shadow-focus", "value": {"light": f"0 0 0 3px {(palette or {}).get('modes', {}).get('light', {}).get('focus', '#2563eb')}",
                                                  "dark": f"0 0 0 3px {(palette or {}).get('modes', {}).get('dark', {}).get('focus', '#60a5fa')}"},
                "usage": "Keyboard focus ring (3 px, the palette's focus colour)."})
    return out


# ----------------------------------------------------------------------------- motion

def duration(axes):
    """Tempo: premium and serious slow down, playful and accessible speed up."""
    f = 1.0 + 0.1 * (-axes["premium_accessible"]) + 0.06 * axes["playful_serious"] + 0.04 * axes["friend_authority"]
    f = max(0.75, min(1.35, f))
    base = [("duration-instant", 70, "Colour and opacity changes on hover/press."),
            ("duration-fast", 140, "Small UI: toggles, chips, tooltips."),
            ("duration-base", 240, "Default: cards, menus, buttons moving."),
            ("duration-slow", 400, "Panels, page elements entering."),
            ("duration-slower", 640, "Large surfaces, hero reveals."),
            ("duration-scene", 1000, "Video: text and graphic transitions between shots."),
            ("duration-sting", 2000, "Logo sting / intro and outro of a video.")]
    return [{"name": n, "value": f"{_r(ms * f, 10)}ms", "usage": u} for n, ms, u in base]


def easing(axes):
    playful = axes["playful_serious"] <= -1
    serious = axes["playful_serious"] >= 1 or axes["friend_authority"] >= 1
    out = [{"name": "ease-standard", "value": "cubic-bezier(0.2, 0, 0, 1)",
            "usage": "Default for anything that moves on screen and stays."},
           {"name": "ease-enter", "value": "cubic-bezier(0, 0, 0.2, 1)",
            "usage": "Elements entering (decelerate into place)."},
           {"name": "ease-exit", "value": "cubic-bezier(0.4, 0, 1, 1)",
            "usage": "Elements leaving (accelerate away)."}]
    if playful:
        out.append({"name": "ease-expressive", "value": "cubic-bezier(0.34, 1.56, 0.64, 1)",
                    "usage": "The brand's signature: a small overshoot for logo, stickers and hero elements."})
    elif serious:
        out.append({"name": "ease-expressive", "value": "cubic-bezier(0.7, 0, 0.2, 1)",
                    "usage": "The brand's signature: a firm, even push for logo and hero moves (no bounce)."})
    else:
        out.append({"name": "ease-expressive", "value": "cubic-bezier(0.3, 0, 0, 1)",
                    "usage": "The brand's signature: a long, calm settle for logo and hero moves."})
    out.append({"name": "ease-linear", "value": "linear", "usage": "Loops, progress bars, marquee text only."})
    return out


def opacity():
    return [{"name": "opacity-disabled", "value": "0.4", "usage": "Disabled controls."},
            {"name": "opacity-muted", "value": "0.64", "usage": "Secondary graphic elements, pattern over photos."},
            {"name": "opacity-overlay", "value": "0.72", "usage": "Scrim behind text on photos and video."}]


def breakpoint():
    return [{"name": "bp-sm", "value": "640px", "usage": "Large phones."},
            {"name": "bp-md", "value": "768px", "usage": "Tablets portrait."},
            {"name": "bp-lg", "value": "1024px", "usage": "Laptops."},
            {"name": "bp-xl", "value": "1280px", "usage": "Desktops; max content width 1200 px."}]


def foundations(identity, palette):
    ax = axes_of(identity)
    return {"derived_from": {"axes": ax}, "locked": False, "type_scale": type_scale(identity, ax),
            "spacing": spacing(ax), "radius": radius(ax), "shadow": shadow(ax, palette), "duration": duration(ax),
            "easing": easing(ax), "opacity": opacity(), "breakpoint": breakpoint()}


# ----------------------------------------------------------------------------- system.json

def _merge(skel, cur):
    """Keep every value the designer wrote; add missing keys from the skeleton."""
    if isinstance(skel, dict):
        cur = cur if isinstance(cur, dict) else {}
        out = dict(cur)
        for k, v in skel.items():
            out[k] = _merge(v, cur.get(k)) if k in cur else json.loads(json.dumps(v))
        return out
    return skel if cur is None else cur


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def system_path(set_dir):
    return os.path.join(os.path.abspath(set_dir), "system.json")


def load_system(set_dir, identity=None, palette=None):
    """system.json merged with the skeleton; foundations derived when absent. Never writes."""
    p = system_path(set_dir)
    cur = load_json(p) if os.path.isfile(p) else {}
    sysd = _merge(TEXT_SKELETON, cur)
    sysd["schema"] = SCHEMA
    if identity is not None and not ((cur.get("foundations") or {}).get("locked")):
        sysd["foundations"] = foundations(identity, palette)
    return sysd


def empty_fields(sysd, prefix=""):
    """Dotted names of text fields still empty (to tell the designer what is left)."""
    out = []
    for k, v in sysd.items():
        if k in ("foundations", "schema", "set", "pattern") or (prefix == "applications." and k == "include"):
            continue
        name = prefix + k
        if isinstance(v, dict):
            out += empty_fields(v, name + ".")
        elif v in ("", [], None):
            out.append(name)
    return out


def ensure_system(set_dir):
    """Create or refresh <set>/system.json: text kept, foundations re-derived unless locked. Returns (path, dict)."""
    sys.path.insert(0, HERE)
    import presentlib as pl
    info = pl.load_set(set_dir)
    sysd = load_system(set_dir, info["identity"], info["palette"])
    sysd["set"] = (info["identity"].get("set") or {}).get("id")
    p = system_path(set_dir)
    write_json(p, sysd)
    return p, sysd


def cli_system(args):
    p, sysd = ensure_system(args.set_dir)
    f = sysd["foundations"]
    ts = f["type_scale"]
    print(f"system: {p}")
    print(f"foundations: type ratio {ts['ratio']} ({len(ts['styles'])} styles) · {len(f['spacing'])} spacing · "
          f"radius-md {next(x['value'] for x in f['radius'] if x['name'] == 'radius-md')} · "
          f"duration-base {next(x['value'] for x in f['duration'] if x['name'] == 'duration-base')} · "
          f"ease-expressive {next(x['value'] for x in f['easing'] if x['name'] == 'ease-expressive')}"
          + (" · locked" if f.get("locked") else ""))
    empty = empty_fields(sysd)
    if empty:
        print(f"to write ({len(empty)}): " + ", ".join(empty[:24]) + (" …" if len(empty) > 24 else ""))
        print("  fill them in system.json (references/creative-framework.md, imagery-ai-prompts.md, motion.md); "
              "empty fields are left out of the kit, never invented")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Derive the brand system foundations for a set and write system.json.")
    ap.add_argument("set_dir")
    ap.add_argument("--json", action="store_true", help="print the derived foundations, write nothing")
    a = ap.parse_args(argv)
    if a.json:
        import presentlib as pl
        info = pl.load_set(a.set_dir)
        print(json.dumps(foundations(info["identity"], info["palette"]), indent=2))
        return 0
    return cli_system(a)


if __name__ == "__main__":
    sys.exit(main())

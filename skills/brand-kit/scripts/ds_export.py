#!/usr/bin/env python3
"""ds_export.py - the chosen set as a claude.ai "Design System" artifact (files under project/).

  python3 brand.py ds WORK/sets/A                     # build WORK/design-system/A/ + validate
  python3 brand.py ds-index WORK/design-system/A --uploads uploads.json --by "Name"

`ds` reads identity.json, palette.json, system.json, the kit (kit/<SET>/: logo files, PDF, pages) and the
applications (applications/<SET>/) and writes:

  WORK/design-system/<SET>/
    project/README.md                 the brand book's front page: usage rules that name tokens and assets
    project/NN-*.md                   further brand-book sections (platform, voice, logo, colour, type, ...)
    project/tokens.json               colour (light + dark), type, spacing, radius, shadow, duration, easing,
                                      opacity, breakpoint - in the list grammar the page reads
    project/fonts/*.woff2             the brand faces (OFL/Apache only; others are named, not shipped)
    project/components/<Comp>/        preview.html (live, token-driven) + README.md (guidelines)
    project/components/Cover/         the cover (bare folder: preview.html only)
    project/assets/<Group>/           logos, pattern, social, video, stationery, merch, guidelines PDF
                                      (binaries are UPLOADS; text READMEs are files)
    upload-plan.json                  the binaries to upload, in batches of <= 25
    publish.json                      the `files` map for the one publish call (text + fonts), index excluded

`ds-index` turns the upload results into project/design-system.json (the index, written LAST).
See references/design-system-artifact.md for the whole publish sequence.
"""
import argparse
import datetime
import html as htmllib
import json
import os
import re
import shutil
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import colorlib  # noqa: E402
import identitylib  # noqa: E402
import presentlib as pl  # noqa: E402
import systemlib  # noqa: E402

e = htmllib.escape
DISPLAY_WEIGHT = 700  # set per build from the display face
SHIP_LICENCES = ("OFL", "APACHE", "UFL", "MIT", "CC0")
MEDIA = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".pdf": "application/pdf", ".webp": "image/webp", ".gif": "image/gif", ".mp4": "video/mp4",
         ".webm": "video/webm"}

# ----------------------------------------------------------------------------- labels (doc language)

L = {
    "en": {
        "how": "How to use this system", "idea": "Brand idea", "content": "Content fundamentals",
        "visual": "Visual foundations", "logo": "Logo", "colour": "Colour", "type": "Typography",
        "space": "Spacing, corners and elevation", "motion": "Motion", "imagery": "Imagery",
        "icons": "Iconography", "apps": "Applications", "files": "Assets", "platform": "Brand platform",
        "voice": "Voice and messaging", "graphic": "Graphic elements", "ai": "AI image and video prompts",
        "access": "Accessibility", "mechanism": "Mechanism", "move": "Expression move", "concept": "Logo idea",
        "differs": "Where it stands apart", "axes": "Position", "purpose": "Purpose", "positioning": "Positioning",
        "audience": "Audience", "archetype": "Archetype", "personality": "Personality", "values": "Values",
        "promise": "Promise", "story": "Story", "pitch": "Elevator pitch", "pillars": "Messaging pillars",
        "is": "We are", "isnot": "We are not", "tone": "Tone by channel", "use": "Words we use",
        "avoid": "Words we avoid", "lines": "Sample lines", "taglines": "Tagline routes", "versions": "Versions",
        "clear": "Clear space", "min": "Minimum size", "misuse": "Never", "brandcol": "Brand colours",
        "roles": "Roles (UI and documents)", "pairs": "Tested pairs", "display": "Display", "text": "Text",
        "scale": "Type scale", "photo": "Photography", "illus": "Illustration", "base": "Base style",
        "neg": "Negative prompt", "prompts": "Ready prompts", "principles": "Principles", "sting": "Logo sting",
        "transitions": "Transitions", "social": "Social", "video": "Video", "stationery": "Stationery",
        "merch": "Merchandise", "guidelines": "Guidelines", "patterns": "Patterns", "logos": "Logos",
        "sample": "Contact details marked sample data are placeholders until the client supplies real ones.",
        "derived": "derived from the mark; adjust after first use",
    },
    "es": {
        "how": "Cómo usar este sistema", "idea": "Idea de marca", "content": "Fundamentos de contenido",
        "visual": "Fundamentos visuales", "logo": "Logotipo", "colour": "Color", "type": "Tipografía",
        "space": "Espaciado, esquinas y elevación", "motion": "Movimiento", "imagery": "Imágenes",
        "icons": "Iconografía", "apps": "Aplicaciones", "files": "Recursos", "platform": "Plataforma de marca",
        "voice": "Voz y mensajes", "graphic": "Elementos gráficos", "ai": "Prompts de IA para imagen y video",
        "access": "Accesibilidad", "mechanism": "Mecanismo", "move": "Gesto expresivo", "concept": "Idea del logo",
        "differs": "En qué se diferencia", "axes": "Posición", "purpose": "Propósito", "positioning": "Posicionamiento",
        "audience": "Público", "archetype": "Arquetipo", "personality": "Personalidad", "values": "Valores",
        "promise": "Promesa", "story": "Historia", "pitch": "Pitch de ascensor", "pillars": "Pilares de mensaje",
        "is": "Somos", "isnot": "No somos", "tone": "Tono por canal", "use": "Palabras que usamos",
        "avoid": "Palabras que evitamos", "lines": "Frases de ejemplo", "taglines": "Rutas de tagline",
        "versions": "Versiones", "clear": "Área de respeto", "min": "Tamaño mínimo", "misuse": "Nunca",
        "brandcol": "Colores de marca", "roles": "Roles (UI y documentos)", "pairs": "Pares comprobados",
        "display": "Titulares", "text": "Texto", "scale": "Escala tipográfica", "photo": "Fotografía",
        "illus": "Ilustración", "base": "Estilo base", "neg": "Prompt negativo", "prompts": "Prompts listos",
        "principles": "Principios", "sting": "Animación del logo", "transitions": "Transiciones",
        "social": "Redes sociales", "video": "Video", "stationery": "Papelería", "merch": "Merchandising",
        "guidelines": "Manual", "patterns": "Patrones", "logos": "Logotipos",
        "sample": "Los datos de contacto marcados como sample data son de ejemplo hasta que el cliente dé los reales.",
        "derived": "derivado del símbolo; ajústalo tras el primer uso",
    },
}

ROLE_USAGE = {
    "background": "Page ground for documents, web and slides.",
    "surface": "Cards and panels on background.",
    "surface-alt": "Alternate rows, wells, quiet sections.",
    "border": "Dividers and hairlines (decorative; inputs need 3:1 - use text-muted for input outlines).",
    "text": "Body copy and headings on background, surface and surface-alt.",
    "text-muted": "Secondary text on background and surface.",
    "primary": "Brand fill: headers, primary buttons, large colour fields.",
    "on-primary": "Text and icons on primary fills only.",
    "accent": "The signal colour: one call to action or highlight per view.",
    "on-accent": "Text and icons on accent fills only.",
    "link": "Inline links on background (underlined).",
    "focus": "Keyboard focus ring (3 px), on every surface.",
    "success": "Success state text/icons on background; always with a word or icon.",
    "warning": "Warning state text/icons on background; always with a word or icon.",
    "danger": "Error state text/icons on background; always with a word or icon.",
    "info": "Informational state text/icons on background.",
}
ROLE_KEYS = {"background": "background", "surface": "surface", "surfaceAlt": "surface-alt", "border": "border",
             "text": "text", "textMuted": "text-muted", "primary": "primary", "onPrimary": "on-primary",
             "accent": "accent", "onAccent": "on-accent", "link": "link", "focus": "focus", "success": "success",
             "warning": "warning", "danger": "danger", "info": "info"}
PAIRS = [("text", "background"), ("text", "surface"), ("text", "surface-alt"), ("text-muted", "background"),
         ("text-muted", "surface"), ("on-primary", "primary"), ("on-accent", "accent"), ("link", "background")]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "x"


def ident_name(s):
    t = re.sub(r"[^A-Za-z0-9]+", " ", s or "Brand").title().replace(" ", "")
    return t if t and t[0].isalpha() else "Brand" + t


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ----------------------------------------------------------------------------- context

class DS:
    def __init__(self, set_dir):
        self.info = pl.load_set(set_dir)
        self.dir = self.info["dir"]
        self.work = self.info["work"]
        self.ident = self.info["identity"]
        self.pal = self.info["palette"]
        self.brand = self.ident.get("brand") or {}
        self.name = self.brand.get("name") or "Brand"
        self.set = self.ident.get("set") or {}
        self.sid = self.set.get("id") or "A"
        self.lang = (self.brand.get("doc_lang") or pl.lang_of(self.brand) or "en").split("-")[0]
        self.L = dict(L["en"], **L.get(self.lang, {}))
        self.sys = systemlib.load_system(self.dir, self.ident, self.pal)
        self.f = self.sys["foundations"]
        self.kit = os.path.join(self.work, "kit", self.sid)
        self.apps = os.path.join(self.work, "applications", self.sid)
        self.svgs = pl.logo_svgs(self.info)
        self.t = pl.theme(self.pal)
        self.notes = []
        self.copy = pl.brand_copy(self.brand)

    def tok(self, fam, name):
        for t in self.f.get(fam) or []:
            if t["name"] == name:
                v = t["value"]
                return v["light"] if isinstance(v, dict) else v
        return None


# ----------------------------------------------------------------------------- tokens.json

def brand_token_names(pal):
    out, seen = [], set()
    for b in (pal or {}).get("brand") or []:
        if not b.get("hex"):
            continue
        n = "brand-" + slug(b.get("name") or b.get("id"))
        while n in seen:
            n += "-2"
        seen.add(n)
        out.append((n, b))
    return out


def tokens_json(d):
    pal = d.pal or {}
    modes = pal.get("modes") or {}
    lt, dk = modes.get("light") or {}, modes.get("dark") or {}
    themes = [{"id": "light", "name": "Light"}] + ([{"id": "dark", "name": "Dark"}] if dk else [])
    colors = []
    for key, name in ROLE_KEYS.items():
        if key not in lt:
            continue
        v = {"light": lt[key]}
        if dk.get(key):
            v["dark"] = dk[key]
        colors.append({"name": name, "value": v, "usage": ROLE_USAGE[name]})
    for n, b in brand_token_names(pal):
        colors.append({"name": n, "value": b["hex"].lower(),
                       "usage": f"{b.get('name') or n}: {b.get('usage') or 'brand colour'}. Artwork, logo and large "
                                f"fields; for UI text use the roles."})
    for x in pal.get("extended") or []:
        n = "ext-" + slug(x.get("name") or x.get("id"))
        v = {"light": x["hex"]}
        if (x.get("dark") or {}).get("hex"):
            v["dark"] = x["dark"]["hex"]
        colors.append({"name": n, "value": v, "usage": x.get("usage") or "Extended colour."})
    for scale, body in (pal.get("scales") or {}).items():
        for step, hx in (body.get("steps") or {}).items():
            colors.append({"name": f"{scale}-{step}", "value": hx.lower(),
                           "usage": f"{scale.capitalize()} scale step {step}; prefer the role tokens in components."})
    ty = d.ident.get("type") or {}
    fonts, families = [], {}
    for role in ("display", "text", "mono"):
        face = ty.get(role)
        if not isinstance(face, dict):
            continue
        families[role] = f'"{face["family"]}", {face.get("fallback") or "sans-serif"}'
    ts = d.f["type_scale"]
    groups = {}
    sample = d.brand.get("tagline") or (d.copy.get("sentence") if isinstance(d.copy.get("sentence"), str) else "") or d.name
    for s in ts["styles"]:
        fam = s["role"] if s["role"] in families else next(iter(families), None)
        st = {"name": s["name"], "fontSize": s["fontSize"], "lineHeight": s["lineHeight"],
              "fontWeight": s["fontWeight"], "usage": s["usage"]}
        if s.get("letterSpacing") and s["letterSpacing"] != "0":
            st["letterSpacing"] = s["letterSpacing"]
        if s["name"] in ("display-xl", "display", "h1", "h2"):
            st["sample"] = sample[:120]
        if fam:
            st["family"] = fam
        groups.setdefault(s["group"], {"name": s["group"], "family": fam or "text", "styles": []})["styles"].append(st)
    out = {"name": d.name, "version": 1,
           "meta": {"source": "brand-kit skill", "set": d.sid, "palette": pal.get("name")},
           "color": {"themes": themes, "tokens": colors},
           "type": {"fonts": fonts, "families": families, "groups": list(groups.values())},
           "spacing": {"tokens": d.f["spacing"]},
           "radius": {"tokens": d.f["radius"]},
           "shadow": {"tokens": d.f["shadow"]},
           "duration": {"note": "Motion durations; scale with the brand tempo (derived from its axes).",
                        "tokens": d.f["duration"]},
           "easing": {"note": "Use ease-expressive only for the brand's signature moves (logo, hero).",
                      "tokens": d.f["easing"]},
           "opacity": {"tokens": d.f["opacity"]},
           "breakpoint": {"tokens": d.f["breakpoint"]}}
    return out


def ship_fonts(d, project):
    """woff2 of each role/weight for shippable licences -> project/fonts; returns tokens type.fonts entries."""
    entries, seen = [], set()
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        d.notes.append("fontTools missing: fonts named, not shipped")
        return entries
    ty = d.ident.get("type") or {}
    for f in pl.resolve_faces(d.ident, d.dir):
        face = ty.get(f["role"]) or {}
        lic = (face.get("license") or "").upper()
        if not f["path"] or not any(lic.startswith(x) for x in SHIP_LICENCES):
            if f["path"] is None or lic:
                d.notes.append(f"{f['family']} {f['weight']}: licence {face.get('license') or 'unknown'}, not shipped")
            continue
        key = (f["family"], f["weight"])
        if key in seen:
            continue
        seen.add(key)
        fn = f"{re.sub(r'[^A-Za-z0-9]+', '', f['family'])}-{f['weight']}.woff2"
        dst = os.path.join(project, "fonts", fn)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            tt = TTFont(f["path"])
            tt.flavor = "woff2"
            tt.save(dst)
        except Exception as exc:  # noqa: BLE001
            d.notes.append(f"{fn}: woff2 failed ({exc})")
            continue
        entries.append({"family": f["family"], "file": f"fonts/{fn}", "weight": str(f["weight"]), "style": "normal"})
    return entries


# ----------------------------------------------------------------------------- brand book

def md_list(items):
    return "\n".join(f"- {x}" for x in items if x)


def bullets_kv(pairs):
    return "\n".join(f"- **{k}:** {v}" for k, v in pairs if v)


def readme(d, assets, comps):
    """README.md: usage rules for people and agents. No title (the page shows the system name)."""
    T, b, s = d.L, d.brand, d.set
    lg = d.ident.get("logo") or {}
    ty = d.ident.get("type") or {}
    disp, text = ty.get("display") or {}, ty.get("text") or {}
    voice = d.sys["voice"]
    lines = []
    intro = " · ".join(x for x in (b.get("sector"), b.get("tagline")) if x)
    if intro:
        lines += [f"{d.name}: {intro}", ""]
    lines += [f"## {T['how']}", "",
              md_list([
                  "Build every piece from these tokens: colours by role (`text` on `background`, `on-primary` on "
                  "`primary`, `on-accent` on `accent`), never raw hex. Brand colours (`brand-*`) are for artwork, logo "
                  "and large fields.",
                  f"Set headlines in `display`/`h1`-`h2` ({disp.get('family', '-')}), running text in `body` "
                  f"({text.get('family', '-')}); see the Typography section for the full scale.",
                  "Space with `space-*` steps, round with `radius-*`, lift with `shadow-*`, move with `duration-*` + "
                  "`ease-*`. `ease-expressive` is reserved for the logo and hero moments.",
                  "Use logo files from the Logos asset group exactly as drawn; never redraw, recolour or stretch "
                  "them (see Logo).",
                  "Start social posts, stories, video graphics, slides, stationery and merch from the matching "
                  "component preview and the PNG in its asset group; keep their safe zones.",
                  "Write copy in the brand voice (Voice and messaging). Generate images with the base style and "
                  "negative prompt in AI image and video prompts.",
                  "Status colours always travel with a word or icon; focus is a 3 px `focus` ring.",
              ]), ""]
    lines += [f"## {T['idea']}", "", bullets_kv([
        (T["mechanism"], s.get("mechanism")), (T["move"], s.get("expression_move")),
        (T["concept"], lg.get("concept")), (T["differs"], s.get("differs_by")),
        (T["axes"], ", ".join(f"{k.replace('_', ' ↔ ')} {v:+d}" for k, v in (d.ident.get("axes") or {}).items()))]), ""]
    cf = []
    if voice.get("summary"):
        cf.append(voice["summary"])
    traits = voice.get("traits") or []
    if traits:
        cf.append("")
        cf.append(f"| {T['is']} | {T['isnot']} |\n|---|---|\n" +
                  "\n".join(f"| {t.get('is', '')} | {t.get('is_not', '')} |" for t in traits))
    if voice.get("sample_lines"):
        cf += ["", md_list(f"“{x}”" for x in voice["sample_lines"][:4])]
    if cf:
        lines += [f"## {T['content']}", ""] + cf + [""]
    vf = [
        f"- **{T['colour']}:** " + ", ".join(f"{b.get('name')} `{n}`" for n, b in brand_token_names(d.pal)) +
        ". UI and documents use the role tokens; light and dark themes are both tested.",
        f"- **{T['type']}:** {disp.get('family', '-')} for display, {text.get('family', '-')} for text; modular "
        f"scale {d.f['type_scale']['ratio']} on {d.f['type_scale']['base']}.",
        f"- **{T['space']}:** 4 px base (`space-1`…`space-10`); default corner `radius-md` "
        f"({d.tok('radius', 'radius-md')}); cards rest on `shadow-sm`.",
        f"- **{T['motion']}:** default `duration-base` ({d.tok('duration', 'duration-base')}) with `ease-standard`; "
        f"signature `ease-expressive` ({d.tok('easing', 'ease-expressive')}). Respect reduced motion.",
    ]
    if (d.sys["imagery"]["photography"] or {}).get("style"):
        vf.append(f"- **{T['imagery']}:** {d.sys['imagery']['photography']['style']}")
    ic = d.sys["imagery"].get("iconography") or {}
    if ic.get("style"):
        vf.append(f"- **{T['icons']}:** {ic['style']}" + (f"; stroke {ic['stroke']}" if ic.get("stroke") else "") +
                  (f"; corners {ic['corner']}" if ic.get("corner") else "") + (f"; grid {ic['grid']}" if ic.get("grid") else ""))
    lines += [f"## {T['visual']}", ""] + vf + [""]
    lines += [f"## {T['files']}", "",
              md_list(f"**{g}** — {len(files)} file(s)" for g, files in assets.items()),
              "", md_list(f"`{c}` — {desc}" for c, desc in comps), ""]
    if d.sys["applications"]["copy"].get("sample", True):
        lines += [f"_{T['sample']}_", ""]
    return "\n".join(lines).rstrip() + "\n"


def sec_platform(d):
    T, p, m = d.L, d.sys["platform"], d.sys["messaging"]
    body = bullets_kv([(T["purpose"], p.get("purpose")), (T["positioning"], p.get("positioning")),
                       (T["audience"], p.get("audience")), (T["archetype"], p.get("archetype")),
                       (T["personality"], ", ".join(p.get("personality") or [])),
                       (T["values"], ", ".join(p.get("values") or [])), (T["promise"], p.get("promise"))])
    out = [f"# {T['platform']}", ""]
    if body:
        out += [body, ""]
    if p.get("story"):
        out += [f"## {T['story']}", "", p["story"], ""]
    if m.get("elevator_pitch"):
        out += [f"## {T['pitch']}", "", m["elevator_pitch"], ""]
    return "\n".join(out) if len(out) > 2 else None


def sec_voice(d):
    T, v, m = d.L, d.sys["voice"], d.sys["messaging"]
    out = [f"# {T['voice']}", ""]
    if v.get("summary"):
        out += [v["summary"], ""]
    if v.get("traits"):
        out += [f"| {T['is']} | {T['isnot']} |", "|---|---|"] + \
               [f"| {t.get('is', '')} | {t.get('is_not', '')} |" for t in v["traits"]] + [""]
    if v.get("tone_by_channel"):
        out += [f"## {T['tone']}", "", "\n".join(f"- **{t.get('channel')}:** {t.get('tone')}" for t in v["tone_by_channel"]), ""]
    voc = v.get("vocabulary") or {}
    if voc.get("use") or voc.get("avoid"):
        out += [bullets_kv([(T["use"], ", ".join(voc.get("use") or [])), (T["avoid"], ", ".join(voc.get("avoid") or []))]), ""]
    if m.get("pillars"):
        out += [f"## {T['pillars']}", ""] + \
               [f"- **{p.get('name')}** — {p.get('message', '')}" + (f" _({p['proof']})_" if p.get("proof") else "")
                for p in m["pillars"]] + [""]
    if v.get("sample_lines"):
        out += [f"## {T['lines']}", "", md_list(f"“{x}”" for x in v["sample_lines"]), ""]
    if v.get("taglines"):
        out += [f"## {T['taglines']}", "", md_list(v["taglines"]), ""]
    return "\n".join(out) if len(out) > 2 else None


MISUSE_WORDS = {"stretch": "Do not stretch or squash the logo.", "rotate": "Do not rotate the logo.",
                "recolour": "Do not recolour the logo outside its approved versions.",
                "effects": "Do not add shadows, glows, gradients or outlines.",
                "outline": "Do not set the logo in outline.", "low-contrast": "Do not place it on low-contrast grounds.",
                "crowd": "Do not crowd the clear space.", "rearrange": "Do not rearrange symbol and wordmark."}


def sec_logo(d, logo_assets):
    T, lg = d.L, d.ident.get("logo") or {}
    out = [f"# {T['logo']}", ""]
    if lg.get("concept"):
        out += [lg["concept"], ""]
    out += [f"## {T['versions']}", "", md_list(f"`{n}`" for n in logo_assets), ""]
    cs = lg.get("clear_space") or {}
    if cs:
        out += [f"## {T['clear']}", "",
                f"{cs.get('multiple', 1)} × {cs.get('unit', 'cap-height')}" + (f" ({T['derived']})" if cs.get("inferred") else ""), ""]
    ms = lg.get("min_size") or {}
    if ms:
        out += [f"## {T['min']}", "", f"{ms.get('px', '-')} px · {ms.get('mm', '-')} mm", ""]
    mis = []
    for m in lg.get("misuse") or []:
        if isinstance(m, dict):
            mis.append(m.get("label") or MISUSE_WORDS.get(m.get("do"), m.get("do")))
    mis = mis or list(MISUSE_WORDS.values())[:5]
    out += [f"## {T['misuse']}", "", md_list(mis), ""]
    return "\n".join(out)


def sec_colour(d):
    T, pal = d.L, d.pal or {}
    out = [f"# {T['colour']}", "", f"## {T['brandcol']}", "", "| | HEX | RGB | OKLCH | Lab D50 | |", "|---|---|---|---|---|---|"]
    for n, b in brand_token_names(pal):
        hx = b["hex"].lower()
        r, g, bl = (round(x * 255) for x in colorlib.parse_color(hx))
        L_, C, H = colorlib.hex_to_oklch(hx)
        lab = (b.get("print") or {}).get("lab_d50")
        out.append(f"| **{b.get('name')}** `{n}` | {hx} | {r} {g} {bl} | {L_:.3f} {C:.3f} {H:.1f} | "
                   f"{' '.join(str(x) for x in lab) if lab else '-'} | {b.get('usage') or ''} |")
    out += ["", "CMYK and Pantone: ask the printer for a conversion with their profile; never guess a Pantone.", ""]
    modes = pal.get("modes") or {}
    out += [f"## {T['pairs']}", "", "| fg / bg | light | dark |", "|---|---|---|"]
    for fg, bg in PAIRS:
        cells = []
        for mode in ("light", "dark"):
            m = modes.get(mode) or {}
            kf = next((k for k, v in ROLE_KEYS.items() if v == fg), None)
            kb = next((k for k, v in ROLE_KEYS.items() if v == bg), None)
            if m.get(kf) and m.get(kb):
                cells.append(f"{colorlib.contrast_ratio(m[kf], m[kb]):.2f}:1")
            else:
                cells.append("-")
        out.append(f"| `{fg}` on `{bg}` | {cells[0]} | {cells[1]} |")
    out += ["", "Only these pairs are tested. Text needs 4.5:1 (3:1 at 24 px+ or bold 19 px+).", ""]
    return "\n".join(out)


def sec_type(d):
    T, ty = d.L, d.ident.get("type") or {}
    out = [f"# {T['type']}", ""]
    for role in ("display", "text", "mono"):
        f = ty.get(role)
        if not isinstance(f, dict):
            continue
        out.append(f"- **{role}:** {f['family']} ({f.get('license') or '-'}, {f.get('source') or '-'}) — weights "
                   f"{', '.join(map(str, f.get('weights') or []))}; tracking {f.get('tracking', 0)}/1000 em; case "
                   f"{f.get('case', 'as-is')}" + (f"; features {', '.join(f['features'])}" if f.get("features") else ""))
    out += ["", f"## {T['scale']}", "", "| style | size / line | weight | use |", "|---|---|---|---|"]
    for s in d.f["type_scale"]["styles"]:
        out.append(f"| `{s['name']}` | {s['fontSize']} / {s['lineHeight']} | {s['fontWeight']} | {s['usage']} |")
    out += ["", "Google Fonts embed: `https://fonts.google.com/specimen/<Family>`; self-host the woff2 files in "
            "`fonts/` (OFL allows it). Office documents: install the same families; fallback "
            + ", ".join(f"{r}: {(ty.get(r) or {}).get('fallback', '-')}" for r in ("display", "text") if ty.get(r)) + ".", ""]
    return "\n".join(out)


def sec_graphic(d):
    T, g = d.L, d.sys.get("graphic") or {}
    out = [f"# {T['graphic']}", ""]
    for dv in g.get("devices") or []:
        if isinstance(dv, dict):
            out.append(f"- **{dv.get('name')}** — {dv.get('description', '')}")
        elif dv:
            out.append(f"- {dv}")
    pat = g.get("pattern") or {}
    out += ["", f"## {T['patterns']}", "",
            f"Repeat of the mark (`pattern.svg` in Patterns): scale {pat.get('scale', 1)}, rotation {pat.get('rotate', 0)}°, "
            f"on `{pat.get('ground', 'primary')}`. Use it on backs (business cards, packaging), banners and slide margins; "
            "never behind body text.", ""]
    return "\n".join(out)


def sec_imagery(d):
    T, im = d.L, d.sys["imagery"]
    out = [f"# {T['imagery']}", ""]
    ph = im.get("photography") or {}
    body = bullets_kv([(k.replace("_", " ").capitalize(), v) for k, v in ph.items()])
    if body:
        out += [f"## {T['photo']}", "", body, ""]
    il = im.get("illustration") or {}
    body = bullets_kv([(k.capitalize(), v) for k, v in il.items()])
    if body:
        out += [f"## {T['illus']}", "", body, ""]
    ic = im.get("iconography") or {}
    body = bullets_kv([(k.capitalize(), v) for k, v in ic.items()])
    if body and ic.get("style"):
        out += [f"## {T['icons']}", "", body, ""]
    return "\n".join(out) if len(out) > 2 else None


def sec_ai(d):
    T, ai = d.L, d.sys["ai_prompts"]
    if not (ai.get("base_style") or ai.get("prompts")):
        return None
    out = [f"# {T['ai']}", ""]
    if ai.get("base_style"):
        out += [f"## {T['base']}", "", "```", ai["base_style"], "```", ""]
    if ai.get("negative"):
        out += [f"## {T['neg']}", "", "```", ai["negative"], "```", ""]
    if ai.get("prompts"):
        out += [f"## {T['prompts']}", ""]
        for p in ai["prompts"]:
            head = " · ".join(x for x in (p.get("use"), p.get("tool"), p.get("aspect")) if x)
            out += [f"**{head}**", "", "```", p.get("prompt", ""), "```", ""]
    return "\n".join(out)


def sec_motion(d):
    T, mo = d.L, d.sys["motion"]
    out = [f"# {T['motion']}", ""]
    if mo.get("principles"):
        out += [f"## {T['principles']}", "", md_list(mo["principles"]), ""]
    out += ["| token | value | use |", "|---|---|---|"]
    for fam in ("duration", "easing"):
        for t in d.f[fam]:
            out.append(f"| `{t['name']}` | `{t['value']}` | {t['usage']} |")
    out.append("")
    if mo.get("logo_sting"):
        out += [f"## {T['sting']}", "", mo["logo_sting"], ""]
    out += ["The `LogoSting` component is the reference animation (loops; record at 1920x1080 for video). "
            "Honour `prefers-reduced-motion`.", ""]
    if mo.get("transitions"):
        out += [f"## {T['transitions']}", "", mo["transitions"], ""]
    return "\n".join(out)


APP_SIZES = {
    "ig-post": "1080x1080", "ig-portrait": "1080x1350", "story": "1080x1920", "linkedin-post": "1200x627",
    "youtube-thumb": "1280x720", "avatar": "400x400 (crop to circle)", "banner": "1500x500",
    "title-card": "1920x1080", "lower-third": "1920x1080 overlay", "subtitles": "1920x1080 overlay",
    "end-card": "1920x1080", "business-card-front": "85x55 mm / 3.5x2 in + 3 mm bleed",
    "business-card-back": "85x55 mm / 3.5x2 in + 3 mm bleed", "letterhead": "A4 210x297 mm",
    "document-cover": "A4 210x297 mm", "email-signature": "600x180 px", "slide-title": "16:9 1920x1080",
    "slide-content": "16:9 1920x1080", "t-shirt": "print ~280 mm wide, chest", "tote-bag": "print ~250 mm wide",
    "mug": "wrap 200x85 mm", "cap": "front embroidery ≤ 60 mm wide", "stickers": "die-cut 50-75 mm",
    "packaging": "per dieline", "storefront-sign": "per site survey"}


def sec_apps(d, app_groups):
    T = d.L
    out = [f"# {T['apps']}", ""]
    for g, files in app_groups.items():
        out += [f"## {T.get(g.lower(), g)}", "", "| piece | size | file |", "|---|---|---|"]
        for fn in files:
            n = re.sub(r"^\d+-|\.png$", "", fn)
            out.append(f"| {n} | {APP_SIZES.get(n, '-')} | `{fn}` |")
        out.append("")
    out += ["Print: CMYK conversion and Pantone matching by the printer from the HEX/Lab values; 3 mm bleed, "
            "5 mm safe margin. Social: keep text inside the central 80% (story: 250 px top and bottom free).", ""]
    if d.sys["applications"]["copy"].get("sample", True):
        out += [f"_{T['sample']}_", ""]
    return "\n".join(out)


def sec_access(d):
    T = d.L
    return "\n".join([f"# {T['access']}", "", md_list([
        "Text meets WCAG 2.2 AA: 4.5:1, or 3:1 at 24 px+ / bold 19 px+; check both themes (Colour → tested pairs).",
        "Never carry meaning by colour alone: status colours always have a word or icon.",
        "Focus: a solid 3 px `focus` ring (`shadow-focus`), at least 3:1 on every surface.",
        "Motion: honour `prefers-reduced-motion`; no flashing above 3 per second in video.",
        "Logos and images carry alt text: the brand name for the logo, the content for photos.",
        "Video: burned-in or closed captions in the `Subtitles` style.",
    ]), ""])


# ----------------------------------------------------------------------------- components

def marker(group, height, subtitle=""):
    sub = f' subtitle="{e(subtitle)}"' if subtitle else ""
    return f'<!-- @dsCard group="{group}" height={height}{sub} -->\n'


def doc(title, css, body, script=""):
    return (f"<!doctype html>\n<html lang=\"en\">\n<head><meta charset=\"utf-8\"><title>{e(title)}</title>\n"
            f"<style>\nhtml,body{{margin:0}}\nbody{{background:var(--background);color:var(--text);font-family:var(--font-text);"
            f"-webkit-font-smoothing:antialiased;--ds-dw:{DISPLAY_WEIGHT}}}\n.disp{{font-family:var(--font-display);font-weight:{DISPLAY_WEIGHT}}}\n{css}\n</style></head>\n<body>\n{body}\n"
            + (f"<script>\n{script}\n</script>\n" if script else "") + "</body>\n</html>\n")


def scaled(w, h, scale, inner_css, inner):
    """A real-size frame (w x h px) shown at `scale` - agents copy the inner markup at full size."""
    return (f'<div class="frame" style="width:{round(w * scale)}px;height:{round(h * scale)}px">'
            f'<div class="art" style="width:{w}px;height:{h}px;transform:scale({scale});{inner_css}">{inner}</div></div>')


FRAME_CSS = (".row{display:flex;gap:16px;padding:16px;flex-wrap:wrap;align-items:flex-start}"
             ".frame{position:relative;overflow:hidden;border-radius:var(--radius-sm);box-shadow:var(--shadow-sm)}"
             ".art{position:absolute;left:0;top:0;transform-origin:0 0;overflow:hidden}"
             ".cap{font-size:12px;color:var(--text-muted);margin-top:6px}")


def mono_svg(svg, pal):
    return pl.colorize(svg, pal, mono="currentColor") if svg else ""


def components(d, pattern_uri):
    """{name: (preview_html, readme_md, short)}"""
    name, pal = d.name, d.pal
    primary = d.svgs.get("primary")
    mark = d.svgs.get("small") or d.svgs.get("symbol") or d.svgs.get("monogram") or primary
    full = pl.colorize(primary, pal, "light") if primary else e(name)
    full_dark = pl.colorize(primary, pal, "dark") if primary else e(name)
    dark_ver = pl.logo_version(d.dir, pl.ground_theme(pal, d.t, "dark")) if pal else None
    if dark_ver:  # the drawn version for dark grounds beats a re-tint of the master
        full_dark = pl.colorize(dark_ver, pal, "dark") if "data-color" in dark_ver else dark_ver
    mono = mono_svg(primary, pal) or e(name)
    mmark = mono_svg(mark, pal) or e(name[:1])
    acp = d.sys["applications"]["copy"]
    hl = acp.get("headline") or d.brand.get("tagline") or name
    sub = acp.get("subhead") or (d.copy.get("sentence") if isinstance(d.copy.get("sentence"), str) else "")
    cta = acp.get("cta") or d.copy.get("cta") or ""
    cp = d.sys["applications"]["copy"]
    person, role = cp.get("person_name") or "Alex Sample", cp.get("person_role") or "Founder"
    web = cp.get("website") or ""                      # never invent contacts in the system
    email = cp.get("email") or ""
    out = {}

    css = (".tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:16px}"
           ".tile{height:140px;border-radius:var(--radius-md);display:grid;place-items:center;padding:24px}"
           ".tile svg{max-height:56px;max-width:100%;width:auto;height:56px}"
           ".t-light{background:#ffffff;border:1px solid var(--border)}.t-dark{background:var(--neutral-950,#111)}"
           ".t-pri{background:var(--primary);color:var(--on-primary)}")
    out["Logo"] = (marker("Brand", 180, "primary logo on light, dark and brand grounds") + doc("Logo", css,
        f'<div class="tiles"><div class="tile t-light">{full}</div><div class="tile t-dark">{full_dark}</div>'
        f'<div class="tile t-pri">{mono}</div></div>'),
        f"# Logo\n\nThe {name} logo. Use the files in the Logos asset group as drawn; this preview shows the approved "
        f"grounds. On a brand fill use the one-colour version in `on-primary`.\n\n- Provide: nothing; place the SVG "
        f"with its clear space.\n- Do: full colour on `background`; reversed on dark.\n- Don't: stretch, rotate, "
        f"recolour, add effects, crowd the clear space.\n", "primary logo on approved grounds")

    out["Pattern"] = (marker("Brand", 200, "the mark as a repeat") + doc("Pattern",
        ".pat{height:168px;margin:16px;border-radius:var(--radius-md);background-color:var(--primary);"
        f"background-image:{pattern_uri};background-size:auto}}", '<div class="pat" role="img" aria-label="pattern"></div>'),
        f"# Pattern\n\nThe {name} mark repeated on a brick grid (`pattern.svg` in Patterns). Backs of cards, packaging, "
        "banners, slide margins.\n\n- Don't: put body text over it, recolour it outside the palette, scale the mark "
        "below its minimum size.\n", "brand pattern from the mark")

    css = (".bar{display:flex;gap:12px;padding:20px;flex-wrap:wrap;align-items:center}"
           ".btn{font:var(--button-weight,600) 15px/1.2 var(--font-text);padding:12px 20px;border-radius:var(--radius-md);"
           "border:1px solid transparent;cursor:pointer;transition:background-color var(--duration-fast) var(--ease-standard),"
           "transform var(--duration-fast) var(--ease-standard)}"
           ".btn:active{transform:translateY(1px)}.btn:focus-visible{outline:none;box-shadow:var(--shadow-focus)}"
           ".pri{background:var(--primary);color:var(--on-primary)}.acc{background:var(--accent);color:var(--on-accent)}"
           ".sec{background:transparent;color:var(--text);border-color:var(--text-muted)}"
           ".ghost{background:transparent;color:var(--link);text-decoration:underline}")
    out["Button"] = (marker("Interface", 88) + doc("Button", css,
        f'<div class="bar"><button class="btn acc">{e(cta or "Call to action")}</button><button class="btn pri">Primary</button>'
        '<button class="btn sec">Secondary</button><button class="btn ghost">Link</button></div>'),
        "# Button\n\nAccent at most once per view for the one action the page is for; primary for main actions; "
        "secondary and link for the rest. Verb first, in the brand voice.\n\n- Provide: label text.\n- Tokens: "
        "`accent`/`on-accent`, `primary`/`on-primary`, `radius-md`, `duration-fast`, `shadow-focus`.\n", "actions")

    css = (".wrap{padding:20px;display:flex;gap:16px;flex-wrap:wrap}.card{background:var(--surface);border-radius:var(--radius-md);"
           "box-shadow:var(--shadow-sm);padding:var(--space-5);width:280px;transition:box-shadow var(--duration-base) var(--ease-standard)}"
           ".card:hover{box-shadow:var(--shadow-md)}.ov{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-muted)}"
           ".ti{font-family:var(--font-display);font-weight:var(--ds-dw,600);font-size:24px;line-height:1.15;margin:8px 0}.bd{font-size:15px;line-height:1.5;color:var(--text-muted)}"
           ".tag{display:inline-block;margin-top:14px;font-size:12px;padding:4px 10px;border-radius:var(--radius-pill);"
           "background:var(--surface-alt);color:var(--text)}")
    out["Card"] = (marker("Interface", 280) + doc("Card", css,
        f'<div class="wrap"><div class="card"><div class="ov">{e(name)}</div><div class="ti">{e(hl)}</div>'
        f'<div class="bd">{e(sub or hl)}</div><span class="tag">Tag</span></div></div>'),
        "# Card\n\nA grouped piece of content on `surface` with `shadow-sm` (hover `shadow-md`), corner `radius-md`, "
        "padding `space-5`.\n\n- Provide: overline, title, body, optional tag.\n", "content card")

    css = (".bar{display:flex;gap:10px;padding:20px;flex-wrap:wrap}.b{font-size:13px;font-weight:600;padding:5px 12px;"
           "border-radius:var(--radius-pill);border:1px solid currentColor;background:var(--background)}"
           ".ok{color:var(--success)}.wa{color:var(--warning)}.da{color:var(--danger)}.in{color:var(--info)}")
    out["Status"] = (marker("Interface", 72) + doc("Status", css,
        '<div class="bar"><span class="b ok">✓ Done</span><span class="b wa">! Check</span><span class="b da">× Error</span>'
        '<span class="b in">i Note</span></div>'),
        "# Status\n\nState labels: always a word and a symbol, never colour alone. Text in `success`, `warning`, "
        "`danger`, `info` on `background`.\n", "status labels")

    # social / video / print templates at real size, scaled
    pat_bg = f"background-image:{pattern_uri};background-size:auto"
    post = (f'<div style="position:absolute;inset:0;background:var(--primary);color:var(--on-primary);padding:96px;display:flex;flex-direction:column">'
            f'<div style="height:64px;color:var(--on-primary)" class="lg">{mono}</div>'
            f'<div class="disp" style="margin-top:auto;font-size:96px;line-height:1.04;max-width:820px">{e(hl)}</div>'
            f'<div style="font-size:30px;margin-top:20px;opacity:.9">{e(sub)}</div></div>')
    story = (f'<div style="position:absolute;inset:0;background:var(--neutral-950,#111);color:#fff;padding:220px 96px 260px;display:flex;flex-direction:column">'
             f'<div style="height:72px" class="lg">{full_dark}</div>'
             f'<div class="disp" style="margin-top:auto;font-size:120px;line-height:1.02">{e(hl)}</div>'
             + (f'<div style="align-self:flex-start;margin-top:56px;background:var(--accent);color:var(--on-accent);font-size:38px;'
                f'font-weight:600;padding:28px 56px;border-radius:var(--radius-md)">{e(cta)}</div>' if cta else "") + "</div>")
    css = FRAME_CSS + ".lg svg{height:100%;width:auto;display:block}"
    out["SocialPost"] = (marker("Social", 380, "1080x1080 and 1080x1920") + doc("Social post", css,
        '<div class="row"><div>' + scaled(1080, 1080, 0.3, "", post) + '<div class="cap">Post 1080x1080</div></div><div>'
        + scaled(1080, 1920, 0.17, "", story) + '<div class="cap">Story 1080x1920</div></div></div>'),
        "# Social post\n\nFeed post (1080x1080) and story (1080x1920). Headline in `display`, one line of support, logo "
        "top-left; story keeps 250 px free top and bottom for the app UI. PNGs of every format are in the Social asset "
        "group.\n\n- Provide: headline (≤ 8 words), support line, optional CTA.\n- Don't: more than one accent element; "
        "text over the pattern.\n", "feed post and story")

    l3 = ('<div style="position:absolute;inset:0;background:repeating-linear-gradient(135deg,#6b6b6b 0 40px,#5f5f5f 40px 80px)"></div>'
          '<div style="position:absolute;left:120px;bottom:120px;display:flex"><div style="width:14px;background:var(--accent)"></div>'
          f'<div style="background:var(--primary);color:var(--on-primary);padding:28px 44px"><div class="disp" style="font-size:52px">{e(person)}</div>'
          f'<div style="font-size:28px;margin-top:6px">{e(role)} · {e(name)}</div></div></div>')
    title = (f'<div style="position:absolute;inset:0;background:var(--primary);color:var(--on-primary);padding:140px 160px;display:flex;'
             f'flex-direction:column;justify-content:center"><div style="font-size:28px;letter-spacing:.08em;text-transform:uppercase">{e(name)}</div>'
             f'<div class="disp" style="font-size:140px;line-height:1.02;margin-top:24px">{e(hl)}</div>'
             '<div style="width:180px;height:14px;background:var(--accent);margin-top:56px"></div></div>')
    out["VideoGraphics"] = (marker("Video", 220, "title card and lower third, 1920x1080") + doc("Video graphics", FRAME_CSS,
        '<div class="row"><div>' + scaled(1920, 1080, 0.16, "", title) + '<div class="cap">Title card</div></div><div>'
        + scaled(1920, 1080, 0.16, "", l3) + '<div class="cap">Lower third (over footage)</div></div></div>'),
        "# Video graphics\n\nTitle card, lower third, subtitles and end card at 1920x1080 (PNGs in the Video group). "
        "Text in: `duration-slow` with `ease-enter`; out: `duration-base` with `ease-exit`; between scenes "
        "`duration-scene`. Lower third: name in `display` 52 px, role in text 28 px, accent bar 14 px.\n\n- Provide: "
        "name, role, title text.\n- Safe area: 5% action-safe, 10% title-safe.\n", "title card and lower third")

    sting_mark = mmark
    css = (".st{height:220px;background:var(--primary);color:var(--on-primary);display:flex;align-items:center;justify-content:center;gap:28px;overflow:hidden}"
           ".m{height:96px;animation:mk calc(var(--duration-sting) * 2) var(--ease-expressive) infinite both}"
           ".w{font-family:var(--font-display);font-size:64px;font-weight:700;clip-path:inset(0 100% 0 0);"
           "animation:wd calc(var(--duration-sting) * 2) var(--ease-enter) infinite both}"
           ".m svg{height:100%;width:auto;display:block}"
           "@keyframes mk{0%{transform:scale(.4) rotate(-90deg);opacity:0}25%{transform:none;opacity:1}85%{opacity:1}100%{opacity:0}}"
           "@keyframes wd{0%,20%{clip-path:inset(0 100% 0 0)}45%{clip-path:inset(0 0 0 0)}85%{opacity:1}100%{opacity:0;clip-path:inset(0 0 0 0)}}"
           "@media (prefers-reduced-motion:reduce){.m,.w{animation:none;clip-path:none}}")
    wm_case = {"lower": name.lower(), "upper": name.upper()}.get(((d.ident.get("type") or {}).get("display") or {}).get("case"), name)
    out["LogoSting"] = (marker("Motion", 220, "duration-sting + ease-expressive") + doc("Logo sting", css,
        f'<div class="st" role="img" aria-label="{e(name)}"><div class="m">{sting_mark}</div><div class="w">{e(wm_case)}</div></div>'),
        "# Logo sting\n\nThe logo's signature move for video intros/outros and app launch: the mark arrives with "
        "`ease-expressive` over `duration-sting`, then the wordmark wipes in with `ease-enter`. `logo-sting.html` in "
        "the Video group is the full-screen version to record at 1920x1080.\n\n- Don't: other easings or durations for "
        "the logo; bounce on a serious brand.\n", "animated logo")

    card_f = (f'<div style="position:absolute;inset:0;background:#fff;color:#111;padding:72px 80px;display:flex;flex-direction:column">'
              f'<div style="height:64px" class="lg">{full}</div><div style="margin-top:auto"><div class="disp" style="font-size:44px">{e(person)}</div>'
              f'<div style="font-size:24px;opacity:.75">{e(role)}</div><div style="font-size:22px;margin-top:24px;line-height:1.5">'
              f'{e(email)}<br>{e(web)}</div></div></div>')
    card_b = (f'<div style="position:absolute;inset:0;background-color:var(--primary);{pat_bg};display:grid;place-items:center">'
              f'<div style="background:#fff;padding:44px 56px;border-radius:var(--radius-md);width:62%;box-sizing:border-box" class="lgw">{full}</div></div>')
    sig = (f'<div style="position:absolute;inset:0;background:#fff;color:#111;display:flex;gap:24px;align-items:center;padding:24px 28px">'
           f'<div style="height:64px;color:var(--primary)" class="lg">{mmark}</div><div style="border-left:2px solid var(--accent);padding-left:20px">'
           f'<div class="disp" style="font-size:20px">{e(person)}</div><div style="font-size:13px;opacity:.75">{e(role)} · {e(name)}</div>'
           f'<div style="font-size:13px;margin-top:8px">{e(email)}</div></div></div>')
    css = FRAME_CSS + ".lg svg{height:100%;width:auto;display:block}.lgw svg{width:100%;height:auto;display:block}"
    if "stationery" in (d.sys["applications"].get("include") or []):
      out["Stationery"] = (marker("Print", 330, "business card front/back, email signature") + doc("Stationery", css,
        '<div class="row"><div>' + scaled(1050, 600, 0.3, "", card_f) + '<div class="cap">Card front</div></div><div>'
        + scaled(1050, 600, 0.3, "", card_b) + '<div class="cap">Card back</div></div><div>'
        + scaled(600, 180, 0.5, "", sig) + '<div class="cap">Email signature</div></div></div>'),
        "# Stationery\n\nBusiness card (85x55 mm, 3 mm bleed), letterhead and document cover (A4), email signature "
        "(600x180), slides (16:9). PNG references are in the Stationery group; set print files in CMYK from the "
        "printer's conversion of the HEX/Lab values.\n\n- Provide: name, role, contacts (real ones; sample values "
        "are marked).\n", "business card, signature")

    # merch has no live preview: its PNG mock-ups are assets
    return out


def cover(d):
    """Cover: brand colour blocks + one pattern of pills at spacing steps, name bottom-left (cover.md brief)."""
    brands = brand_token_names(d.pal)
    b1 = brands[0][0] if brands else "primary"
    b2 = brands[1][0] if len(brands) > 1 else "accent"
    n = d.name  # as the README writes it (cover.md): no case transform
    disp = (d.ident.get("type") or {}).get("display") or {}
    loc = disp.get("location") or {}
    em = 0.6 * float(loc.get("wdth", 100)) / 100 + (0.06 if float(loc.get("wght", (disp.get("weights") or [400])[0])) >= 700 else 0)
    size = max(56, min(120, int(440 / (em * max(4, len(n))))))
    rad = d.tok("radius", "radius-md") or "6px"
    pills = []
    for i in range(14):
        x = 192 + (i % 5) * 48 + (24 if (i // 5) % 2 else 0)
        y = 232 - (i // 5) * 32
        w = (16, 32, 24, 40, 16)[i % 5]
        pills.append(f'<rect class="pill" x="{x}" y="{y}" width="{w}" height="8" rx="4"/>')
    tag = d.brand.get("tagline") or ""
    return (f"""<!-- @dsCard height=288 -->
<!doctype html>
<html lang="{e(pl.lang_of(d.brand))}">
<head><meta charset="utf-8"><title>{e(n)}</title>
<style>
html,body{{margin:0;height:100%}}
body{{background:var(--background);color:var(--text);font-family:var(--font-text);overflow:hidden}}
.cover{{position:relative;height:288px;overflow:hidden}}
.art{{position:absolute;top:0;left:480px;width:480px;height:288px;overflow:hidden}}
.art svg{{display:block;width:640px;height:288px}}
.b1{{fill:var(--{b1})}}.b2{{fill:var(--{b2})}}.deep{{fill:var(--primary-800)}}.tint{{fill:var(--primary-200)}}
.blk{{rx:var(--radius-md)}}.pill{{fill:var(--{b2})}}
.words{{position:absolute;left:var(--space-6);bottom:var(--space-6);max-width:440px}}
.name{{margin:0;font-family:var(--font-display);font-size:{size}px;line-height:.92;font-weight:{DISPLAY_WEIGHT};color:var(--text)}}
.tag{{margin:var(--space-2) 0 0 4px;font-size:14px;line-height:20px;color:var(--text-muted)}}
</style></head>
<body><div class="cover">
<div class="art" aria-hidden="true"><svg viewBox="0 0 640 288" width="640" height="288">
<!--
  blocks      {b1} 144x240 bled off the top (the brand colour people know) · primary-200 tint 144x184 · primary-800 216 tall off the right edge (stays visible on the dark ground) · {b2} 64x24 once
  arrangement one tall brand slab with satellites, bottoms on one line space-6 above the edge, space-4 gutters
  pattern     pills at a space-6 pitch rising over the tint, in {b2}: the brand's one signal colour, used sparingly
  scales      sides in space-2 multiples; gutters space-4; corners radius-md ({rad}); pills rx = half of space-2
-->
<rect class="b1 blk" x="16" y="-16" width="144" height="240" rx="{rad.rstrip('px')}"/>
<rect class="b2 blk" x="16" y="240" width="64" height="24" rx="4"/>
<rect class="tint blk" x="176" y="80" width="144" height="184" rx="{rad.rstrip('px')}"/>
<rect class="deep blk" x="336" y="48" width="304" height="216" rx="{rad.rstrip('px')}"/>
{chr(10).join(pills)}
</svg></div>
<div class="words"><h1 class="name">{e(n)}</h1>{f'<p class="tag">{e(tag)}</p>' if tag else ''}</div>
</div></body></html>
""")


# ----------------------------------------------------------------------------- assets

LOGO_FILES = ["full-color.svg", "full-color.png", "full-color-dark.svg", "full-color-dark.png", "one-color-dark.svg",
              "one-color-dark.png", "one-color-light.svg", "one-color-light.png", "symbol-only.svg", "symbol-only.png",
              "on-dark-background.svg", "on-light-primary.svg", "app-icon-512.png", "app-icon-512.svg", "favicon-32.png",
              "favicon-48.svg"]
APP_GROUPS = {"social": ("ig-post", "ig-portrait", "story", "linkedin-post", "youtube-thumb", "avatar", "banner"),
              "video": ("title-card", "lower-third", "subtitles", "end-card"),
              "stationery": ("business-card-front", "business-card-back", "letterhead", "document-cover",
                             "email-signature", "slide-title", "slide-content"),
              "merch": ("t-shirt", "tote-bag", "mug", "cap", "stickers", "packaging", "storefront-sign")}


def collect_assets(d, project):
    """Copy assets into project/assets/<Group>/ and return {group: [file names]}, app groups and the upload plan."""
    T = d.L
    groups, plan, app_groups = {}, [], {}

    def add(group, src, name=None):
        if not os.path.isfile(src):
            return
        name = name or os.path.basename(src)
        dst = os.path.join(project, "assets", group, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        groups.setdefault(group, []).append(name)
        ext = os.path.splitext(name)[1].lower()
        plan.append({"group": group, "name": name, "path": dst, "size": os.path.getsize(dst),
                     "type": MEDIA.get(ext, "application/octet-stream")})

    slug_ = pl.slug(d.name)
    logo_dir = os.path.join(d.kit, "logo")
    for fn in LOGO_FILES:
        add("Logos", os.path.join(logo_dir, fn), f"{slug_}-{fn}")
    if not os.path.isdir(logo_dir):
        d.notes.append("no kit/<SET>/logo: run `brand.py kit` first for logo files")
    add("Patterns", os.path.join(d.apps, "pattern.svg"), f"{slug_}-pattern.svg")
    if os.path.isdir(d.apps):
        pngs = sorted(f for f in os.listdir(d.apps) if f.endswith(".png"))
        for g, names in APP_GROUPS.items():
            grp = {"social": "Social", "video": "Video", "stationery": "Stationery", "merch": "Merch"}[g]
            for fn in pngs:
                if re.sub(r"^\d+-|\.png$", "", fn) in names:
                    add(grp, os.path.join(d.apps, fn), re.sub(r"^\d+-", "", fn))
                    app_groups.setdefault(grp, []).append(re.sub(r"^\d+-", "", fn))
    else:
        d.notes.append("no applications/<SET>: run `brand.py apps` first for social/video/print/merch PNGs")
    sting = os.path.join(d.apps, "logo-sting.html")
    if os.path.isfile(sting):  # text: a plain file in the group, not an upload
        dst = os.path.join(project, "assets", "Video", "logo-sting.html")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(sting, dst)
    if os.path.isdir(d.kit):
        for fn in sorted(os.listdir(d.kit)):
            if fn.endswith(".pdf"):
                add("Guidelines", os.path.join(d.kit, fn))
    readmes = {
        "Logos": f"# {T['logos']}\n\nFull colour on light grounds; `-dark` versions on dark grounds; one-colour versions "
                 "for single-ink print (embroidery, stamps, engraving); `symbol-only` for avatars and small spaces; "
                 "app icon and favicon for digital. Colours are fixed artwork (not `currentColor`).\n",
        "Patterns": f"# {T['patterns']}\n\nThe brand pattern tile (SVG, repeats seamlessly). Ground `primary`, ink as drawn.\n",
        "Social": f"# {T['social']}\n\nReference renders at native size (PNG). Rebuild from the `SocialPost` component for "
                  "new copy.\n",
        "Video": f"# {T['video']}\n\n1920x1080 references: title card, lower third, subtitles, end card. Grey stripes "
                 "stand for footage. Animate with the motion tokens.\n",
        "Stationery": f"# {T['stationery']}\n\nBusiness card (front/back), letterhead, document cover, email signature, "
                      "slides. Sample contact data is marked on the image.\n",
        "Merch": f"# {T['merch']}\n\nFlat mock-ups (labelled) showing placement and colour on t-shirt, tote, mug, cap, "
                 "stickers, packaging and a storefront sign. Production files: the logo SVGs.\n",
        "Guidelines": f"# {T['guidelines']}\n\nThe brand guidelines PDF (fonts embedded).\n",
    }
    for g in groups:
        write(os.path.join(project, "assets", g, "README.md"), readmes.get(g, f"# {g}\n"))
    return groups, app_groups, plan


# ----------------------------------------------------------------------------- build

def build(set_dir, out=None):
    d = DS(set_dir)
    out = os.path.abspath(out or os.path.join(d.work, "design-system", d.sid))
    project = os.path.join(out, "project")
    if os.path.isdir(project):
        idx = os.path.join(project, "design-system.json")
        keep = open(idx, encoding="utf-8").read() if os.path.isfile(idx) else None
        shutil.rmtree(project)
        if keep:
            write(idx, keep)
    os.makedirs(project, exist_ok=True)
    tokens = tokens_json(d)
    tokens["type"]["fonts"] = ship_fonts(d, project)
    write(os.path.join(project, "tokens.json"), json.dumps(tokens, ensure_ascii=False, indent=2) + "\n")
    groups, app_groups, plan = collect_assets(d, project)
    gp = pl.ground_theme(d.pal, d.t, "primary")
    import applications
    try:
        actx = applications.Ctx(set_dir)
        pat_uri = applications.pattern_css(applications.pattern_svg(
            actx, gp["bg"], gp["rule"] if colorlib.delta_e_ok(gp["rule"], gp["bg"]) > 0.08 else gp["ink"]))
    except Exception as exc:  # noqa: BLE001 - the pattern preview is optional
        d.notes.append(f"pattern preview skipped: {exc}")
        pat_uri = "none"
    global DISPLAY_WEIGHT
    DISPLAY_WEIGHT = (((d.ident.get("type") or {}).get("display") or {}).get("weights") or [700])[0]
    comps = components(d, pat_uri)
    for cname, (prev, rd, _short) in comps.items():
        write(os.path.join(project, "components", cname, "preview.html"), prev)
        write(os.path.join(project, "components", cname, "README.md"), rd)
    write(os.path.join(project, "components", "Cover", "preview.html"), cover(d))
    sections = [("01-brand-platform.md", sec_platform(d)), ("02-voice-and-messaging.md", sec_voice(d)),
                ("03-logo.md", sec_logo(d, groups.get("Logos", []))), ("04-colour.md", sec_colour(d)),
                ("05-typography.md", sec_type(d)), ("06-graphic-elements.md", sec_graphic(d)),
                ("07-imagery.md", sec_imagery(d)), ("08-ai-prompts.md", sec_ai(d)), ("09-motion.md", sec_motion(d)),
                ("10-applications.md", sec_apps(d, app_groups)), ("11-accessibility.md", sec_access(d))]
    written = []
    for fn, body in sections:
        if body:
            write(os.path.join(project, fn), body)
            written.append(fn)
    write(os.path.join(project, "README.md"), readme(d, groups, [(c, v[2]) for c, v in comps.items()]))
    # upload plan in batches of 25, and the publish files map (text + fonts; not the index, not uploads)
    batches = [plan[i:i + 25] for i in range(0, len(plan), 25)]
    write(os.path.join(out, "upload-plan.json"), json.dumps(
        {"schema": "brand-kit/ds-upload-plan@1", "batches": [[x["path"] for x in b] for b in batches], "files": plan},
        ensure_ascii=False, indent=2) + "\n")
    upload_paths = {x["path"] for x in plan}
    files = {}
    for root, _dirs, fns in os.walk(project):
        for fn in fns:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, out).replace(os.sep, "/")
            if p in upload_paths or rel == "project/design-system.json":
                continue
            files[rel] = rel
    write(os.path.join(out, "publish.json"), json.dumps({"root": out, "files": files}, ensure_ascii=False, indent=2) + "\n")
    import ds_validate
    report = ds_validate.validate(out)
    return {"dir": out, "project": project, "sections": written, "components": list(comps) + ["Cover"],
            "assets": groups, "uploads": len(plan), "batches": len(batches), "files": len(files),
            "notes": d.notes, "report": report, "title": d.name, "namespace": ident_name(d.name)}


# ----------------------------------------------------------------------------- local preview sheet

def tokens_css(tokens, project):
    """A local stand-in for the page's compiled tokens.css (format.md: "tokens.css as compiled")."""
    col = tokens.get("color") or {}
    themes = [t["id"] for t in col.get("themes") or []] or ["light"]
    first = themes[0]
    per = {t: [] for t in themes}

    def val(v):
        m = re.match(r"^\{(.+)\}$", v)
        return f"var(--{m.group(1)})" if m else v
    for t in col.get("tokens") or []:
        v = t["value"]
        vals = v if isinstance(v, dict) else {first: v}
        for th, x in vals.items():
            per.setdefault(th, []).append(f"--{t['name']}:{val(x)};")
    for t in (tokens.get("shadow") or {}).get("tokens") or []:
        v = t["value"]
        vals = v if isinstance(v, dict) else {first: v}
        for th, x in vals.items():
            per.setdefault(th, []).append(f"--{t['name']}:{x};")
    out = [f':root,[data-theme="{first}"]{{{"".join(per[first])}}}']
    for th in themes[1:]:
        out.append(f'[data-theme="{th}"]{{{"".join(per.get(th, []))}}}')
    rest = []
    for fam, body in tokens.items():
        if fam in ("color", "type", "shadow") or not isinstance(body, dict) or "tokens" not in body:
            continue
        for t in body["tokens"]:
            rest.append(f"--{t['name']}:{t['value']};")
    ty = tokens.get("type") or {}
    for k, stack in (ty.get("families") or {}).items():
        rest.append(f"--font-{k}:{stack};")
    out.append(f":root{{{''.join(rest)}}}")
    for g in ty.get("groups") or []:
        for st in g.get("styles") or []:
            fam = st.get("family") or g.get("family")
            out.append(f".{st['name']}{{font-family:var(--font-{fam});font-size:{st['fontSize']};"
                       f"line-height:{st.get('lineHeight', 'normal')};font-weight:{st.get('fontWeight', 400)};"
                       f"letter-spacing:{st.get('letterSpacing', 'normal')}}}")
    for f in ty.get("fonts") or []:
        path = os.path.join(project, f["file"])
        out.append(f'@font-face{{font-family:"{f["family"]}";src:url("{pl._url(path, None)}");'
                   f'font-weight:{f.get("weight", "400")};font-style:{f.get("style", "normal")}}}')
    return "\n".join(out)


def render_previews(ds_dir):
    """ds_dir/previews.png: every component preview (Cover first) in each theme, side by side. Local check only."""
    import render_png
    project = os.path.join(ds_dir, "project")
    tokens = json.load(open(os.path.join(project, "tokens.json"), encoding="utf-8"))
    css = tokens_css(tokens, project)
    themes = [t["id"] for t in (tokens.get("color") or {}).get("themes") or []] or ["light"]
    comps = sorted(os.listdir(os.path.join(project, "components")), key=lambda c: (c != "Cover", c))
    rows = []
    for c in comps:
        p = os.path.join(project, "components", c, "preview.html")
        if not os.path.isfile(p):
            continue
        src = open(p, encoding="utf-8").read()
        m = re.search(r"height=(\d+)", src.splitlines()[0])
        h = int(m.group(1)) if m else 120
        cells = []
        for th in themes:
            doc_ = re.sub(r"<html\b", f'<html data-theme="{th}"', src, count=1)
            doc_ = doc_.replace("<head>", f"<head><style>{css}</style>", 1)
            cells.append(f'<iframe style="width:960px;height:{h}px;border:0;background:#fff" '
                         f'srcdoc="{e(doc_, quote=True)}"></iframe>')
        rows.append(f'<div style="font:600 13px system-ui;margin:18px 0 6px">{e(c)}</div>'
                    f'<div style="display:flex;gap:24px">{"".join(cells)}</div>')
    html = (f'<!doctype html><html><body style="margin:24px;background:#d9d9d9">{"".join(rows)}</body></html>')
    hp = os.path.join(ds_dir, "previews.html")
    write(hp, html)
    png = os.path.join(ds_dir, "previews.png")
    render_png.screenshot_html(hp, png, width=48 + 984 * len(themes), height=900, full_page=True)
    return png


# ----------------------------------------------------------------------------- index

BLOB = re.compile(r"([0-9a-f]{32})")


def write_index(ds_dir, uploads, by="Claude", via="Claude Code", note=None, title=None, existing=None):
    """project/design-system.json from the upload results. `uploads`: {local path | 'Group/name': blob id or
    '/_blob/<id>' url}. An existing index (read right before) keeps every key it has."""
    ds_dir = os.path.abspath(ds_dir)
    project = os.path.join(ds_dir, "project")
    with open(os.path.join(ds_dir, "upload-plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)["files"]
    tokens = json.load(open(os.path.join(project, "tokens.json"), encoding="utf-8"))
    title = title or tokens.get("name") or "Brand"
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    idx = existing or {"v": 3, "layout": "files", "createdOnFiles": {"v": 1, "at": now}, "title": title,
                       "namespace": ident_name(title), "libraries": [], "sections": {}, "groups": [],
                       "assetGroups": {}, "blobs": {}, "docs": {"sections": []}}
    missing = []
    norm = {}
    for k, v in (uploads or {}).items():
        m = BLOB.search(str(v))
        if m:
            norm[os.path.abspath(k) if os.path.isabs(k) else k.replace("\\", "/")] = m.group(1)
    for x in plan:
        rel = f"{x['group']}/{x['name']}"
        blob = norm.get(x["path"]) or norm.get(rel) or norm.get(f"assets/{rel}") or norm.get(f"project/assets/{rel}") \
            or norm.get(x["name"])
        if not blob:
            missing.append(rel)
            continue
        g = idx["assetGroups"].setdefault(x["group"], {"name": x["group"], "tile": "l" if x["group"] == "Logos" else "m",
                                                       "order": [], "files": {}})
        key = re.sub(r"[^A-Za-z0-9_./-]", lambda m: "~%02x" % ord(m.group(0)), x["name"])
        g["files"][key] = {"name": x["name"], "blob": blob, "size": x["size"], "type": x["type"]}
        if x["name"] not in g["order"]:
            g["order"].append(x["name"])
        if x["group"] not in idx["groups"]:
            idx["groups"].append(x["group"])
    idx["lastChange"] = {"by": by, "at": now, "via": via, "note": note or f"{title} brand system from the brand-kit skill"}
    write(os.path.join(project, "design-system.json"), json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    return {"index": os.path.join(project, "design-system.json"), "missing": missing,
            "assets": sum(len(g["files"]) for g in idx["assetGroups"].values())}


# ----------------------------------------------------------------------------- cli

def cli_ds(args):
    identitylib.utf8_console()
    r = build(args.set_dir, args.out)
    rep = r["report"]
    print(f"design system: {r['dir']}  (title {r['title']})")
    print(f"sections: README + {len(r['sections'])} · components: {', '.join(r['components'])}")
    print("assets: " + ", ".join(f"{g} {len(v)}" for g, v in r["assets"].items()) +
          f" → {r['uploads']} upload(s) in {r['batches']} batch(es): upload-plan.json")
    print(f"publish: {r['files']} file(s) in publish.json (index excluded; write it with ds-index, send it LAST)")
    for n in r["notes"][:6]:
        print(f"note: {n}")
    for f in rep["errors"][:10]:
        print(f"error: {f}")
    for f in rep["warnings"][:8]:
        print(f"warn: {f}")
    print("validate: ✔ passed" if not rep["errors"] else f"validate: {len(rep['errors'])} error(s)")
    if not args.no_render:
        try:
            print(f"look: {render_previews(r['dir'])}  (every preview, light and dark)")
        except Exception as exc:  # noqa: BLE001 - the sheet is a convenience
            print(f"note: preview sheet skipped ({exc})")
    return 0 if not rep["errors"] else 1


def cli_index(args):
    identitylib.utf8_console()
    with open(args.uploads, encoding="utf-8") as fh:
        up = json.load(fh)
    existing = None
    if args.existing:
        with open(args.existing, encoding="utf-8") as fh:
            existing = json.load(fh)
    r = write_index(args.ds_dir, up, by=args.by, via=args.via, note=args.note, title=args.title, existing=existing)
    print(f"index: {r['index']} ({r['assets']} asset record(s))")
    if r["missing"]:
        print(f"missing upload ids ({len(r['missing'])}): " + ", ".join(r["missing"][:12]))
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export a set as a claude.ai Design System artifact tree.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("set_dir")
    p.add_argument("--out")
    p.add_argument("--no-render", action="store_true")
    p.set_defaults(func=cli_ds)
    p = sub.add_parser("index")
    p.add_argument("ds_dir")
    p.add_argument("--uploads", required=True)
    p.add_argument("--by", default="Claude")
    p.add_argument("--via", default="Claude Code")
    p.add_argument("--note")
    p.add_argument("--title")
    p.add_argument("--existing", help="the current design-system.json (read right before) to merge into")
    p.set_defaults(func=cli_index)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())

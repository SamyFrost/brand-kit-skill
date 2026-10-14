#!/usr/bin/env python3
"""ds_validate.py - check a Design System artifact tree (WORK/design-system/<SET>/project/) before publishing.

  python3 ds_validate.py WORK/design-system/A

Errors (the page would drop or refuse something): tokens.json not in the list grammar, bad token names or
duplicates, colour values the page cannot read (named colours, var(), color-mix(), missing aliases), bad lengths,
type styles without a valid fontSize, other-family values outside the allowed characters, caps exceeded,
refused paths, previews without the line-1 marker or with frames/iframes, a Cover folder that is not bare,
files over 15 MiB, a missing README.md.
Warnings: text pairs under 4.5:1 in any theme, tokens without a usage note, a README that starts with a title,
uploads over 20 MB, more than 24 sections.
"""
import argparse
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import colorlib  # noqa: E402

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
FUNC = re.compile(r"^(rgb|rgba|hsl|hsla|oklch|oklab|lab|lch|color)\(\s*[^()]*\)$", re.I)
ALIAS = re.compile(r"^\{([A-Za-z0-9][A-Za-z0-9_.-]{0,63})\}$")
LENGTH = re.compile(r"^-?(?:\d+|\d*\.\d+)(?:px|rem|em|%)?$")
PLAIN = re.compile(r"^[A-Za-z0-9 #%(),./+_-]{1,200}$")
SHADOW_BAD = re.compile(r"var\(|url\(", re.I)
REFUSED = re.compile(r"(^|/)(\.[^/]+|node_modules|package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|bunfig\.toml|"
                     r"tsconfig\.json|deno\.json|CLAUDE\.md|AGENTS\.md|index\.html|SKILL\.md)(/|$)|(^|/)[^/]*~\d")
CAPS = {"themes": 8, "colors": 600, "families": 12, "groups": 12, "styles": 80, "other": 60, "other_families": 12}
CORE = ("color", "type", "spacing", "radius", "shadow", "name", "version", "meta")
PAIRS = [("text", "background"), ("text", "surface"), ("text", "surface-alt"), ("text-muted", "background"),
         ("on-primary", "primary"), ("on-accent", "accent")]


def _color_ok(v, names):
    if not isinstance(v, str):
        return False
    v = v.strip()
    if HEX.match(v) or (FUNC.match(v) and "var(" not in v.lower() and "color-mix" not in v.lower()):
        return True
    m = ALIAS.match(v)
    return bool(m and m.group(1) in names)


def check_tokens(tok, errors, warnings):
    if not isinstance(tok, dict):
        errors.append("tokens.json: not an object")
        return
    seen = set()

    def name_ok(fam, n):
        if not isinstance(n, str) or not NAME.match(n):
            errors.append(f"{fam}: bad token name {n!r}")
            return False
        if n in seen:
            errors.append(f"{fam}: duplicate token name {n!r} (names are shared across families)")
            return False
        seen.add(n)
        return True

    col = tok.get("color") or {}
    themes = [t.get("id") for t in col.get("themes") or []]
    if not themes:
        errors.append("color.themes: none")
    if len(themes) > CAPS["themes"]:
        errors.append(f"color.themes: {len(themes)} > {CAPS['themes']}")
    ctoks = col.get("tokens")
    if not isinstance(ctoks, list):
        errors.append("color.tokens: must be a LIST of {name, value, usage} (a name->value map shows empty)")
        ctoks = []
    if len(ctoks) > CAPS["colors"]:
        errors.append(f"color.tokens: {len(ctoks)} > {CAPS['colors']}")
    cnames = {t.get("name") for t in ctoks if isinstance(t, dict)}
    values = {th: {} for th in themes}
    for t in ctoks:
        n = t.get("name")
        if not name_ok("color", n):
            continue
        v = t.get("value")
        vals = v if isinstance(v, dict) else {themes[0] if themes else "light": v}
        for th, x in vals.items():
            if th not in themes:
                errors.append(f"color {n}: unknown theme {th!r}")
            elif not _color_ok(x, cnames - {n}):
                errors.append(f"color {n} ({th}): value {x!r} is not readable (hex, rgb()/oklch()… or an existing alias)")
            else:
                values[th][n] = x
        if not t.get("usage"):
            warnings.append(f"color {n}: no usage note")
    first = themes[0] if themes else None
    for th in themes:
        for fg, bg in PAIRS:
            a = values[th].get(fg) or values.get(first, {}).get(fg)
            b = values[th].get(bg) or values.get(first, {}).get(bg)
            if a and b and HEX.match(a) and HEX.match(b):
                r = colorlib.contrast_ratio(a, b)
                if r < 4.5:
                    warnings.append(f"contrast {th}: {fg} on {bg} is {r:.2f}:1 (< 4.5:1)")
    ty = tok.get("type") or {}
    fams = ty.get("families") or {}
    if len(fams) > CAPS["families"]:
        errors.append(f"type.families: {len(fams)} > {CAPS['families']}")
    for k, stack in fams.items():
        if not isinstance(stack, str) or len(stack) > 200 or re.search(r"[;{}<>\\()]", stack) or stack.count('"') % 2:
            errors.append(f"type.families.{k}: invalid stack {stack!r}")
    for f in ty.get("fonts") or []:
        if '"' in (f.get("family") or "") or "'" in (f.get("family") or ""):
            errors.append(f"type.fonts: family {f.get('family')!r} must be a bare name")
    groups = ty.get("groups") or []
    if len(groups) > CAPS["groups"]:
        errors.append(f"type.groups: {len(groups)} > {CAPS['groups']}")
    nstyles, snames = 0, set()
    for g in groups:
        for s in g.get("styles") or []:
            nstyles += 1
            if not NAME.match(str(s.get("name", ""))) or s.get("name") in snames:
                errors.append(f"type style {s.get('name')!r}: bad or duplicate name")
            snames.add(s.get("name"))
            if not LENGTH.match(str(s.get("fontSize", ""))):
                errors.append(f"type style {s.get('name')}: fontSize {s.get('fontSize')!r} drops the style")
            lh = str(s.get("lineHeight", "1.4"))
            if not (LENGTH.match(lh) or re.match(r"^\d*\.?\d+$", lh)):
                errors.append(f"type style {s.get('name')}: lineHeight {lh!r}")
            fam = s.get("family") or g.get("family")
            if fam and fam not in fams:
                errors.append(f"type style {s.get('name')}: family key {fam!r} not in type.families")
    if nstyles > CAPS["styles"]:
        errors.append(f"type styles: {nstyles} > {CAPS['styles']}")
    other = [k for k, v in tok.items() if k not in CORE and isinstance(v, dict)]
    if len(other) > CAPS["other_families"]:
        errors.append(f"{len(other)} extra token families > {CAPS['other_families']}")
    for fam in ["spacing", "radius", "shadow"] + other:
        body = tok.get(fam)
        if body is None:
            continue
        lst = body.get("tokens") if isinstance(body, dict) else None
        if not isinstance(lst, list):
            errors.append(f"{fam}: must be {{\"tokens\": [ ... ]}} (a list)")
            continue
        if len(lst) > CAPS["other"]:
            errors.append(f"{fam}: {len(lst)} tokens > {CAPS['other']}")
        for t in lst:
            n = t.get("name")
            if not name_ok(fam, n):
                continue
            v = t.get("value")
            if fam in ("spacing", "radius"):
                if not LENGTH.match(str(v)):
                    errors.append(f"{fam} {n}: {v!r} is not a length")
            elif fam == "shadow":
                for x in (v.values() if isinstance(v, dict) else [v]):
                    if not isinstance(x, str) or len(x) > 400 or SHADOW_BAD.search(x):
                        errors.append(f"shadow {n}: {x!r} not readable")
            else:
                if not PLAIN.match(str(v)) or str(v).count("(") != str(v).count(")") or SHADOW_BAD.search(str(v)):
                    errors.append(f"{fam} {n}: {v!r} outside the allowed characters")
            if not t.get("usage"):
                warnings.append(f"{fam} {n}: no usage note")


def validate(ds_dir):
    ds_dir = os.path.abspath(ds_dir)
    project = os.path.join(ds_dir, "project")
    errors, warnings = [], []
    if not os.path.isfile(os.path.join(project, "README.md")):
        errors.append("README.md missing (every reader starts there)")
    else:
        with open(os.path.join(project, "README.md"), encoding="utf-8") as fh:
            if fh.readline().startswith("# "):
                warnings.append("README.md starts with a title; the page already shows the system's name")
    tp = os.path.join(project, "tokens.json")
    if os.path.isfile(tp):
        try:
            with open(tp, encoding="utf-8") as fh:
                check_tokens(json.load(fh), errors, warnings)
        except ValueError as exc:
            errors.append(f"tokens.json: invalid JSON ({exc})")
        if os.path.getsize(tp) > 512 * 1024:
            errors.append("tokens.json > 512 KB")
    else:
        warnings.append("no tokens.json")
    n_files, sections = 0, 0
    for root, dirs, files in os.walk(project):
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, project).replace(os.sep, "/")
            n_files += 1
            if REFUSED.search(rel):
                errors.append(f"{rel}: refused path")
            if ".." in rel.split("/"):
                errors.append(f"{rel}: '..' in path")
            size = os.path.getsize(p)
            if size > 15 * 1024 * 1024:
                errors.append(f"{rel}: {size} bytes > 15 MiB")
            if rel.endswith(".md") and "/" not in rel and rel != "README.md":
                sections += 1
            if rel.startswith("components/") and fn == "preview.html":
                with open(p, encoding="utf-8") as fh:
                    text = fh.read()
                if not re.match(r"<!--\s*@dsCard\b[^>]*-->", text.splitlines()[0] if text else ""):
                    errors.append(f"{rel}: line 1 must be the <!-- @dsCard ... --> marker")
                if re.search(r"<(iframe|frame|object|embed|portal|noscript)\b", text, re.I):
                    errors.append(f"{rel}: frames/objects are not allowed in previews")
                if len(text.encode("utf-8")) > 256 * 1024:
                    errors.append(f"{rel}: preview > 256 KB")
                for m in re.finditer(r"""(?:src|href)=["']https?://([^"'/]+)/([^"']*)""", text):
                    host, path = m.group(1), m.group(2)
                    if host not in ("fonts.googleapis.com", "fonts.gstatic.com", "cdnjs.cloudflare.com",
                                    "cdn.jsdelivr.net", "unpkg.com"):
                        warnings.append(f"{rel}: external {host} will not load")
    cover = os.path.join(project, "components", "Cover")
    if os.path.isdir(cover):
        extra = [f for f in os.listdir(cover) if f != "preview.html"]
        if extra:
            errors.append(f"components/Cover must hold only preview.html (has {', '.join(extra)})")
    else:
        warnings.append("no components/Cover/preview.html")
    if sections > 24:
        warnings.append(f"{sections} sections > 24 (the rest stay files)")
    if n_files > 1008:
        errors.append(f"{n_files} files > 1008")
    plan = os.path.join(ds_dir, "upload-plan.json")
    if os.path.isfile(plan):
        with open(plan, encoding="utf-8") as fh:
            for x in json.load(fh).get("files") or []:
                lim = 2 * 1024 * 1024 if x["name"].endswith(".svg") else 20 * 1024 * 1024
                if x["size"] > lim:
                    errors.append(f"upload {x['group']}/{x['name']}: {x['size']} bytes over the upload limit")
    return {"errors": errors, "warnings": warnings, "files": n_files, "sections": sections}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a Design System artifact tree before publishing.")
    ap.add_argument("ds_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = validate(a.ds_dir)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        for x in r["errors"]:
            print(f"error: {x}")
        for x in r["warnings"]:
            print(f"warn: {x}")
        print(f"{r['files']} file(s), {r['sections']} section(s): " + ("✔ passed" if not r["errors"] else f"{len(r['errors'])} error(s)"))
    return 0 if not r["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())

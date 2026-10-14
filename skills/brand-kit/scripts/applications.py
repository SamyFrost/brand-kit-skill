#!/usr/bin/env python3
"""applications.py - the chosen set applied to real formats: social, video, stationery and merchandise.

  python3 brand.py apps WORK/sets/A [--only social,video] [--scale 1]

Reads identity.json, palette.json, logo/build/ and system.json (foundations + applications.copy) of one set and
renders one HTML file with a `.page` per application, then one PNG per page into WORK/applications/<SET>/:

  social      ig-post 1080², ig-portrait 1080x1350, story 1080x1920, linkedin 1200x627, youtube-thumb 1280x720,
              avatar 400², banner 1500x500
  video       title-card, lower-third, subtitles, end-card (1920x1080) + logo-sting.html (animated, loops)
  stationery  business card front/back (3.5x2 in at 300 dpi), letterhead and document cover (A4 at 96 dpi),
              email signature, two presentation slides
  merch       t-shirt, tote, mug, cap, sticker sheet, packaging, storefront sign (flat vector mock-ups)

Also writes pattern.svg (the brand pattern tile built from the mark) and applications.json (what was made, sizes,
findings). The probe measures text contrast on every page; a failing pair is a gate. Copy comes from the brand
(tagline, sentence, CTA) and system.json applications.copy; contact details the client has not given are filled
with clearly sample values and the page carries a small "sample data" tag.
"""
import argparse
import html as htmllib
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import colorlib  # noqa: E402
import identitylib  # noqa: E402
import presentlib as pl  # noqa: E402
import systemlib  # noqa: E402

e = htmllib.escape
GROUPS = ("social", "video", "stationery", "merch")


# ----------------------------------------------------------------------------- data

class Ctx:
    def __init__(self, set_dir):
        self.info = pl.load_set(set_dir)
        self.dir = self.info["dir"]
        self.ident = self.info["identity"]
        self.pal = self.info["palette"]
        self.brand = self.ident.get("brand") or {}
        self.name = self.brand.get("name") or "Brand"
        self.slug = pl.slug(self.name)
        self.sys = systemlib.load_system(self.dir, self.ident, self.pal)
        self.f = self.sys["foundations"]
        self.t = pl.theme(self.pal)
        self.g = {k: pl.ground_theme(self.pal, self.t, k) for k in ("light", "dark", "primary")}
        acc = pl.role_hex(self.pal, "accent") if self.pal else None
        self.g["accent"] = pl.ground_theme(self.pal, self.t, "accent") if acc else self.g["primary"]
        self.svgs = pl.logo_svgs(self.info)
        self.faces = pl.resolve_faces(self.ident, self.dir)
        bc = pl.brand_copy(self.brand)
        cp = dict(self.sys["applications"]["copy"])
        self.sample = []

        def pick(key, *alts, sample=None):
            v = cp.get(key)
            if v:
                return v
            for a in alts:
                if a:
                    return a
            if sample is not None:
                self.sample.append(key)
            return sample or ""
        tagline = self.brand.get("tagline") or ""
        sentence = bc.get("sentence") or ""
        self.copy = {
            "headline": pick("headline", tagline, sentence, sample=self.name),
            "subhead": pick("subhead", sentence if sentence != tagline else "", sample=""),
            "cta": pick("cta", bc.get("cta")),
            "handle": pick("handle", sample=f"@{self.slug.replace('-', '')}"),
            "website": pick("website", sample=f"{self.slug.replace('-', '')}.com"),
            "email": pick("email", sample=f"hello@{self.slug.replace('-', '')}.com"),
            "phone": pick("phone", sample="+00 000 000 000"),
            "address": pick("address", sample="Street 00, City"),
            "person_name": pick("person_name", sample="Alex Sample"),
            "person_role": pick("person_role", sample="Founder"),
            "tagline": tagline,
            "nav": bc.get("nav") or [],
        }
        self.pillars = [p.get("name") for p in (self.sys.get("messaging") or {}).get("pillars") or [] if p.get("name")]

    def tok(self, fam, name):
        for t in self.f.get(fam) or []:
            if t["name"] == name:
                v = t["value"]
                return v["light"] if isinstance(v, dict) else v
        return None

    def logo(self, ground, one_color=False):
        gt = self.g[ground]
        if one_color or ground not in ("light", "dark", "primary"):
            # a saturated ground: the whole logo in that ground's ink reads best
            src = self.svgs.get("primary")
            return pl.colorize(src, self.pal, gt["mode"], mono=gt["ink"]) if src else f'<span class="wm">{e(self.name)}</span>'
        svg = pl.logo_version(self.dir, gt)
        if not svg:
            src = self.svgs.get("primary")
            svg = pl.colorize(src, self.pal, gt["mode"]) if src else ""
        else:
            svg = pl.colorize(svg, self.pal, gt["mode"]) if "data-color" in svg else _strip(svg)
        return svg or f'<span class="wm">{e(self.name)}</span>'

    def mark(self, ink):
        """The symbol (or monogram / small mark) in one ink."""
        src = self.svgs.get("small") or self.svgs.get("symbol") or self.svgs.get("monogram")
        if not src:
            return f'<span class="wm" style="color:{ink}">{e(self.name[:1])}</span>'
        return pl.colorize(src, self.pal, mono=ink)

    def mark_accented(self, ink, ground):
        """The small mark in `ink`, keeping its non-primary parts (an accent detail) in their palette colour when
        that colour holds 3:1 on `ground`."""
        src = self.svgs.get("small") or self.svgs.get("symbol") or self.svgs.get("monogram")
        if not src:
            return self.mark(ink)

        def paint(m):
            role = m.group(1)
            hx = pl.role_hex(self.pal, role) if role not in ("primary", "text") else None
            if not hx or colorlib.contrast_ratio(hx, ground) < 3:
                hx = ink
            return f'data-color="{hx}"'
        import re as _re
        src = _re.sub(r'data-color="([^"]+)"', paint, src)
        svg = pl.colorize(src, self.pal, default=ink)
        return _re.sub(r'<([a-zA-Z]+)\b([^>]*)data-color="(#[0-9a-fA-F]{6})"',
                       lambda m: f'<{m.group(1)}{_re.sub(r" fill=\"[^\"]*\"", "", m.group(2))}fill="{m.group(3)}" data-color="{m.group(3)}"', svg)


def _strip(svg):
    svg = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>|<!--.*?-->", "", svg, flags=re.S).strip()
    return re.sub(r'\sid="[^"]*"', "", svg)


def _mark_src(c):
    return c.svgs.get("small") or c.svgs.get("symbol") or c.svgs.get("monogram")


# ----------------------------------------------------------------------------- pattern

def pattern_svg(c, ground_hex, ink_hex, tile=120):
    """A repeat tile of the mark: rows offset by half a tile (brick), rotation and gap from system.graphic.pattern."""
    pat = (c.sys.get("graphic") or {}).get("pattern") or {}
    src = _mark_src(c)
    scale = float(pat.get("scale") or 1.0)
    rot = float(pat.get("rotate") or 0)
    gap = float(pat.get("gap") or 1.0)
    op = float(pat.get("opacity") or 1.0)
    if not src:
        return ""
    inner = pl.colorize(src, c.pal, mono=ink_hex)
    vb = pl.viewbox(inner) or [0, 0, 100, 100]
    body = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", inner.strip())
    s = tile * 0.5 * scale / max(vb[2], vb[3])
    w = tile * (1 + gap) / 1.5
    cells = []
    for row in range(2):
        for col in range(2):
            x = col * w + (w / 2 if row else 0)
            y = row * w
            cells.append(f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot:g} {vb[2] * s / 2:.1f} {vb[3] * s / 2:.1f}) '
                         f'scale({s:.4f}) translate({-vb[0]:g} {-vb[1]:g})" opacity="{op:g}">{body}</g>')
    size = 2 * w
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size:.0f}" height="{size:.0f}" '
            f'viewBox="0 0 {size:.1f} {size:.1f}"><rect width="100%" height="100%" fill="{ground_hex}"/>'
            f'<g transform="translate({w / 4:.1f} {w / 4:.1f})">{"".join(cells)}</g>'
            # the brick offset leaves the right half-cell of row 2 at x = 2w - w/2: repeat it on the left edge
            f'<g transform="translate({w / 4 - 2 * w:.1f} {w / 4:.1f})">{cells[3]}</g></svg>')


def pattern_css(svg):
    from urllib.parse import quote
    return f"url('data:image/svg+xml,{quote(svg)}')" if svg else "none"


# ----------------------------------------------------------------------------- pages

def page(name, group, w, h, body, cls="", style="", sample=False):
    tag = '<span class="sample">sample data</span>' if sample else ""
    return (f'<section class="page {cls}" data-name="{name}" data-group="{group}" '
            f'style="width:{w}px;height:{h}px;{style}">{body}{tag}</section>')


def gvars(gt):
    return pl.ground_css(gt)


def social_pages(c, P):
    cp, out = c.copy, []
    gp, gl, gd = c.g["primary"], c.g["light"], c.g["dark"]
    out.append(page("ig-post", "social", 1080, 1080, f"""
      <div class="pat" style="background-image:{P['primary']};inset:0 0 auto auto;width:400px;height:320px"></div>
      <div class="pad" style="padding:96px">
        <div class="logo" style="height:64px">{c.logo('primary')}</div>
        <h1 class="disp" style="font-size:{min(104, 2600 // max(12, len(cp['headline'])))}px;margin-top:auto;max-width:820px">{e(cp['headline'])}</h1>
        <p class="txt" style="font-size:30px;color:var(--g-muted);max-width:760px">{e(cp['subhead'])}</p>
        <div class="row" style="margin-top:40px"><span class="txt" style="font-size:26px">{e(cp['handle'])}</span></div>
      </div>""", style=gvars(gp), sample="handle" in c.sample))
    quote_line = (c.sys["voice"].get("sample_lines") or [cp["subhead"] or cp["headline"]])[0]
    out.append(page("ig-portrait", "social", 1080, 1350, f"""
      <div class="pad" style="padding:110px 96px">
        <div class="rule" style="width:120px;height:12px;background:var(--g-rule)"></div>
        <p class="disp" style="font-size:{min(86, 3000 // max(16, len(quote_line)))}px;margin-top:80px">{e(quote_line)}</p>
        <div class="row" style="margin-top:auto;justify-content:space-between;align-items:flex-end">
          <div class="logo" style="height:56px">{c.logo('light')}</div>
          <span class="txt" style="font-size:24px;color:var(--g-muted)">{e(cp['website'])}</span></div>
      </div>""", style=gvars(gl), sample="website" in c.sample))
    out.append(page("story", "social", 1080, 1920, f"""
      <div class="pat" style="background-image:{P['dark']};inset:0 0 auto 0;height:180px;opacity:var(--o-muted)"></div>
      <div class="pad" style="padding:220px 96px 260px">
        <div class="logo" style="height:72px">{c.logo('dark')}</div>
        <h1 class="disp" style="font-size:{min(132, 3600 // max(12, len(cp['headline'])))}px;margin-top:auto">{e(cp['headline'])}</h1>
        <p class="txt" style="font-size:36px;color:var(--g-muted)">{e(cp['subhead'])}</p>
        {f'<div class="btn" style="font-size:38px;margin-top:64px;padding:30px 56px">{e(cp["cta"])}</div>' if cp['cta'] else ''}
      </div>""", style=gvars(gd)))
    out.append(page("linkedin-post", "social", 1200, 627, f"""
      <div class="split">
        <div class="pad" style="padding:72px;flex:1.4">
          <span class="over" style="font-size:20px;color:var(--g-muted)">{e(c.name)}</span>
          <h1 class="disp" style="font-size:{min(64, 1700 // max(12, len(cp['headline'])))}px;margin-top:auto">{e(cp['headline'])}</h1>
          <span class="txt" style="font-size:22px;margin-top:24px">{e(cp['website'])}</span></div>
        <div style="flex:1;background-color:{gp['bg']};background-image:{P['primary']};display:grid;place-items:center">
          <div class="mark" style="height:200px">{c.mark(gp['ink'])}</div></div>
      </div>""", style=gvars(gl), sample="website" in c.sample))
    out.append(page("youtube-thumb", "social", 1280, 720, f"""
      <div class="pad" style="padding:64px 72px">
        <div class="row" style="justify-content:space-between"><div class="logo" style="height:48px">{c.logo('accent')}</div>
          <span class="chip" style="font-size:22px">{e((c.pillars or [c.copy['tagline'] or c.name])[0])}</span></div>
        <h1 class="disp" style="font-size:{min(120, 2400 // max(10, len(cp['headline'])))}px;margin-top:auto;max-width:1000px">{e(cp['headline'])}</h1>
      </div>""", style=gvars(c.g["accent"])))
    out.append(page("avatar", "social", 400, 400, f"""
      <div style="position:absolute;inset:0;display:grid;place-items:center">
        <div class="mark" style="height:200px">{c.mark_accented(gp['ink'], gp['bg'])}</div></div>""", style=gvars(gp)))
    out.append(page("banner", "social", 1500, 500, f"""
      <div class="pat" style="background-image:{P['primary']};inset:0 0 0 auto;width:560px"></div>
      <div class="pad" style="padding:0 96px;justify-content:center">
        <div class="logo" style="height:80px">{c.logo('primary')}</div>
        <p class="txt" style="font-size:30px;margin-top:28px;color:var(--g-muted)">{e(cp['tagline'] or cp['headline'])}</p>
      </div>""", style=gvars(gp)))
    return out


def video_pages(c, P):
    cp, out = c.copy, []
    gp, gd = c.g["primary"], c.g["dark"]
    foot = ("background:repeating-linear-gradient(135deg,#6b6b6b 0 40px,#5f5f5f 40px 80px)")
    out.append(page("title-card", "video", 1920, 1080, f"""
      <div class="pat" style="background-image:{P['primary']};inset:0;opacity:.18"></div>
      <div class="pad" style="padding:140px 160px;justify-content:center">
        <span class="over" style="font-size:28px;color:var(--g-muted)">{e(c.name)}</span>
        <h1 class="disp" style="font-size:{min(150, 3600 // max(12, len(cp['headline'])))}px;margin-top:24px;max-width:1500px">{e(cp['headline'])}</h1>
        <div class="rule" style="width:180px;height:14px;background:var(--g-rule);margin-top:56px"></div>
      </div>""", style=gvars(gp)))
    gl3 = c.g["primary"]
    out.append(page("lower-third", "video", 1920, 1080, f"""
      <div style="position:absolute;inset:0;{foot}"></div>
      <span class="mocklabel">footage</span>
      <div style="position:absolute;left:120px;bottom:120px;display:flex;align-items:stretch;{gvars(gl3)}">
        <div style="background:var(--g-rule);width:14px"></div>
        <div style="background:var(--g-bg);padding:28px 44px 30px">
          <div class="disp" style="font-size:52px;color:var(--g-ink)">{e(cp['person_name'])}</div>
          <div class="txt" style="font-size:28px;color:var(--g-muted);margin-top:6px">{e(cp['person_role'])} · {e(c.name)}</div>
        </div></div>
      <div class="mark" style="position:absolute;right:96px;top:84px;height:72px;opacity:.9">{c.mark('#ffffff')}</div>
      """, style="background:#5f5f5f", sample="person_name" in c.sample))
    sub = (c.sys["voice"].get("sample_lines") or [cp["subhead"] or cp["headline"]])[0]
    out.append(page("subtitles", "video", 1920, 1080, f"""
      <div style="position:absolute;inset:0;{foot}"></div><span class="mocklabel">footage</span>
      <div style="position:absolute;left:0;right:0;bottom:110px;display:grid;place-items:center">
        <span class="txt" style="font-size:48px;font-weight:var(--text-weight-2);color:#ffffff;background:rgba(0,0,0,.72);
          padding:10px 28px;border-radius:var(--r-sm);max-width:1500px;text-align:center">{e(sub)}</span></div>""",
        style="background:#5f5f5f"))
    out.append(page("end-card", "video", 1920, 1080, f"""
      <div class="pad" style="padding:140px;align-items:center;justify-content:center;text-align:center">
        <div class="logo" style="height:140px">{c.logo('dark')}</div>
        <p class="txt" style="font-size:40px;margin-top:56px;color:var(--g-muted)">{e(cp['tagline'] or cp['headline'])}</p>
        <div class="row" style="gap:40px;margin-top:72px;justify-content:center">
          {f'<span class="btn" style="font-size:34px;padding:24px 48px">{e(cp["cta"])}</span>' if cp['cta'] else ''}
          <span class="txt" style="font-size:34px">{e(cp['website'])}</span></div>
      </div>""", style=gvars(gd), sample="website" in c.sample))
    return out


def stationery_pages(c, P):
    cp, out = c.copy, []
    gp, gl = c.g["primary"], c.g["light"]
    smp = any(k in c.sample for k in ("person_name", "email", "phone", "website", "address"))
    out.append(page("business-card-front", "stationery", 1050, 600, f"""
      <div class="pad" style="padding:72px 80px">
        <div class="logo" style="height:64px">{c.logo('light')}</div>
        <div style="margin-top:auto">
          <div class="disp" style="font-size:44px">{e(cp['person_name'])}</div>
          <div class="txt" style="font-size:24px;color:var(--g-muted);margin-top:4px">{e(cp['person_role'])}</div>
          <div class="txt" style="font-size:22px;margin-top:28px;line-height:1.5">{e(cp['email'])}<br>{e(cp['phone'])}<br>{e(cp['website'])}</div>
        </div></div>""", cls="card", style=gvars(gl), sample=smp))
    out.append(page("business-card-back", "stationery", 1050, 600, f"""
      <div class="pat" style="background-image:{P['primary']};inset:0"></div>
      <div style="position:absolute;inset:0;display:grid;place-items:center">
        <div style="background:{gl['bg']};padding:44px 56px;border-radius:var(--r-md)"><div class="logo" style="height:84px">{c.logo('light')}</div></div></div>""",
        cls="card", style=gvars(gp)))
    out.append(page("letterhead", "stationery", 794, 1123, f"""
      <div class="pad" style="padding:64px 72px">
        <div class="row" style="justify-content:space-between;align-items:flex-start">
          <div class="logo" style="height:40px">{c.logo('light')}</div>
          <div class="txt" style="font-size:11px;line-height:1.6;text-align:right;color:var(--g-muted)">{e(cp['address'])}<br>{e(cp['email'])} · {e(cp['phone'])}<br>{e(cp['website'])}</div></div>
        <div class="txt" style="font-size:12px;color:var(--g-muted);margin-top:96px">00.00.0000</div>
        <div class="txt" style="font-size:13px;line-height:1.7;margin-top:28px">
          <div class="lines">{''.join('<i></i>' for _ in range(16))}</div></div>
        <div class="rule" style="margin-top:auto;height:6px;width:100%;background:var(--g-rule)"></div>
      </div>""", style=gvars(gl), sample=smp))
    out.append(page("document-cover", "stationery", 794, 1123, f"""
      <div class="pat" style="background-image:{P['primary']};inset:auto 0 0 0;height:380px"></div>
      <div class="pad" style="padding:80px 72px">
        <div class="logo" style="height:44px">{c.logo('primary')}</div>
        <span class="over" style="font-size:13px;margin-top:200px;color:var(--g-muted)">{e(c.name)} · 0000</span>
        <h1 class="disp" style="font-size:52px;margin-top:16px;max-width:600px">{e(cp['headline'])}</h1>
        <p class="txt" style="font-size:17px;color:var(--g-muted);max-width:520px">{e(cp['subhead'])}</p>
      </div>""", style=gvars(gp)))
    out.append(page("email-signature", "stationery", 600, 180, f"""
      <div class="row" style="position:absolute;inset:0;padding:24px 28px;gap:24px;align-items:center">
        <div class="mark" style="height:64px">{c.mark(c.g['light']['btn'])}</div>
        <div style="border-left:2px solid var(--g-rule);padding-left:20px">
          <div class="disp" style="font-size:20px">{e(cp['person_name'])}</div>
          <div class="txt" style="font-size:13px;color:var(--g-muted)">{e(cp['person_role'])} · {e(c.name)}</div>
          <div class="txt" style="font-size:13px;margin-top:8px">{e(cp['email'])} · {e(cp['phone'])}</div>
          <div class="txt" style="font-size:13px;color:var(--g-btn)">{e(cp['website'])}</div></div></div>""",
        style=gvars(gl), sample=smp))
    out.append(page("slide-title", "stationery", 1920, 1080, f"""
      <div class="pat" style="background-image:{P['primary']};inset:0 0 0 auto;width:640px"></div>
      <div class="pad" style="padding:140px 160px;max-width:1280px">
        <div class="logo" style="height:64px">{c.logo('primary')}</div>
        <h1 class="disp" style="font-size:{min(120, 3000 // max(12, len(cp['headline'])))}px;margin-top:auto">{e(cp['headline'])}</h1>
        <p class="txt" style="font-size:36px;color:var(--g-muted)">{e(cp['subhead'])}</p>
      </div>""", style=gvars(gp)))
    pill = c.pillars[:3] or [c.copy["tagline"] or c.name]
    cols = "".join(f'<div style="flex:1;border-top:8px solid var(--g-rule);padding-top:32px"><div class="disp" style="font-size:44px">{e(p)}</div>'
                   f'<div class="lines" style="margin-top:28px">{"<i></i>" * 4}</div></div>' for p in pill)
    out.append(page("slide-content", "stationery", 1920, 1080, f"""
      <div class="pad" style="padding:120px 160px">
        <span class="over" style="font-size:24px;color:var(--g-muted)">{e(c.name)}</span>
        <h2 class="disp" style="font-size:80px;margin-top:20px">{e(cp['headline'])}</h2>
        <div class="row" style="gap:72px;margin-top:auto;align-items:flex-start">{cols}</div>
        <div class="row" style="margin-top:80px;justify-content:space-between"><div class="logo" style="height:36px">{c.logo('light')}</div>
          <span class="txt" style="font-size:22px;color:var(--g-muted)">02</span></div>
      </div>""", style=gvars(gl)))
    return out


# flat silhouettes for merchandise mock-ups (viewBox 0 0 1000 1000)
SHIRT = ("M330 120 L420 90 Q500 150 580 90 L670 120 L860 230 L790 380 L700 340 L700 900 L300 900 L300 340 "
         "L210 380 L140 230 Z")
TOTE = "M220 330 L780 330 L820 920 L180 920 Z"
TOTE_H = "M370 340 Q370 140 500 140 Q630 140 630 340"
CAP = "M180 620 Q180 300 500 290 Q820 300 820 620 Z"
CAP_B = "M120 620 L880 620 Q900 690 800 700 L200 700 Q100 690 120 620 Z"


def merch_pages(c, P):
    out = []
    gp, gl, gd = c.g["primary"], c.g["light"], c.g["dark"]
    garment = gd["bg"]
    out.append(page("t-shirt", "merch", 1200, 1200, f"""
      <svg viewBox="0 0 1000 1000" style="position:absolute;inset:100px"><path d="{SHIRT}" fill="{garment}"/></svg>
      <div style="position:absolute;left:0;right:0;top:420px;display:grid;place-items:center">
        <div class="logo" style="height:110px;max-width:360px">{c.logo('dark')}</div></div>
      <span class="mocklabel">mock-up</span>""", style=gvars(gl)))
    out.append(page("tote-bag", "merch", 1200, 1200, f"""
      <svg viewBox="0 0 1000 1000" style="position:absolute;inset:100px"><path d="{TOTE_H}" fill="none" stroke="{gp['bg']}" stroke-width="34"/>
        <path d="{TOTE}" fill="{gp['bg']}"/></svg>
      <div style="position:absolute;left:0;right:0;top:620px;display:grid;place-items:center;{gvars(gp)}">
        <div class="logo" style="height:100px;max-width:420px">{c.logo('primary')}</div></div>
      <span class="mocklabel">mock-up</span>""", style=gvars(gl)))
    out.append(page("mug", "merch", 1200, 900, f"""
      <div style="position:absolute;left:300px;top:180px;width:520px;height:600px;background:{gl['bg']};border-radius:20px 20px 60px 60px;
        box-shadow:inset -40px 0 60px rgba(0,0,0,.08), 0 30px 60px rgba(0,0,0,.18)"></div>
      <div style="position:absolute;left:790px;top:300px;width:170px;height:300px;border:44px solid {gl['bg']};border-left:0;border-radius:0 150px 150px 0;
        box-shadow:0 20px 40px rgba(0,0,0,.12)"></div>
      <div style="position:absolute;left:300px;top:180px;width:520px;height:600px;display:grid;place-items:center;{gvars(gl)}">
        <div class="mark" style="height:220px">{c.mark(gl['btn'])}</div></div>
      <span class="mocklabel">mock-up</span>""", style=gvars(gp)))
    out.append(page("cap", "merch", 1200, 900, f"""
      <svg viewBox="0 0 1000 1000" style="position:absolute;left:100px;top:-40px;width:1000px;height:1000px">
        <path d="{CAP}" fill="{gp['bg']}"/><path d="{CAP_B}" fill="{gp['bg']}" opacity=".85"/></svg>
      <div style="position:absolute;left:0;right:0;top:330px;display:grid;place-items:center">
        <div class="mark" style="height:150px">{c.mark(gp['ink'])}</div></div>
      <span class="mocklabel">mock-up</span>""", style=gvars(gl)))
    stickers = [(gp, c.mark(gp["ink"]), "50%"), (gl, c.logo("light"), "var(--r-lg)"), (c.g["accent"], c.mark(c.g["accent"]["ink"]), "50%"),
                (gd, c.logo("dark"), "var(--r-lg)")]
    st = "".join(f'<div style="background:{g["bg"]};border-radius:{r};display:grid;place-items:center;padding:56px;'
                 f'box-shadow:0 0 0 14px #ffffff, 0 18px 36px rgba(0,0,0,.18)"><div class="logo" style="height:120px;max-width:300px">{m}</div></div>'
                 for g, m, r in stickers)
    out.append(page("stickers", "merch", 1200, 1200, f"""
      <div style="position:absolute;inset:120px;display:grid;grid-template-columns:1fr 1fr;gap:110px">{st}</div>""",
        style=gvars(c.g["light"]) + f"background:{c.t['paper']}"))
    out.append(page("packaging", "merch", 1200, 1200, f"""
      <div style="position:absolute;left:260px;top:200px;width:680px;height:780px;background-color:{gp['bg']};background-image:{P['primary']};
        border-radius:var(--r-sm);box-shadow:0 40px 80px rgba(0,0,0,.25)"></div>
      <div style="position:absolute;left:330px;top:420px;width:540px;padding:52px 40px;background:{gl['bg']};border-radius:var(--r-md);
        display:flex;flex-direction:column;align-items:center;gap:22px;{gvars(gl)}">
        <div class="logo" style="height:90px;max-width:440px">{c.logo('light')}</div>
        <span class="txt" style="font-size:24px;color:var(--g-muted);text-align:center">{e(c.copy['tagline'] or c.copy['headline'])}</span></div>
      <span class="mocklabel">mock-up</span>""", style=gvars(gl) + f"background:{c.t['paper']}"))
    out.append(page("storefront-sign", "merch", 1600, 900, f"""
      <div style="position:absolute;left:0;right:0;top:0;height:420px;background:#cfcac2"></div>
      <div style="position:absolute;left:180px;right:180px;top:140px;height:260px;background:{gd['bg']};border-radius:var(--r-sm);
        display:grid;place-items:center;box-shadow:0 30px 50px rgba(0,0,0,.3);{gvars(gd)}">
        <div class="logo" style="height:130px;max-width:1000px">{c.logo('dark')}</div></div>
      <div style="position:absolute;left:0;right:0;top:420px;bottom:0;background:#8b8781"></div>
      <span class="mocklabel">mock-up</span>""", style="background:#8b8781"))
    return out


# ----------------------------------------------------------------------------- html

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#e9e9e9;font-family:var(--font-text);color:#111;-webkit-font-smoothing:antialiased}
.page{position:relative;overflow:hidden;background:var(--g-bg);color:var(--g-ink);margin:0 0 40px 0}
.pad{position:absolute;inset:0;display:flex;flex-direction:column;gap:20px}
.row{display:flex;gap:16px;align-items:center}
.split{position:absolute;inset:0;display:flex}
.split>.pad{position:relative}
.disp{font-family:var(--font-display);font-weight:var(--display-weight);letter-spacing:var(--display-track);
  line-height:1.04;color:var(--g-ink);text-wrap:balance}
.txt{font-family:var(--font-text);font-weight:var(--text-weight);letter-spacing:var(--text-track);line-height:1.4}
.over{font-family:var(--font-text);font-weight:var(--text-weight-2);letter-spacing:.08em;text-transform:uppercase}
.btn{display:inline-block;align-self:flex-start;background:var(--g-btn);color:var(--g-on-btn);border-radius:var(--r-md);
  font-family:var(--font-text);font-weight:var(--text-weight-2);line-height:1.1}
.chip{border:2px solid var(--g-ink);border-radius:var(--r-pill);padding:8px 22px;font-weight:var(--text-weight-2)}
.logo,.mark{display:flex;align-items:center}
.logo svg,.mark svg{height:100%;width:auto;max-width:100%;display:block}
.wm{font-family:var(--font-display);font-weight:var(--display-weight);font-size:48px}
.pat{position:absolute;background-repeat:repeat;background-size:auto}
.lines i{display:block;height:9px;margin:0 0 14px;background:currentColor;opacity:.12;border-radius:5px}
.lines i:nth-child(4n){width:62%}
.sample,.mocklabel{position:absolute;right:12px;bottom:10px;font:600 12px/1 system-ui,sans-serif;letter-spacing:.06em;
  text-transform:uppercase;color:#111111;background:#ffffff;padding:5px 7px;border-radius:3px}
.mocklabel{left:14px;top:12px;right:auto;bottom:auto}
.card{border-radius:0}
"""


def foundations_css(c):
    f = c.f
    r = {x["name"]: x["value"] for x in f["radius"]}
    op = {x["name"]: x["value"] for x in f["opacity"]}
    return (f"--r-sm:{r.get('radius-sm', '4px')};--r-md:{r.get('radius-md', '8px')};--r-lg:{r.get('radius-lg', '16px')};"
            f"--r-pill:{r.get('radius-pill', '999px')};--o-muted:{op.get('opacity-muted', '0.64')};")


def build_html(c, groups, html_dir):
    P = {}
    for k in ("primary", "dark", "light"):
        g = c.g[k]
        ink = g["rule"] if colorlib.delta_e_ok(g["rule"], g["bg"]) > 0.08 else g["ink"]
        P[k] = pattern_css(pattern_svg(c, g["bg"], ink))
    pages = []
    if "social" in groups:
        pages += social_pages(c, P)
    if "video" in groups:
        pages += video_pages(c, P)
    if "stationery" in groups:
        pages += stationery_pages(c, P)
    if "merch" in groups:
        pages += merch_pages(c, P)
    rv = pl.role_vars(c.ident)
    lang = e(pl.lang_of(c.brand))
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{e(c.name)} applications</title>'
            f"<style>{pl.font_face_css(c.faces, html_dir)}\n:root{{{rv}{foundations_css(c)}}}{CSS}</style></head>"
            f"<body>{''.join(pages)}</body></html>"), len(pages)


def sting_html(c):
    """Animated logo sting: the mark arrives with the brand's expressive easing, then the wordmark. Loops."""
    d = c.tok("duration", "duration-sting") or "2000ms"
    ease = c.tok("easing", "ease-expressive") or "cubic-bezier(0.2,0,0,1)"
    enter = c.tok("easing", "ease-enter") or "ease-out"
    gp = c.g["primary"]
    mark = c.mark(gp["ink"])
    wm_src = c.svgs.get("wordmark")
    wm = pl.colorize(wm_src, c.pal, mono=gp["ink"]) if wm_src else f'<span class="wm" style="color:{gp["ink"]}">{e(c.name)}</span>'
    rv = pl.role_vars(c.ident)
    faces = []
    for f in c.ident.get("type", {}).values() if isinstance(c.ident.get("type"), dict) else []:
        if isinstance(f, dict) and f.get("source") == "google":
            faces.append(f["family"].replace(" ", "+"))
    gf = (f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{"&".join("family=" + x for x in dict.fromkeys(faces))}&display=swap">'
          if faces else "")
    return f"""<!doctype html><html lang="{e(pl.lang_of(c.brand))}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(c.name)} logo sting</title>{gf}
<style>
:root{{{rv}--dur:{d};--ease:{ease};--enter:{enter}}}
html,body{{margin:0;height:100%;background:{gp['bg']}}}
.stage{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;gap:4vmin;overflow:hidden}}
.m{{height:22vmin;animation:mark calc(var(--dur) * 2) var(--ease) infinite both}}
.w{{height:12vmin;clip-path:inset(0 100% 0 0);animation:word calc(var(--dur) * 2) var(--enter) infinite both}}
.m svg,.w svg{{height:100%;width:auto;display:block}}
.wm{{font-family:var(--font-display);font-weight:var(--display-weight);font-size:12vmin;line-height:1}}
@keyframes mark{{0%{{transform:scale(.4) rotate(-90deg);opacity:0}}25%{{transform:none;opacity:1}}85%{{opacity:1}}100%{{opacity:0}}}}
@keyframes word{{0%,20%{{clip-path:inset(0 100% 0 0)}}45%{{clip-path:inset(0 0 0 0)}}85%{{opacity:1}}100%{{opacity:0;clip-path:inset(0 0 0 0)}}}}
@media (prefers-reduced-motion:reduce){{.m,.w{{animation:none;clip-path:none}}}}
</style></head><body><div class="stage" role="img" aria-label="{e(c.name)}"><div class="m">{mark}</div><div class="w">{wm}</div></div>
<!-- {e(c.name)} logo sting: duration {d} (duration-sting), easing {ease} (ease-expressive). Record 1920x1080 for video. -->
</body></html>"""


def build(set_dir, groups=GROUPS, scale=1.0):
    import render_png
    c = Ctx(set_dir)
    sid = (c.ident.get("set") or {}).get("id") or "A"
    out = os.path.join(c.info["work"], "applications", sid)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(out):
        if fn.endswith(".png"):
            os.remove(os.path.join(out, fn))
    cache = os.path.join(c.info["work"], ".cache")
    os.makedirs(cache, exist_ok=True)
    html_path = os.path.join(cache, f"applications-{sid}.html")
    html, n = build_html(c, groups, cache)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    res = render_png.render(html_path, out, 1920, 1080, pdf=False, pages=True, probe=True, scale=scale)
    findings = render_png.probe_findings(res, pl.expected_fonts(c.faces), None, None, component="applications")
    # pattern tile and logo sting as standalone files
    gp = c.g["primary"]
    pat = pattern_svg(c, gp["bg"], gp["rule"] if colorlib.delta_e_ok(gp["rule"], gp["bg"]) > 0.08 else gp["ink"])
    files = {}
    if pat:
        files["pattern"] = os.path.join(out, "pattern.svg")
        with open(files["pattern"], "w", encoding="utf-8") as fh:
            fh.write(pat)
    files["logo_sting"] = os.path.join(out, "logo-sting.html")
    with open(files["logo_sting"], "w", encoding="utf-8") as fh:
        fh.write(sting_html(c))
    pages = res.get("pages") or []
    if len(pages) != n:
        findings.append(identitylib.finding("apps-page-count", "applications", "gate",
                                            f"{len(pages)} PNGs for {n} applications", measured=len(pages), threshold=n))
    manifest = {"schema": "brand-kit/applications@1", "set": sid, "groups": list(groups),
                "pages": [{"file": os.path.basename(p), "name": re.sub(r"^\d+-|\.png$", "", os.path.basename(p))} for p in pages],
                "files": {k: os.path.basename(v) for k, v in files.items()}, "sample_fields": c.sample,
                "findings": findings}
    with open(os.path.join(out, "applications.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    gates = [f for f in findings if f["severity"] == "gate"]
    return {"dir": out, "pages": pages, "files": files, "findings": findings, "passed": not gates, "sample": c.sample,
            "html": html_path}


def cli_apps(args):
    identitylib.utf8_console()
    groups = tuple(g.strip() for g in (args.only or ",".join(GROUPS)).split(",") if g.strip())
    bad = [g for g in groups if g not in GROUPS]
    if bad:
        print(f"error: unknown group(s) {', '.join(bad)}; choose from {', '.join(GROUPS)}", file=sys.stderr)
        return 2
    r = build(args.set_dir, groups, scale=args.scale)
    print(f"applications: {r['dir']} ({len(r['pages'])} PNG)")
    for k, v in r["files"].items():
        print(f"{k}: {v}")
    if r["sample"]:
        print(f"sample data on the pages for: {', '.join(r['sample'])} (fill system.json applications.copy)")
    gates = [f for f in r["findings"] if f["severity"] == "gate"]
    for f in gates[:8]:
        print(f"gate {f['id']}: {f['message']}")
    print("gates: ✔ none" if not gates else f"gates: {len(gates)} failed")
    return 0 if r["passed"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render the chosen set on social, video, stationery and merch formats.")
    ap.add_argument("set_dir")
    ap.add_argument("--only", help="comma list of groups: social,video,stationery,merch")
    ap.add_argument("--scale", type=float, default=1.0)
    return cli_apps(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())

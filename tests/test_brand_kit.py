"""brand-kit additions: systemlib (foundations from axes, system.json merge), ds_export (tokens.json in the Design
System grammar, brand book, components, index), ds_validate, applications (render, when Chromium is present).

Runs on a copy of templates/demo with fixture fonts (typelib off, nothing downloaded).
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "brand-kit")
SCRIPTS = os.path.join(SKILL, "scripts")
DEMO = os.path.join(SKILL, "templates", "demo")
sys.dont_write_bytecode = True
sys.path.insert(0, SCRIPTS)
import ds_export  # noqa: E402
import ds_validate  # noqa: E402
import presentlib as pl  # noqa: E402
import render_png as rp  # noqa: E402
import systemlib  # noqa: E402

BROWSER = rp.find_browser()


def _copy_demo(tmp):
    work = os.path.join(tmp, "ferrow")
    shutil.copytree(DEMO, work)
    return work


class Foundations(unittest.TestCase):
    def ident(self, **axes):
        return {"axes": axes, "type": {"display": {"family": "X", "weights": [700], "tracking": -20},
                                       "text": {"family": "Y", "weights": [400, 600]}}}

    def test_loud_brand_gets_a_wider_scale_than_a_quiet_one(self):
        loud = systemlib.foundations(self.ident(quiet_loud=2), None)["type_scale"]
        quiet = systemlib.foundations(self.ident(quiet_loud=-2), None)["type_scale"]
        self.assertGreater(loud["ratio"], quiet["ratio"])
        size = {s["name"]: int(s["fontSize"][:-2]) for s in loud["styles"]}
        self.assertGreater(size["display-xl"], size["h1"])
        self.assertEqual(size["body"], 16)

    def test_round_for_warm_playful_square_for_cool_serious(self):
        r = lambda f: next(int(t["value"][:-2]) for t in f["radius"] if t["name"] == "radius-md")  # noqa: E731
        warm = systemlib.foundations(self.ident(warm_cool=-2, playful_serious=-2, friend_authority=-2), None)
        cool = systemlib.foundations(self.ident(warm_cool=2, playful_serious=2, friend_authority=2), None)
        self.assertGreater(r(warm), r(cool))
        self.assertEqual(r(cool), 0)

    def test_premium_moves_slower_and_playful_overshoots(self):
        d = lambda f: next(int(t["value"][:-2]) for t in f["duration"] if t["name"] == "duration-base")  # noqa: E731
        prem = systemlib.foundations(self.ident(premium_accessible=-2), None)
        acc = systemlib.foundations(self.ident(premium_accessible=2), None)
        self.assertGreater(d(prem), d(acc))
        play = systemlib.foundations(self.ident(playful_serious=-2), None)
        exp = next(t["value"] for t in play["easing"] if t["name"] == "ease-expressive")
        self.assertIn("1.56", exp)

    def test_every_token_has_a_usage_note(self):
        f = systemlib.foundations(self.ident(), None)
        for fam in ("spacing", "radius", "shadow", "duration", "easing", "opacity", "breakpoint"):
            for t in f[fam]:
                self.assertTrue(t.get("usage"), f"{fam} {t['name']}")


class SystemJson(unittest.TestCase):
    def setUp(self):
        pl._typelib = lambda: None
        self.tmp = tempfile.mkdtemp(prefix="bk-sys-")
        self.work = _copy_demo(self.tmp)
        self.set_dir = os.path.join(self.work, "sets", "A")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_text_is_kept_and_foundations_rederived(self):
        p, sysd = systemlib.ensure_system(self.set_dir)
        self.assertIn("platform.purpose", systemlib.empty_fields(sysd))
        sysd["platform"]["purpose"] = "Keep commuters riding."
        sysd["foundations"]["spacing"] = []
        systemlib.write_json(p, sysd)
        _, again = systemlib.ensure_system(self.set_dir)
        self.assertEqual(again["platform"]["purpose"], "Keep commuters riding.")
        self.assertEqual(len(again["foundations"]["spacing"]), 11)  # re-derived

    def test_locked_foundations_survive(self):
        p, sysd = systemlib.ensure_system(self.set_dir)
        sysd["foundations"]["locked"] = True
        sysd["foundations"]["radius"][2]["value"] = "3px"
        systemlib.write_json(p, sysd)
        _, again = systemlib.ensure_system(self.set_dir)
        self.assertEqual(again["foundations"]["radius"][2]["value"], "3px")


class DesignSystemExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pl._typelib = lambda: None
        cls.tmp = tempfile.mkdtemp(prefix="bk-ds-")
        cls.work = _copy_demo(cls.tmp)
        cls.set_dir = os.path.join(cls.work, "sets", "A")
        p, sysd = systemlib.ensure_system(cls.set_dir)
        sysd["voice"]["summary"] = "Short, plain sentences."
        sysd["voice"]["traits"] = [{"is": "Direct", "is_not": "Blunt"}]
        sysd["ai_prompts"]["base_style"] = "Documentary photograph, side light."
        systemlib.write_json(p, sysd)
        cls.res = ds_export.build(cls.set_dir)
        cls.project = cls.res["project"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_validates(self):
        self.assertEqual(self.res["report"]["errors"], [])

    def test_tokens_are_lists_with_themes_and_motion(self):
        with open(os.path.join(self.project, "tokens.json"), encoding="utf-8") as fh:
            t = json.load(fh)
        self.assertEqual([x["id"] for x in t["color"]["themes"]], ["light", "dark"])
        names = {x["name"] for x in t["color"]["tokens"]}
        for n in ("background", "text", "on-primary", "accent", "brand-workshop-green", "primary-500"):
            self.assertIn(n, names)
        for fam in ("spacing", "radius", "shadow", "duration", "easing"):
            self.assertIsInstance(t[fam]["tokens"], list)
        self.assertIn("display", t["type"]["families"])
        self.assertTrue(any(s["name"] == "body" for g in t["type"]["groups"] for s in g["styles"]))

    def test_brand_book_and_components(self):
        with open(os.path.join(self.project, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertFalse(readme.startswith("# "))
        self.assertIn("`on-primary`", readme)
        self.assertTrue(os.path.isfile(os.path.join(self.project, "02-voice-and-messaging.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.project, "08-ai-prompts.md")))
        self.assertFalse(os.path.isfile(os.path.join(self.project, "01-brand-platform.md")))  # empty: not invented
        self.assertEqual(os.listdir(os.path.join(self.project, "components", "Cover")), ["preview.html"])
        for c in ("Logo", "Button", "SocialPost", "LogoSting", "VideoGraphics", "Stationery"):
            with open(os.path.join(self.project, "components", c, "preview.html"), encoding="utf-8") as fh:
                self.assertTrue(fh.readline().startswith("<!-- @dsCard"))

    def test_index_from_uploads(self):
        ds = self.res["dir"]
        with open(os.path.join(ds, "upload-plan.json"), encoding="utf-8") as fh:
            plan = json.load(fh)["files"]
        if not plan:
            self.skipTest("no binaries in the demo export")
        ups = {x["path"]: f"/_blob/{i:032x}" for i, x in enumerate(plan)}
        r = ds_export.write_index(ds, ups, by="Tester")
        self.assertEqual(r["missing"], [])
        with open(r["index"], encoding="utf-8") as fh:
            idx = json.load(fh)
        self.assertEqual(idx["layout"], "files")
        self.assertIn("createdOnFiles", idx)
        self.assertEqual(idx["lastChange"]["by"], "Tester")
        g = idx["assetGroups"][plan[0]["group"]]
        self.assertEqual(g["files"][plan[0]["name"]]["blob"], f"{0:032x}")


class Validator(unittest.TestCase):
    def check(self, tokens):
        errors, warnings = [], []
        ds_validate.check_tokens(tokens, errors, warnings)
        return errors, warnings

    def test_map_shaped_family_and_bad_values_are_errors(self):
        errs, _ = self.check({"color": {"themes": [{"id": "light"}], "tokens": [
            {"name": "a", "value": "red", "usage": "x"}, {"name": "b", "value": "{missing}", "usage": "x"},
            {"name": "c", "value": "var(--a)", "usage": "x"}, {"name": "ok", "value": "#fff", "usage": "x"}]},
            "spacing": {"space-1": "4px"}, "easing": {"tokens": [{"name": "e", "value": "url(x)", "usage": "x"}]}})
        joined = "\n".join(errs)
        for bad in ("color a", "color b", "color c", "spacing: must be", "easing e"):
            self.assertIn(bad, joined)
        self.assertNotIn("color ok", joined)

    def test_duplicate_names_across_families(self):
        errs, _ = self.check({"color": {"themes": [{"id": "light"}], "tokens": [{"name": "x", "value": "#000", "usage": "u"}]},
                              "radius": {"tokens": [{"name": "x", "value": "4px", "usage": "u"}]}})
        self.assertTrue(any("duplicate" in e for e in errs))

    def test_low_contrast_warns_per_theme(self):
        _, warns = self.check({"color": {"themes": [{"id": "light"}, {"id": "dark"}], "tokens": [
            {"name": "text", "value": {"light": "#111111", "dark": "#333333"}, "usage": "u"},
            {"name": "background", "value": {"light": "#ffffff", "dark": "#222222"}, "usage": "u"}]}})
        self.assertTrue(any(w.startswith("contrast dark: text on background") for w in warns))


@unittest.skipUnless(BROWSER, "needs Chromium")
class Applications(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pl._typelib = lambda: None
        import applications
        cls.tmp = tempfile.mkdtemp(prefix="bk-apps-")
        cls.work = _copy_demo(cls.tmp)
        cls.res = applications.build(os.path.join(cls.work, "sets", "A"), ("social", "merch"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pages_render_without_contrast_gates(self):
        names = [os.path.basename(p) for p in self.res["pages"]]
        self.assertIn("01-ig-post.png", names)
        self.assertEqual(len(names), 14)
        self.assertEqual(rp.png_size(self.res["pages"][0]), (1080, 1080))
        self.assertEqual([f["message"] for f in self.res["findings"] if f["id"] == "text-contrast"], [])
        self.assertTrue(os.path.isfile(self.res["files"]["logo_sting"]))

    def test_missing_contacts_are_marked_sample(self):
        self.assertIn("email", self.res["sample"])


if __name__ == "__main__":
    unittest.main()

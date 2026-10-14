"""Tests for cardkit. The browser-free tests run anywhere; the build test is skipped when no
Chromium-family browser is found or when CARDKIT_SKIP_BROWSER=1.

    python3 -m unittest test_cardkit
"""
import json, os, tempfile, unittest

import cardkit as ck


class Data(unittest.TestCase):
    def test_formats_are_complete(self):
        for k, f in ck.formats().items():
            for key in ("w", "h", "pad", "min_font", "cards", "max_chars", "label"):
                self.assertIn(key, f, f"{k} lacks {key}")
            self.assertGreater(f["w"], 0)
            self.assertLessEqual(f["cards"][0], f["cards"][1])

    def test_mood_colours_are_readable(self):
        ms, _ = ck.moods()
        for name, m in ms.items():
            bg, surf, ink, muted = (ck.hex_rgb(m[k]) for k in ("bg", "surface", "ink", "muted"))
            self.assertGreaterEqual(ck.contrast(ink, bg), 7.0, f"{name}: ink on bg")
            self.assertGreaterEqual(ck.contrast(ink, surf), 7.0, f"{name}: ink on surface")
            self.assertGreaterEqual(ck.contrast(muted, bg), 4.5, f"{name}: muted on bg")
            self.assertGreaterEqual(ck.contrast(muted, surf), 4.5, f"{name}: muted on surface")
            for extra in ("bg2", "glow"):
                if m.get(extra):
                    self.assertGreaterEqual(ck.contrast(ink, ck.hex_rgb(m[extra])), 7.0, f"{name}: ink on {extra}")
                    self.assertGreaterEqual(ck.contrast(muted, ck.hex_rgb(m[extra])), 4.5, f"{name}: muted on {extra}")
            for a in m["accents"]:
                self.assertGreaterEqual(ck.contrast(ck.hex_rgb(a), surf), 3.0, f"{name}: accent {a} on surface")

    def test_readable_on_picks_higher_contrast(self):
        self.assertEqual(ck.readable_on("#000000", ["#FFFFFF", "#111111"]), "#FFFFFF")
        self.assertEqual(ck.readable_on("#FFFFFF", ["#FFFFFF", "#111111"]), "#111111")


class Text(unittest.TestCase):
    def test_rich_escapes_html_and_keeps_bold(self):
        self.assertEqual(ck.rich("a<b>**x**"), "a&lt;b&gt;<b>x</b>")
        self.assertEqual(ck.rich("line1\nline2"), "line1<br>line2")

    def test_plain_len_ignores_layout_and_paths(self):
        self.assertEqual(ck.plain_len({"layout": "cover", "title": "ab cd", "bg": "x.png"}), 4)


class Lint(unittest.TestCase):
    F = ck.formats()["xhs-3x4"]

    def test_unknown_layout_is_a_problem(self):
        p, _ = ck.lint({"cards": [{"layout": "nope"}]}, self.F, "xhs-3x4")
        self.assertTrue(any("unknown layout" in x for x in p))

    def test_missing_field_is_a_problem(self):
        p, _ = ck.lint({"cards": [{"layout": "list"}]}, self.F, "xhs-3x4")
        self.assertTrue(any("missing 'items'" in x for x in p))

    def test_repeated_layout_warns(self):
        c = {"layout": "points", "boxes": [{"head": "a", "body": "b"}]}
        _, w = ck.lint({"cards": [c, c, c]}, self.F, "xhs-3x4")
        self.assertTrue(any("vary the layouts" in x for x in w))

    def test_budget_warns(self):
        c = {"layout": "points", "boxes": [{"head": "x", "body": "字" * 400}]}
        _, w = ck.lint({"cards": [c, c, c]}, self.F, "xhs-3x4")
        self.assertTrue(any("over the budget" in x for x in w))

    def test_card_count_range_warns(self):
        c = {"layout": "quote", "text": "hi"}
        _, w = ck.lint({"cards": [c]}, self.F, "xhs-3x4")
        self.assertTrue(any("usual range" in x for x in w))


class Tokens(unittest.TestCase):
    def test_brand_overrides_mood(self):
        t = ck.build_tokens("warm", {"palette": {"bg": "#000000", "accents": ["#FF0000"]}, "radius": 3})
        self.assertEqual(t["bg"], "#000000")
        self.assertEqual(t["accents"][0], "#FF0000")
        self.assertEqual(len(t["accents"]), 5)
        self.assertEqual(t["radius"], 3)

    def test_unknown_mood_exits(self):
        with self.assertRaises(SystemExit):
            ck.build_tokens("nope", {})

    def test_format_class(self):
        fs = ck.formats()
        self.assertEqual(ck.fmt_class(fs["xhs-3x4"]), "tall")
        self.assertEqual(ck.fmt_class(fs["square-1x1"]), "square")
        self.assertEqual(ck.fmt_class(fs["wide-16x9"]), "wide")
        self.assertEqual(ck.fmt_class(fs["banner-3x1"]), "banner")


@unittest.skipIf(os.environ.get("CARDKIT_SKIP_BROWSER") == "1" or not ck.find_browser(), "no browser")
class BuildAvatar(unittest.TestCase):
    def test_avatar_builds_and_passes(self):
        spec = {"format": "avatar-1x1", "mood": "playful", "cards": [{"layout": "avatar", "mark": "A"}]}
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, "spec.json")
            json.dump(spec, open(sp, "w"))
            rc = ck.build(sp, os.path.join(d, "out"))
            self.assertEqual(rc, 0)
            self.assertEqual(ck.png_size(os.path.join(d, "out", "card-01.png")), (800, 800))


if __name__ == "__main__":
    unittest.main()

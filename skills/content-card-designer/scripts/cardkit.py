#!/usr/bin/env python3
"""cardkit: build social cards, covers, avatars and banners from a JSON spec.

  python3 cardkit.py build spec.json [--out DIR]
  python3 cardkit.py directions spec.json --moods warm,efficient,knowledge [--out DIR]
  python3 cardkit.py lint spec.json
  python3 cardkit.py formats
  python3 cardkit.py check-env

Text is always laid out by a browser (HTML/CSS), never drawn by an image model.
Each card is fitted to its canvas, rendered to PNG with a headless Chromium-family
browser, and checked: overflow, minimum font size, fill, contrast (including text over
photos when Pillow is installed), short last lines, adjacent repeated layouts and export size.
Standard library only; Pillow is optional.
"""
import argparse, html, json, os, re, shutil, struct, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")


# ---------------------------------------------------------------- data files
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def formats():
    return {k: v for k, v in load_json(os.path.join(ASSETS, "formats.json")).items() if not k.startswith("_")}


def moods():
    raw = load_json(os.path.join(ASSETS, "moods.json"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}, raw["_fonts"]


# ---------------------------------------------------------------- colour helpers
def hex_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _chan(v):
    v /= 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * _chan(r) + 0.7152 * _chan(g) + 0.0722 * _chan(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def readable_on(bg_hex, candidates):
    bg = hex_rgb(bg_hex)
    return max(candidates, key=lambda c: contrast(hex_rgb(c), bg))


# ---------------------------------------------------------------- browser
BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome", "msedge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser(explicit=None):
    cands = [explicit, os.environ.get("CARDKIT_BROWSER")] + BROWSERS
    for c in cands:
        if not c:
            continue
        p = c if os.path.isabs(c) else shutil.which(c)
        if p and os.path.exists(p):
            return p
    return None


def run_browser(browser, args, timeout=120, retries=1, want_log=False):
    """Run the browser once with a throwaway profile. A hung browser is killed with all its
    child processes (own process group) and retried once. The generous timeout allows for a busy machine."""
    import signal
    last = ""
    for _ in range(retries + 1):
        prof = tempfile.mkdtemp(prefix="cardkit-prof-")
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               "--hide-scrollbars", "--allow-file-access-from-files", "--user-data-dir=" + prof] + args
        kw = {"start_new_session": True} if os.name != "nt" else {}
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE if want_log else subprocess.DEVNULL, text=True, **kw)
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                if os.name != "nt":
                    os.killpg(p.pid, signal.SIGKILL)
                else:
                    p.kill()
            except Exception:
                p.kill()
            out, err = p.communicate()
        shutil.rmtree(prof, ignore_errors=True)
        last = (out or "") + (err or "" if want_log else "")
        if last or any(a.startswith("--screenshot=") and os.path.exists(a.split("=", 1)[1]) for a in args):
            return last
    return last


def file_url(path, query=""):
    return "file://" + os.path.abspath(path).replace(" ", "%20") + query


def screenshot(browser, html_path, png_path, w, h, query=""):
    if os.path.exists(png_path):
        os.remove(png_path)
    run_browser(browser, [f"--window-size={w},{h}", f"--screenshot={png_path}",
                          file_url(html_path, query)])
    if not os.path.exists(png_path) or os.path.getsize(png_path) < 500:
        raise RuntimeError("render failed: " + png_path)


def dump_qa(browser, html_path, w, h):
    out = run_browser(browser, [f"--window-size={w},{h}", "--dump-dom", file_url(html_path)])
    m = re.search(r'<pre id="qa"[^>]*>(.*?)</pre>', out, re.S)
    if not m:
        return None
    return json.loads(html.unescape(m.group(1)))[0]


def shot_and_qa(browser, html_path, png_path, w, h):
    """One browser launch: write the screenshot and read the in-page QA result from the console log.
    Falls back to a second launch (--dump-dom) if the console line is not captured."""
    if os.path.exists(png_path):
        os.remove(png_path)
    log = run_browser(browser, [f"--window-size={w},{h}", "--enable-logging=stderr", "--v=0",
                                f"--screenshot={png_path}", file_url(html_path)], want_log=True)
    if not os.path.exists(png_path) or os.path.getsize(png_path) < 500:
        raise RuntimeError("render failed: " + png_path)
    m = re.search(r"QA_B64:([A-Za-z0-9+/=]+)", log)
    if m:
        import base64
        return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))[0]
    return dump_qa(browser, html_path, w, h)


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


# ---------------------------------------------------------------- text helpers
def esc(s):
    return html.escape(str(s), quote=True)


def rich(s):
    """Escape, then allow **bold** and newlines."""
    t = esc(s)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t.replace("\\n", "<br>").replace("\n", "<br>")


def plain_len(c):
    n = 0

    def walk(v):
        nonlocal n
        if isinstance(v, str):
            n += len(re.sub(r"\s", "", v))
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for k, x in v.items():
                if k in ("layout", "src", "bg", "product", "color", "safe", "scrim", "ink", "shape", "kind", "fit"):
                    continue
                walk(x)
    walk(c)
    return n


# ---------------------------------------------------------------- tokens
def merge_brand(spec, base_dir):
    brand = spec.get("brand") or {}
    if isinstance(brand, str):
        brand = load_json(brand if os.path.isabs(brand) else os.path.join(base_dir, brand))
    return brand


def build_tokens(mood_name, brand):
    ms, fonts = moods()
    if mood_name not in ms:
        raise SystemExit(f"unknown mood '{mood_name}'. Choose from: {', '.join(ms)}")
    t = dict(ms[mood_name])
    pal = brand.get("palette") or {}
    for k in ("bg", "ink", "muted", "surface", "line"):
        if pal.get(k):
            t[k] = pal[k]
    if pal.get("accents"):
        t["accents"] = (list(pal["accents"]) + t["accents"])[:5]
    if brand.get("radius") is not None:
        t["radius"] = brand["radius"]
    bf = brand.get("fonts") or {}
    t["font"] = bf.get("body") or fonts[t["body_font"]]
    t["tfont"] = bf.get("title") or fonts[t["title_font"]]
    t["mono"] = fonts["mono"]
    return t


def resolve_color(c, T):
    if not c:
        return None
    m = re.fullmatch(r"a([1-5])", str(c))
    if m:
        return T["accents"][int(m.group(1)) - 1]
    return c


def accent(i, T, explicit=None):
    return resolve_color(explicit, T) or T["accents"][i % len(T["accents"])]


# ---------------------------------------------------------------- layouts
def L_cover(c, T, F):
    chips = "".join(
        f"<span class='chip' style='background:{accent(i, T, x.get('color') if isinstance(x, dict) else None)};"
        f"color:{readable_on(accent(i, T, x.get('color') if isinstance(x, dict) else None), ['#FFFFFF', T['ink'], '#111111'])}'>"
        f"{esc(x['text'] if isinstance(x, dict) else x)}</span>" for i, x in enumerate(c.get("chips", [])))
    left = ""
    if c.get("rule", True):
        left += "<div class='rule'></div>"
    if c.get("kicker"):
        left += f"<div class='kicker caps'>{esc(c['kicker'])}</div>"
    left += f"<div class='title t-xl gap-t'>{rich(c['title'])}</div>"
    if c.get("subtitle"):
        left += f"<div class='sub'>{rich(c['subtitle'])}</div>"
    right = f"<div class='cv-right push'>{chips}</div>" if chips else ""
    wide = fmt_class(F) in ("wide", "banner")
    extra = "" if chips else "vcenter"
    deco = decos_html(c.get("deco"), T, fmt_class(F))
    nofoot = False
    if deco:
        # circles live in a zone reserved for them; text never enters it, and the footer is hidden so no text sits on a circle
        extra += " deco-r" if wide else " deco-b"
        nofoot = True
    return dict(inner=f"<div class='cv-left'>{left}</div>{right}", fit="fill" if wide else "shrink", maxscale=1.5 if wide else None,
                extra=extra, bg=deco, nofoot=nofoot)


def decos_html(kind, T, cls):
    """Optional decoration: a few big soft circles in the accent colors, kept to the side the text does not use."""
    if kind != "circles":
        return ""
    a = T["accents"]
    spots = {
        "wide":   [("66%", "-14%", "56%", a[0], .9), ("84%", "56%", "30%", a[1], .8), ("62%", "66%", "20%", a[2], .6)],
        "banner": [("74%", "-45%", "95%", a[0], .9), ("90%", "35%", "55%", a[1], .75)],
        "square": [("46%", "66%", "62%", a[0], .9), ("-8%", "76%", "34%", a[1], .8), ("78%", "56%", "20%", a[2], .6)],
        "tall":   [("34%", "68%", "78%", a[0], .9), ("-10%", "82%", "38%", a[1], .8), ("76%", "58%", "22%", a[2], .6)],
    }[cls]
    out = "".join(f"<i style='left:{x};top:{y};width:{s};aspect-ratio:1;background:{col};opacity:{o}'></i>" for x, y, s, col, o in spots)
    return f"<div class='decos'>{out}</div>"


def _head(c, size="t-lg"):
    h = ""
    if c.get("kicker"):
        h += f"<div class='kicker'>{esc(c['kicker'])}</div>"
    if c.get("title"):
        h += f"<div class='title {size} gap-t'>{rich(c['title'])}</div>"
    return h


def L_list(c, T, F):
    rows = ""
    for i, it in enumerate(c["items"]):
        col = accent(i, T, it.get("color"))
        rows += (f"<div class='row surface'><div class='bar' style='background:{col}'></div><div class='body'>"
                 f"<div class='head'><span class='name' style='color:{col}'>{esc(it['name'])}</span>"
                 + (f"<span class='tag'>{esc(it['tag'])}</span>" if it.get("tag") else "") + "</div>"
                 + (f"<div class='detail'>{esc(it['detail'])}</div>" if it.get("detail") else "") + "</div></div>")
    return dict(inner=_head(c) + f"<div class='cols'>{rows}</div>", fit="fill")


def L_steps(c, T, F):
    out = ""
    for g in c["groups"]:
        kind = g.get("kind", "steps")
        body = ""
        if kind == "steps":
            body = "<div class='steps'>" + "".join(
                f"<div class='step surface'><i>{i + 1}</i>{esc(s)}</div>" for i, s in enumerate(g["items"])) + "</div>"
        elif kind == "chips":
            body = "<div>" + "".join(
                f"<span class='chip' style='background:{accent(i, T)};color:{readable_on(accent(i, T), ['#FFFFFF', T['ink'], '#111111'])}'>{esc(s)}</span>"
                for i, s in enumerate(g["items"])) + "</div>"
        else:
            body = "<div>" + "".join(f"<span class='pill'>{esc(s)}</span>" for s in g["items"]) + "</div>"
        out += f"<div class='group'>" + (f"<div class='group-label'>{esc(g['label'])}</div>" if g.get("label") else "") + body + "</div>"
    return dict(inner=_head(c) + out, fit="fill")


def L_points(c, T, F):
    boxes = "".join(f"<div class='box surface'><b>{esc(b['head'])}</b><span>{rich(b['body'])}</span></div>" for b in c["boxes"])
    return dict(inner=_head(c) + f"<div class='boxes cols'>{boxes}</div>", fit="fill")


def L_compare(c, T, F):
    def col(side, i):
        s = c[side]
        col_c = accent(i, T, s.get("color"))
        lis = "".join(f"<li>{esc(x)}</li>" for x in s["items"])
        return (f"<div class='compare-col surface' style='color:{T['ink']}'><div class='col-head' style='color:{col_c}'>{esc(s['head'])}</div>"
                f"<ul style='color:{T['ink']}'>{lis}</ul></div>")
    return dict(inner=_head(c) + f"<div class='cols'>{col('left', 0)}{col('right', 1)}</div>", fit="fill")


def L_stat(c, T, F):
    notes = "".join(f"<div>{esc(n)}</div>" for n in c.get("notes", []))
    inner = _head(c, "t-md") + (f"<div class='push'><div class='stat-v' style='color:{accent(0, T, c.get('color'))}'>{esc(c['value'])}</div>"
                                f"<div class='stat-c'>{rich(c['caption'])}</div>" + (f"<div class='notes'>{notes}</div>" if notes else "") + "</div>")
    return dict(inner=inner, fit="shrink")


def L_quote(c, T, F):
    inner = ("<div class='mark'>“</div>" f"<div class='quote'>{rich(c['text'])}</div>"
             + (f"<div class='quote-by'>{esc(c['by'])}</div>" if c.get("by") else ""))
    return dict(inner=f"<div class='push'></div>{inner}<div class='push'></div>", fit="fill", maxscale=1.7)


def L_cta(c, T, F):
    steps = "".join(f"<div class='step surface'><i>{i + 1}</i>{esc(s)}</div>" for i, s in enumerate(c.get("steps", [])))
    note = ""
    if c.get("note"):
        note = f"<div class='box surface'><b>{esc(c['note']['head'])}</b><span>{rich(c['note']['body'])}</span></div>"
    code = f"<div class='code'>{rich(c['code'])}</div>" if c.get("code") else ""
    inner = _head(c, "t-xl" if len(c.get("title", "")) < 9 else "t-lg") + f"<div class='steps'>{steps}</div>"
    inner += (f"<div style='margin-top:calc(30*var(--px))'>{note}</div>" if note else "")
    inner += (f"<div style='margin-top:calc(30*var(--px))'>{code}</div>" if code else "")
    return dict(inner=inner, fit="fill", maxscale=1.15)


def _bg_html(c, base_dir, scrim_default=0.35):
    bg = c.get("bg") or c.get("background")
    if not bg:
        return "", False
    src = bg["src"] if isinstance(bg, dict) else bg
    sc = bg.get("scrim", scrim_default) if isinstance(bg, dict) else scrim_default
    path = src if os.path.isabs(src) else os.path.join(base_dir, src)
    return (f"<div class='bgimg' style=\"background-image:url('{file_url(path)}')\"></div>"
            f"<div class='scrim' style='background:rgba(0,0,0,{sc})'></div>"), True


def L_image(c, T, F, base_dir="."):
    safe = c.get("safe", "left")
    inner = ""
    if c.get("kicker"):
        inner += f"<div class='kicker'>{esc(c['kicker'])}</div>"
    inner += f"<div class='title t-xl gap-t'>{rich(c['title'])}</div>"
    if c.get("subtitle"):
        inner += f"<div class='sub'>{rich(c['subtitle'])}</div>"
    bg, _ = _bg_html(c, base_dir)
    ink = "#FFFFFF" if c.get("ink", "light") == "light" else "#111111"
    return dict(inner=inner, fit="shrink", bg=bg, extra=f"image-text safe-{safe}", style=f"--imgink:{ink}")


_ASSET_DIR = None
NOTES = []


def prepare_product(path):
    """Trim fully transparent margins so the product is not tiny inside a big empty image.
    Visible pixels are untouched. Needs Pillow; otherwise the image is used as supplied."""
    try:
        from PIL import Image
    except Exception:
        return path
    try:
        im = Image.open(path)
        if im.mode != "RGBA":
            return path
        bbox = im.getchannel("A").getbbox()
        if not bbox or bbox == (0, 0, im.width, im.height):
            return path
        if (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > 0.97 * im.width * im.height:
            return path
        out_dir = _ASSET_DIR or tempfile.gettempdir()
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "trimmed-" + os.path.basename(path))
        im.crop(bbox).save(out)
        NOTES.append(f"Trimmed the empty transparent margins of {os.path.basename(path)}; the visible pixels are unchanged.")
        return out
    except Exception:
        return path


def L_product(c, T, F, base_dir="."):
    p = c["product"]
    path = prepare_product(p if os.path.isabs(p) else os.path.join(base_dir, p))
    prodh = int(F["h"] * (0.46 if F["h"] >= F["w"] else 0.62))
    head = ""
    if c.get("kicker"):
        head += f"<div class='kicker caps'>{esc(c['kicker'])}</div>"
    if c.get("title"):
        head += f"<div class='title t-lg gap-t'>{rich(c['title'])}</div>"
    inner = f"<div class='prod-head'>{head}</div><div class='prod-stage'><div class='prod-glow'></div><img class='prod-img' src='{file_url(path)}' alt=''></div>"
    specs = c.get("specs")
    if specs:
        inner += "<div class='prod-specs'>" + "".join(f"<span>{esc(s)}</span>" for s in specs) + "</div>"
    bul = "".join(f"<div>• {esc(b)}</div>" for b in c.get("bullets", []))
    if bul:
        inner += f"<div class='bul'>{bul}</div>"
    bg, has = _bg_html(c, base_dir, 0.0) if c.get("bg") else ("", False)
    style = f"--prodh:{prodh};"
    if c.get("bg_color"):
        bgc = resolve_color(c["bg_color"], T)
        fg = readable_on(bgc, ["#FFFFFF", T["ink"], "#111111"])
        style += f"background:{bgc};--bgfx:none;--ink:{fg};--muted:{fg};--line:{fg};"
    center = c.get("align", "center") == "center"
    return dict(inner=inner, fit="fill", maxscale=1.1, bg=bg, extra="prod-card" + (" pcenter" if center else ""), style=style)


def L_point(c, T, F):
    col = accent(0, T, c.get("color"))
    out = ""
    if c.get("number"):
        out += f"<div class='pt-num' style='color:{col}'>{esc(c['number'])}</div>"
    if c.get("kicker"):
        out += f"<div class='kicker caps'>{esc(c['kicker'])}</div>"
    out += f"<div class='title t-lg gap-t'>{rich(c['title'])}</div>"
    if c.get("body"):
        out += f"<div class='pt-body'>{rich(c['body'])}</div>"
    cmp = c.get("compare")
    if cmp:
        for i, side in enumerate(("a", "b")):
            if cmp.get(side):
                sc = accent(1 if i == 0 else 2, T, cmp[side].get("color"))
                out += (f"<div class='cmp surface' style='border-left:calc(14*var(--px)) solid {sc}'>"
                        f"<small style='color:{T['muted']}'>{esc(cmp[side].get('label', ''))}</small><span>{rich(cmp[side]['text'])}</span></div>")
    if c.get("code"):
        out += f"<div class='code' style='margin-top:calc(14*var(--px))'>{rich(c['code'])}</div>"
    return dict(inner=out, fit="fill", maxscale=1.15)


def L_avatar(c, T, F):
    col = accent(0, T, c.get("color"))
    ink = readable_on(col, ["#FFFFFF", T["ink"], "#111111"])
    shape = c.get("shape", "circle")
    rad = {"circle": "50%", "rounded": "22%", "square": "0"}[shape]
    inner = (f"<div class='avatar-shape' style='background:{col};border-radius:{rad};max-width:78%'>"
             f"<div class='avatar-mark' style='color:{ink}'>{esc(c['mark'])}</div></div>")
    return dict(inner=inner, fit="shrink", extra="avatar", nofoot=True)


def L_banner(c, T, F):
    inner = (f"<div class='title t-xl' style='border-left:calc(14*var(--px)) solid {accent(0, T)};padding-left:calc(34*var(--px))'>{rich(c['title'])}</div>"
             + (f"<div class='sub' style='padding-left:calc(48*var(--px));margin-top:calc(14*var(--px))'>{rich(c['subtitle'])}</div>" if c.get("subtitle") else "")
             + (f"<div class='banner-handle' style='padding-left:calc(48*var(--px))'>{esc(c['handle'])}</div>" if c.get("handle") else ""))
    return dict(inner=inner, fit="shrink", nofoot=True)


LAYOUTS = {
    "cover": (L_cover, ["title"]), "list": (L_list, ["items"]), "steps": (L_steps, ["groups"]),
    "points": (L_points, ["boxes"]), "compare": (L_compare, ["left", "right"]), "stat": (L_stat, ["value", "caption"]),
    "quote": (L_quote, ["text"]), "cta": (L_cta, []), "image": (L_image, ["title", "bg"]),
    "product": (L_product, ["product"]), "point": (L_point, ["title"]), "avatar": (L_avatar, ["mark"]), "banner": (L_banner, ["title"]),
}
REPEAT_OK = {"cover", "cta", "image", "avatar", "banner", "product", "point"}


# ---------------------------------------------------------------- page
def fmt_class(F):
    r = F["w"] / F["h"]
    if r >= 2.5:
        return "banner"
    if r >= 1.5:
        return "wide"
    if F["h"] / F["w"] >= 1.2:
        return "tall"
    return "square"


def css_vars(T, F):
    u = F.get("u", min(F["w"], F["h"]) / 1080.0)
    v = {
        "--w": F["w"], "--h": F["h"], "--minfont": F["min_font"], "--pad": F["pad"], "--u": round(u, 4), "--bg": T["bg"], "--ink": T["ink"],
        "--muted": T["muted"], "--surface": T["surface"], "--line": T["line"], "--radius": T["radius"], "--bw": T["bw"],
        "--tw": T["tw"], "--lh": T["lh"], "--tls": "-0.01em", "--footfs": max(34, F["min_font"]), "--font": T["font"], "--tfont": T["tfont"],
        "--mono": T["mono"],
    }
    for i, a in enumerate(T["accents"], 1):
        v[f"--a{i}"] = a
    glow, bg2 = T.get("glow"), T.get("bg2")
    if glow or bg2:
        v["--bgfx"] = ((f"radial-gradient(ellipse 90% 60% at 50% 42%, {glow} 0%, transparent 72%), " if glow else "")
                       + f"linear-gradient(180deg, {T['bg']} 0%, {bg2 or T['bg']} 100%)")
    v["--glow"] = glow or "rgba(255,255,255,.55)"
    return ";".join(f"{k}:{x}" for k, x in v.items())


def card_html(c, idx, total, T, F, fid, spec, base_dir, mood_name):
    name = c["layout"]
    fn = LAYOUTS[name][0]
    r = fn(c, T, F, base_dir) if name in ("image", "product") else fn(c, T, F)
    style = r.get("style", "")
    foot_left = (spec.get("footer") if "footer" in spec else (spec.get("_brand_footer") or ""))
    show_foot = F.get("footer", True) and not r.get("nofoot") and spec.get("footer") is not False
    foot = ""
    if show_foot:
        n = f"{idx + 1}/{total}" if total > 1 and spec.get("page_numbers", True) else ""
        dots = ""
        if total > 1 and total <= 12 and spec.get("progress", "dots") == "dots":
            dots = "<span class='dots'>" + "".join(f"<i class='{'on' if j == idx else ''}'></i>" for j in range(total)) + "</span>"
        foot = f"<div class='foot'><span>{esc(foot_left or '')}</span><span>{dots}{n}</span></div>"
    cls = f"card L-{name} {r.get('extra', '')}"
    attrs = (f"data-layout='{name}' data-fit='{r['fit']}' data-minfont='{F['min_font']}' data-basemin='34'"
             + (f" data-maxscale='{r['maxscale']}'" if r.get("maxscale") else ""))
    return (f"<section class='{cls}' {attrs} style='{style}'>{r.get('bg', '')}"
            f"<div class='main'><div class='inner'>{r['inner']}</div></div>{foot}</section>")


def page(cards_html, T, F, orn):
    with open(os.path.join(HERE, "styles.css"), encoding="utf-8") as f:
        css = f.read()
    with open(os.path.join(HERE, "inpage.js"), encoding="utf-8") as f:
        js = f.read()
    body_cls = f"{fmt_class(F)} orn{orn}"
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>card</title>"
            f"<style>:root{{{css_vars(T, F)}}}\n{css}</style></head><body class='{body_cls}'>{cards_html}"
            f"<pre id='qa'></pre><script>{js}</script></body></html>")


# ---------------------------------------------------------------- spec handling
def load_spec(path):
    spec = load_json(path)
    base = os.path.dirname(os.path.abspath(path))
    brand = merge_brand(spec, base)
    mood = spec.get("mood") or brand.get("mood") or "efficient"
    fid = spec.get("format", "xhs-3x4")
    fs = formats()
    if fid not in fs:
        raise SystemExit(f"unknown format '{fid}'. Choose from: {', '.join(fs)}")
    spec["_brand_footer"] = brand.get("footer_left") or brand.get("name") or ""
    return spec, base, brand, mood, fid, fs[fid]


def lint(spec, F, fid):
    problems, warns = [], []
    cards = spec.get("cards", [])
    if not cards:
        problems.append("spec has no cards")
    lo, hi = F.get("cards", [1, 99])
    if cards and not (lo <= len(cards) <= hi):
        warns.append(f"{len(cards)} cards; the usual range for {fid} is {lo} to {hi}")
    prev = None
    for i, c in enumerate(cards, 1):
        name = c.get("layout")
        if name not in LAYOUTS:
            problems.append(f"card {i}: unknown layout '{name}'. Choose from: {', '.join(LAYOUTS)}")
            continue
        for req in LAYOUTS[name][1]:
            if req not in c:
                problems.append(f"card {i} ({name}): missing '{req}'")
        n = plain_len(c)
        if n > F["max_chars"] * 1.3:
            warns.append(f"card {i}: {n} characters, over the budget of about {F['max_chars']} for {fid}; consider splitting")
        if prev == name and name not in REPEAT_OK:
            warns.append(f"cards {i - 1} and {i} both use '{name}'; vary the layouts")
        prev = name
    return problems, warns


# ---------------------------------------------------------------- photo contrast
def photo_contrast(browser, html_path, png_path, F, qa):
    """Render with text hidden, then compare text colour with the pixels behind each text box."""
    try:
        from PIL import Image
    except Exception:
        return None, "Pillow not installed: text over photos was not verified"
    notext = png_path.replace(".png", ".notext.png")
    screenshot(browser, html_path, notext, F["w"], F["h"], "?notext=1")
    im = Image.open(notext).convert("RGB")
    issues = []
    for t in qa.get("photoText", []):
        x0, y0 = max(0, int(t["x"])), max(0, int(t["y"]))
        x1, y1 = min(im.width, int(t["x"] + t["w"])), min(im.height, int(t["y"] + t["h"]))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        region = im.crop((x0, y0, x1, y1)).resize((24, 8))
        fg = tuple(int(v) for v in t["color"])
        ratios = sorted(contrast(fg, px) for px in region.getdata())
        worst = ratios[max(0, int(len(ratios) * 0.1) - 1)]
        need = 3.0 if t["fs"] >= 32 else 4.5
        if worst < need:
            issues.append({"text": t["text"], "ratio": round(worst, 2), "need": need})
    os.remove(notext)
    return issues, None


# ---------------------------------------------------------------- build
def overview(browser, items, out_png, thumb_h=520, title=None):
    """items: list of (png_path, caption)."""
    imgs = ""
    for p, cap in items:
        w, h = png_size(p)
        tw = int(thumb_h * w / h)
        imgs += (f"<figure><img src='{file_url(p)}' width='{tw}' height='{thumb_h}'>"
                 f"<figcaption>{esc(cap)}</figcaption></figure>")
    total_w = sum(int(thumb_h * png_size(p)[0] / png_size(p)[1]) + 24 for p, _ in items)
    width = min(max(total_w + 60, 900), 2600)
    html_doc = (f"<!doctype html><meta charset='utf-8'><style>body{{margin:0;background:#E9E4D8;font-family:-apple-system,'PingFang SC',sans-serif;"
                f"padding:30px;width:{width - 60}px}}h2{{font-size:26px;margin:0 0 18px;color:#1B1F2A}}"
                f".w{{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start}}figure{{margin:0}}"
                f"img{{display:block;border-radius:8px;box-shadow:0 2px 10px #0003}}figcaption{{font-size:18px;color:#444;margin-top:8px}}</style>"
                + (f"<h2>{esc(title)}</h2>" if title else "") + f"<div class='w'>{imgs}</div>")
    p = out_png.replace(".png", ".html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html_doc)
    rows = 1 + (total_w // 2400)
    screenshot(browser, p, out_png, width, int((thumb_h + 90) * rows + (60 if title else 20)))


def build(spec_path, out, browser=None, photo=True, mood_override=None, jobs=3):
    spec, base, brand, mood, fid, F = load_spec(spec_path)
    if mood_override:
        mood = mood_override
    problems, warns = lint(spec, F, fid)
    if problems:
        print("Spec problems:\n- " + "\n- ".join(problems))
        return 1
    b = find_browser(browser)
    if not b:
        print("No Chromium-family browser found (Chrome, Edge, Chromium, Brave). Set CARDKIT_BROWSER or use --browser.")
        return 1
    os.makedirs(out, exist_ok=True)
    global _ASSET_DIR
    _ASSET_DIR = os.path.join(out, "assets")
    del NOTES[:]
    T = build_tokens(mood, brand)
    cards = spec["cards"]
    def process(i, c):
        stem = f"card-{i + 1:02d}"
        hp, pp = os.path.join(out, stem + ".html"), os.path.join(out, stem + ".png")
        with open(hp, "w", encoding="utf-8") as f:
            f.write(page(card_html(c, i, len(cards), T, F, fid, spec, base, mood), T, F, T["ornament"]))
        qa = shot_and_qa(b, hp, pp, F["w"], F["h"])
        size = png_size(pp)
        r = {"card": i + 1, "file": stem + ".png", "layout": c["layout"], "qa": qa, "png_size": size, "fails": [], "warns": []}
        if not qa:
            r["fails"].append("the in-page checks did not run")
        else:
            if qa["overflow"]:
                r["fails"].append("content does not fit this canvas even at the smallest allowed font; cut text or split the card")
            if qa["minFont"] + 0.5 < qa["minFontRequired"]:
                r["fails"].append(f"smallest font {qa['minFont']}px is below the {qa['minFontRequired']}px minimum")
            if qa["contrastIssues"]:
                r["fails"].append("low contrast: " + "; ".join(f"'{x['text']}' {x['ratio']}:1 (needs {x['need']})" for x in qa["contrastIssues"][:3]))
            if qa["shortLastLines"]:
                r["warns"].append("short last line: " + "; ".join(f"'{x['text']}'" for x in qa["shortLastLines"][:3]))
            if qa["fitStatus"] == "ok" and qa["fillPct"] < 50 and c["layout"] in ("list", "steps", "points", "compare", "product"):
                r["warns"].append(f"card is only {qa['fillPct']}% full; add content or choose a sparser layout")
            if qa["photoText"] and photo:
                issues, note = photo_contrast(b, hp, pp, F, qa)
                if note:
                    r["warns"].append(note)
                elif issues:
                    r["fails"].append("text over photo has low contrast: " + "; ".join(f"'{x['text']}' {x['ratio']}:1 (needs {x['need']})" for x in issues[:3]))
        if size != (F["w"], F["h"]):
            r["fails"].append(f"exported {size}, expected {(F['w'], F['h'])}")
        return r, (pp, f"{i + 1}. {c['layout']}")

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        done = list(ex.map(lambda ic: process(*ic), list(enumerate(cards))))
    results = [d[0] for d in done]
    pngs = [d[1] for d in done]
    adj = [w for w in warns] + list(dict.fromkeys(NOTES))
    with open(os.path.join(out, "qa.json"), "w", encoding="utf-8") as f:
        json.dump({"format": fid, "mood": mood, "cards": results, "spec_warnings": adj}, f, ensure_ascii=False, indent=1)
    overview(b, pngs, os.path.join(out, "overview.png"), title=f"{fid} · {mood}")
    report(out, fid, mood, F, results, adj)
    ok = all(not r["fails"] for r in results)
    print(open(os.path.join(out, "REPORT.md"), encoding="utf-8").read())
    return 0 if ok else 2


def report(out, fid, mood, F, results, spec_warns):
    lines = [f"# Quality report: {fid}, mood '{mood}'", ""]
    if F.get("verify"):
        lines += ["Canvas sizes and budgets for this format are starting points. Check the platform's current specs before publishing.", ""]
    lines += ["| Card | Layout | Scale | Fill | Min font | Result |", "|---|---|---|---|---|---|"]
    for r in results:
        q = r["qa"] or {}
        res = "PASS" if not r["fails"] else "FAIL"
        if not r["fails"] and r["warns"]:
            res = "PASS (see notes)"
        lines.append(f"| {r['card']} | {r['layout']} | {q.get('scale', '-')} | {q.get('fillPct', '-')}% | {q.get('minFont', '-')}px | {res} |")
    notes = []
    for r in results:
        for f in r["fails"]:
            notes.append(f"- Card {r['card']} FAIL: {f}")
        for w in r["warns"]:
            notes.append(f"- Card {r['card']} note: {w}")
    for w in spec_warns:
        notes.append(f"- Spec note: {w}")
    if notes:
        lines += ["", "## Notes", *notes]
    lines += ["", "Checks run: overflow, minimum font, fill, contrast, short last lines, repeated layouts, export size."]
    with open(os.path.join(out, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def directions(spec_path, mood_list, out, browser=None):
    spec, base, brand, _, fid, F = load_spec(spec_path)
    b = find_browser(browser)
    if not b:
        print("No Chromium-family browser found.")
        return 1
    os.makedirs(out, exist_ok=True)
    ms, _ = moods()
    names = [m for m in mood_list if m in ms] or list(ms)[:3]
    c = spec["cards"][0]
    items = []
    for m in names:
        T = build_tokens(m, brand)
        hp, pp = os.path.join(out, f"direction-{m}.html"), os.path.join(out, f"direction-{m}.png")
        with open(hp, "w", encoding="utf-8") as f:
            f.write(page(card_html(c, 0, 1, T, F, fid, spec, base, m), T, F, T["ornament"]))
        screenshot(b, hp, pp, F["w"], F["h"])
        items.append((pp, f"{m}: {ms[m]['label']}" + (" (proposed)" if ms[m].get("proposed") else "")))
    overview(b, items, os.path.join(out, "directions.png"), title=f"Style directions for {fid}")
    print("Wrote", os.path.join(out, "directions.png"))
    return 0


def check_env():
    b = find_browser()
    print("browser:", b or "NOT FOUND (set CARDKIT_BROWSER)")
    try:
        import PIL
        print("Pillow:", PIL.__version__, "(text over photos can be verified)")
    except Exception:
        print("Pillow: not installed (text over photos will be reported as unverified)")
    print("python:", sys.version.split()[0])
    return 0 if b else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build"); p.add_argument("spec"); p.add_argument("--out", default="out"); p.add_argument("--browser")
    p.add_argument("--mood", help="override the mood in the spec"); p.add_argument("--no-photo-check", action="store_true"); p.add_argument("--jobs", type=int, default=3, help="cards rendered in parallel")
    p = sub.add_parser("directions"); p.add_argument("spec"); p.add_argument("--moods", default="warm,efficient,knowledge")
    p.add_argument("--out", default="out/directions"); p.add_argument("--browser")
    p = sub.add_parser("lint"); p.add_argument("spec")
    sub.add_parser("formats"); sub.add_parser("check-env")
    a = ap.parse_args()
    if a.cmd == "build":
        return build(a.spec, a.out, a.browser, not a.no_photo_check, a.mood, a.jobs)
    if a.cmd == "directions":
        return directions(a.spec, a.moods.split(","), a.out, a.browser)
    if a.cmd == "lint":
        spec, base, brand, mood, fid, F = load_spec(a.spec)
        pr, wr = lint(spec, F, fid)
        print("\n".join(["PROBLEM: " + x for x in pr] + ["warning: " + x for x in wr]) or "ok")
        return 1 if pr else 0
    if a.cmd == "formats":
        for k, v in formats().items():
            print(f"{k:20s} {v['w']}x{v['h']}  {v['label']}")
        return 0
    return check_env()


if __name__ == "__main__":
    sys.exit(main())

---
name: content-card-designer
description: Design social image cards, carousels, covers, avatars, profile banners and product posters as HTML/CSS rendered to PNG, with crisp text, real assets kept pixel-exact, a style derived from the content's mood, and measured quality checks before export. Works across formats (Xiaohongshu 3:4, Instagram or LinkedIn 4:5, square, 16:9, WeChat cover, 9:16 story, avatar, banner) and needs no image-generation API. Use whenever the user wants to turn text or notes into a set of image cards or a cover, asks for a carousel, a social post graphic, 小红书图文, 公众号头图/封面, 配图, 轮播图, 头像, 主页头图, 产品海报, 品牌风格探索, "make this into slides for social", "design a cover for my article", or wants style directions to choose from. Use it even when the user names no format or style. Not for photographs or painterly illustrations (it cannot create those; it can place images you supply), slide decks as .pptx, data charts, or printable logos.
---

# Content card designer

Turn content into image cards that read well on a phone, look consistent as a set, and survive a quality check. Text is always laid out by a browser (HTML/CSS), never drawn by an image model, so it stays sharp and correct, including Chinese. Real material (screenshots, product photos, numbers, logos) is placed as it is, never redrawn. Style comes from the mood of the content, not from picking a preset.

Reply in the user's language.

## Principles

1. **Text is code-rendered.** Never ask an image model to draw words. If a background image is wanted, it must be text-free, with a clear zone left for the text.
2. **Real things stay real.** Place the user's screenshots, product photos, numbers and logos unchanged. Do not redraw, restyle or "improve" them. Do not invent figures, quotes, results or product details.
3. **Style follows mood.** Decide what the content should feel like first (warm, efficient, knowledge-heavy, personal, playful, analytical), then derive the palette, type, spacing and decoration from that. Do not default to a purple-blue gradient or a stock "tech" look.
4. **Measure, don't trust.** Every export goes through the checks in "Quality gates". Report what passed and what did not.
5. **Plan first, then build.** One idea per card, a clear first card and last card, and no run of identical layouts.
6. **Use the user's words; offer, don't insert.** Keep the user's wording and claims as written. If a line looks like a typo or contradicts another, keep it, say so, and let the user decide. Do not add explanations, examples, sample code, statistics, taglines or product claims they did not give. If the cards would be richer with supporting text, offer to draft some and wait for a yes.
7. **Stay out of the user's accounts.** Produce files only. Do not log in, post or schedule anything.

## Workflow

1. **Brief.** Ask at most five short questions, skipping anything already known: where it will be posted and for what, who reads it, what feeling it should give, what the source content is, and which real assets and brand colors or fonts exist. Write down a short design brief (see `references/workflow.md`). If the user says "just make it", state your assumptions in one line and go.
2. **Style directions.** Infer the mood (`references/mood-to-style.md`). For a new look, render the first card in two or three moods as one overview image and let the user choose. Lock the choice so the whole set is consistent.
3. **Plan the cards.** Split the content into a cover, content cards and an ending. One claim per card, within the character budget of the chosen format. Vary layouts (`references/layouts.md`).
4. **Build.** Write a spec file and run the builder (below). Use the user's text as written; tighten wording only to fit and tell them exactly what you shortened. Never rewrite a claim.
5. **Check and fix.** Read the report. Fix failures by cutting text, splitting a card or changing a layout, then rebuild. Do not hide a failure.
6. **Deliver.** PNGs, the overview image, the quality report and the HTML sources. Say plainly what was not verified.

## Building with the bundled scripts

```bash
python3 scripts/cardkit.py check-env                      # finds a Chromium-family browser; reports Pillow
python3 scripts/cardkit.py formats                        # list canvas formats
python3 scripts/cardkit.py lint spec.json                 # check the spec before rendering
python3 scripts/cardkit.py directions spec.json --moods warm,efficient,knowledge
python3 scripts/cardkit.py build spec.json --out out      # PNGs, overview.png, qa.json, REPORT.md
```

A spec is JSON: a `format`, a `mood`, optional `brand` and `footer`, and a list of `cards`, each with a `layout` and its fields. Layouts: `cover`, `list`, `steps`, `points`, `point`, `compare`, `stat`, `quote`, `cta`, `image`, `product`, `avatar`, `banner`. Fields, examples and the brand kit are in `references/spec.md`. Format profiles are in `assets/formats.json` and moods in `assets/moods.json`; both are meant to be edited.

Each card is fitted to its canvas by scaling the layout up or down, so the same content works across formats without cropping. A card that still cannot fit at the minimum font size fails and must be cut or split.

## Quality gates

Every export is checked for: overflow or clipping, minimum font size, fill (no large empty band), text contrast (including text over photos when Pillow is available), very short last lines, repeated adjacent layouts, and exported size. Thresholds and fixes are in `references/quality-gates.md`.

State what was **not** verified. Typical cases: text over a photo when Pillow is missing, how the cards look on the actual platform, and platform size rules, which change (the formats are marked `verify`).

## If the scripts cannot run

The skill still works. Write one self-contained HTML file per card at the format's exact pixel size, apply the principles and the gate thresholds by hand, and export with any Chromium-family browser:

```bash
chrome --headless=new --window-size=1080,1440 --screenshot=card-01.png file:///path/card-01.html
```

With no command line at all, give the user the HTML files and tell them to open each in a browser and screenshot it at the stated size. Use system fonts only. Never inline fonts as base64, which can make exports time out.

## Optional images

- **User photos or an AI-made background** can sit behind text on `image` and `product` cards. Read `references/backgrounds-and-real-assets.md` first: backgrounds must be text-free with a clear zone for the text, and text over a photo is contrast-checked.
- **Avatars, profile banners and style boards** are covered in `references/profile-visuals.md`.

## What this skill cannot do

Photographs, painterly or character illustration, and print-ready logos are outside it. It can place images you supply, draw simple geometric marks and diagrams, and help you write a brief for an image tool.

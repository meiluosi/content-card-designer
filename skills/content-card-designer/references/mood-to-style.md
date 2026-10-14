# From mood to style

Decide what the content should feel like, then derive the look. This avoids the sameness of picking from a preset list.

The idea of working from emotional tone to visual style comes from the book 《把自己变成一门生意》. The first three moods follow its examples; the other three are this project's extension and have not been tested with readers.

## Finding the mood

Ask for one feeling in the user's own words, or infer it:

| The content is about | Likely mood |
|---|---|
| Comfort, healing, slowing down, care | `warm` |
| Productivity, work, process, tools | `efficient` |
| Tips, how-tos, explanations, lists to save | `knowledge` |
| A personal experience, a reflection, a journey | `story` (proposed) |
| Fun, lightness, a casual recommendation | `playful` (proposed) |
| Data, analysis, technical depth, evaluation | `analytical` (proposed) |

If two fit, choose the one that matches the reader's feeling, not the topic's subject. A technical topic written as a personal story is `story`.

## The moods

Tokens live in `assets/moods.json`. This table is the intent; read the file for exact values.

| Mood | Palette and light | Type and form | Density and decoration |
|---|---|---|---|
| `warm` | Low-saturation warm; soft cream background; warm dark ink | Sans, generous line height, large radius | Airy; no decoration |
| `efficient` | Cool grey-blue; white panels; restrained blue and teal | Sans, firm weight, small radius | Medium; thin rules |
| `knowledge` | Off-white with near-black ink; one hot accent; strong outlines | Heavy sans titles, square corners | Medium to dense; thick outlines |
| `story` (proposed) | Paper tones; muted earthy accents | Serif titles, loose line height | Airy; quiet |
| `playful` (proposed) | Bright yellow ground; saturated accents; black outlines | Heavy sans, large radius | Medium; hard offset shadows |
| `analytical` (proposed) | Dark navy; cool bright accents | Sans, tight and numeric | Dense; hairlines |

## Using the tokens

- **A brand kit overrides a mood.** If the user has brand colors or fonts, keep the mood's structure (radius, density, outline weight) and swap in their palette and fonts.
- **Check, don't assume.** Mood palettes pass contrast checks by design, but brand colors may not. The quality gates will say.
- **Blend carefully.** Take one primary mood. Borrow at most one trait from another, for example `knowledge` with the warm background.
- **Add a mood** by adding an entry to `assets/moods.json` with the same fields. Keep ink-on-background contrast at 7:1 or better and accents at 3:1 or better on the panel color.

## What to avoid

- Purple-to-blue gradients, glow effects and generic "tech" stock looks.
- Random decorative blobs, circles or stickers that carry no meaning. The `deco: circles` option is the one allowed exception: it is an explicit choice for friendly looks, kept in a reserved zone away from the text. Offer it; do not apply it by default.
- Nested cards inside cards as the default layout.
- Different styles on different cards of one set.

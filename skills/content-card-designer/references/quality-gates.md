# Quality gates

Every card is measured inside the browser after the layout has been fitted to its canvas. `REPORT.md` lists the result per card; `qa.json` has the numbers.

## Gates

| Gate | How it is measured | Fails when | What to do |
|---|---|---|---|
| Overflow or clipping | Natural content height and width against the card's main area; any element past the canvas edge | Content does not fit even at the smallest scale | Cut text, split into two cards, or choose a sparser layout. Never shrink below the minimum font. |
| Minimum font | Smallest computed font size among all visible text | Below the format's `min_font` (34 px at 1080 wide for most formats) | Cut text. Small text is clamped to the minimum, so this fails only when something else has gone wrong. |
| Contrast, solid backgrounds | WCAG contrast ratio of each text run against the nearest solid background | Below 3:1 for large text (32 px or more, or 24 px and bold) or 4.5:1 for smaller text | Change the color, or put the text on a solid panel. |
| Contrast, text over a photo | The card is rendered again with the text hidden; pixels behind each text box are sampled and compared with the text color (10th percentile, so one dark patch cannot hide a bright one) | Below the same thresholds | Darken with `scrim`, move the text to a quieter side (`safe`), switch `ink`, or use another picture. Needs Pillow; without it the report says "not verified". |
| Fill | Natural content height as a share of the card's main area | Warned when a `list`, `steps`, `points`, `compare` or `product` card is under 50% full | Add content, merge with a neighbor, or pick a sparser layout. Cover, quote, stat and image cards are meant to be sparse. |
| Short last line | Last rendered line of each text block | Warned when a block of two or more lines ends in a line shorter than about two characters' width | Rephrase, or add a manual line break. |
| Repeated layouts | Spec check | Warned when two neighbors use the same layout (except cover, cta, image, avatar, banner, product) | Change one of them. |
| Export size | PNG header | Exported size differs from the format | Rebuild. |

## Scaling

Each layout is a "fill" layout (grows up to about 1.3 times to use the space) or a "shrink" layout (stays at its natural size and shrinks only if needed). The report's Scale column shows the factor used. A scale well under 1 means the card is crowded; consider splitting it even if it passes.

## What the gates do not cover

State these honestly in the delivery message when they apply:

- **Taste.** Passing every gate means "no known defects", not "good design".
- **Text over a photo without Pillow.**
- **Platform behavior**: crops, compression, safe areas, AI-content labels. Check the platform's current rules.
- **Color vision differences** beyond the contrast ratio.
- **Meaning**: whether the copy is accurate. Numbers and claims must come from the user.

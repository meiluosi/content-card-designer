# Workflow in detail

## Contents
- 1. The brief
- 2. Style directions
- 3. Planning the cards
- 4. Build, check, fix
- 5. Delivery
- 6. Changing things later

## 1. The brief

Ask at most five short questions, in one message, skipping anything already stated.

1. **Where and for what?** Platform or use (note, carousel, article cover, avatar, banner), which sets the format.
2. **Who reads it?** The reader and what they are doing when they see it.
3. **What should it feel like?** One feeling in the user's words: warm, calm and efficient, sharp and informative, personal, playful, serious. This drives the mood.
4. **What is the content?** The text, notes or outline. If it is long, you will propose how to split it.
5. **What real material and brand details exist?** Screenshots, product photos, numbers, logo, colors, fonts, an account name.

Then write a short design brief. The fields are adapted from the usual image-prompt structure, but here they drive layout rather than a model:

| Field | Example |
|---|---|
| Subject and content | Five kinds of content for a creator's weekly plan |
| Key elements | A list of five items; one real screenshot |
| Mood and style | Knowledge-heavy, sharp, high contrast |
| Palette and light | Off-white paper, near-black ink, one red accent |
| Composition | Big title top left; one claim per card; no photo |
| Platform and format | Xiaohongshu, `xhs-3x4`, 5 cards |
| Density | Medium; no card over about 140 characters |

If the user says "just make it", write the brief yourself, state your assumptions in one line and carry on.

## 2. Style directions

Infer the mood from the user's words and the content (see `mood-to-style.md`). If the look is not settled, render the first card in two or three moods:

```bash
python3 scripts/cardkit.py directions spec.json --moods warm,efficient,knowledge
```

Show the overview, name the moods, say which you would pick and why, and let the user choose. Once chosen, set `mood` in the spec (and in the brand kit, if they have one) so every card uses it.

## 3. Planning the cards

- Count the claims in the content. One claim per card gives the card count; stay inside the format's range.
- Give each card a layout from `layouts.md`; avoid neighbors with the same layout.
- Write a plan before the spec: card number, layout, the one claim, the text. If the user asked to approve first, show it. Otherwise go ahead.
- Keep each card inside the format's character budget (`max_chars` in `assets/formats.json`), measured across all its text.

## 4. Build, check, fix

1. Write `spec.json` and run `lint`.
2. Run `build`. Read `REPORT.md`.
3. For each failure, change the content, not the thresholds: cut text, split a card, choose another layout, change the text color or panel.
4. Rebuild until everything passes, or tell the user exactly what still fails and why.
5. Open the overview image and look at it. The gates catch defects, not ugliness. Fix anything that looks wrong even if every gate passes.

## 5. Delivery

Give the user: the PNGs, `overview.png`, `REPORT.md`, the HTML sources, and the spec. Say:

- what was shortened or changed in their text;
- which gates passed and what was not verified;
- that platform sizes are starting points and should be checked against the platform's current rules.

## 6. Changing things later

Edit the spec and rebuild; the HTML sources are also self-contained and can be edited by hand. To restyle, change `mood` or the brand kit. To add a format, add an entry to `assets/formats.json`.

# Spec reference

A spec is a JSON file. Run `python3 scripts/cardkit.py lint spec.json` to check it before rendering.

## Top level

| Field | Meaning |
|---|---|
| `format` | One id from `assets/formats.json` (`xhs-3x4`, `ig-4x5`, `square-1x1`, `wide-16x9`, `wechat-cover-21x9`, `story-9x16`, `avatar-1x1`, `banner-3x1`). Default `xhs-3x4`. |
| `mood` | One of `warm`, `efficient`, `knowledge`, `story`, `playful`, `analytical`. Default `efficient`. |
| `brand` | A path to a brand kit JSON, or the object itself. Overrides the mood's tokens. See below. |
| `footer` | Text at the bottom left of each card, or `false` to hide the footer. Defaults to the brand's `footer_left` or `name`. |
| `page_numbers` | `false` to hide "2/5". Default true. |
| `progress` | `"dots"` (default) shows progress dots in the footer; any other value hides them. |
| `cards` | List of cards. Each has a `layout` and that layout's fields. |

In any text field, `\n` is a line break and `**word**` is bold. Everything else is escaped, so the spec cannot inject HTML.

Colors in cards are either a hex value or `a1` to `a5`, the mood's five accent colors.

## Layouts

`*` marks a required field.

| Layout | Fields | Notes |
|---|---|---|
| `cover` | `title`*, `kicker`, `subtitle`, `chips` (strings or `{text, color}`), `rule` (default true: a short accent bar above the title), `deco` (`"circles"` adds large soft accent circles) | Title is large. Chips sit at the bottom (right side on wide canvases). On wide canvases the title scales up to use the space. With no chips the title block is centered vertically. `deco` reserves a zone for the circles that text never enters and hides the footer, so put the account name in `kicker` if you want it shown. Use it for friendly or playful looks; leave it off for restrained ones. |
| `list` | `items`* (`{name*, tag, detail, color}`), `kicker`, `title` | Rows with a colored bar. Two columns on wide canvases. |
| `steps` | `groups`* (`{label, kind, items}`), `kicker`, `title` | `kind` is `steps` (numbered boxes), `chips` (filled) or `pills` (outlined). |
| `points` | `boxes`* (`{head, body}`), `kicker`, `title` | Short statement boxes. |
| `point` | `title`*, `number`, `kicker`, `body`, `compare` (`{a: {label, text}, b: {label, text}}`), `code`, `color` | One numbered point per card: big numeral, title, optional supporting line, an optional two-state comparison and an optional code block. Only include `body`, `compare` and `code` text the user gave you. |
| `compare` | `left`*, `right`* (`{head, items, color}`), `kicker`, `title` | Two columns on wide canvases, stacked otherwise. |
| `stat` | `value`*, `caption`*, `notes`, `kicker`, `title`, `color` | One big number. The number must come from the user. |
| `quote` | `text`*, `by` | A single statement; the text scales up to fill the card. |
| `cta` | `kicker`, `title`, `steps`, `note` (`{head, body}`), `code` | Closing card. `code` is shown in a monospace block. |
| `image` | `title`*, `bg`*, `kicker`, `subtitle`, `safe`, `ink` | Text over a picture. `bg` is a path or `{src, scrim}` (scrim 0 to 0.7 darkens the picture). `safe` is `left`, `right`, `top` or `bottom`, the side the text sits on. `ink` is `light` or `dark`. |
| `product` | `product`*, `title`, `kicker`, `specs` (up to two short labels shown on one line), `bullets`, `bg`, `bg_color`, `align` | Your product image, unchanged, centered on the mood background (with a soft glow), a solid color (`bg_color`) or a picture (`bg`). If the PNG has empty transparent margins they are trimmed; visible pixels are never changed. Needs Pillow for the trim. |
| `avatar` | `mark`* (up to about 3 characters), `shape`, `color` | `shape` is `circle`, `rounded` or `square`. No footer. |
| `banner` | `title`*, `subtitle`, `handle` | Profile header. No footer. |

Paths in `bg`, `product` are relative to the spec file.

## Example

```json
{
  "format": "xhs-3x4",
  "mood": "knowledge",
  "footer": "my-account",
  "cards": [
    {"layout": "cover", "title": "One topic,\nfive kinds of posts", "subtitle": "A plan you can start this week",
     "chips": ["Tutorial", "Case", "Opinion"]},
    {"layout": "list", "title": "Each does one job",
     "items": [{"name": "Tutorial", "tag": "clarity", "detail": "How do I do this?"},
               {"name": "Case", "tag": "credibility", "detail": "Did it work for anyone?"}]},
    {"layout": "cta", "title": "Try it", "steps": ["Install", "Say your topic"]}
  ]
}
```

## Brand kit

`assets/brand-kit.template.json` lists every field. All are optional.

| Field | Meaning |
|---|---|
| `name`, `handle`, `footer_left` | Used for the footer and banner. |
| `mood` | Default mood when the spec does not set one. |
| `palette` | `bg`, `ink`, `muted`, `surface`, `line`, `accents` (up to five). Override the mood. |
| `fonts` | `title`, `body`: CSS font stacks. System fonts only. |
| `radius` | Corner radius at 1080 px wide. |
| `avoid` | Notes for you, not enforced by code. Respect them. |

## Formats

`assets/formats.json` holds the canvas size, margin, minimum font size, usual card count and character budget per format. Sizes are starting points and every format is marked `verify`. Edit the file when a platform's rules change; do not hard-code sizes elsewhere.

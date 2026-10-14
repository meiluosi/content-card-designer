# Avatars, banners and style boards

## Avatars (`avatar-1x1`, layout `avatar`)

- A short mark (one to three characters, a monogram or a symbol character) on a solid accent color.
- Keep the mark inside the central circle: many platforms crop avatars to a circle.
- One shape and one color per account, kept in the brand kit so cards and avatar match.
- A mark is not a logo. It is fine for a profile picture; it is not a print-ready identity.

## Profile banners (`banner-3x1`, layout `banner`)

- A short statement of what the account is about, an optional subtitle and the handle.
- Platforms crop and overlay banners differently, so keep everything in the central part and leave the corners empty. Check the platform's current safe area.
- Reuse the brand kit's palette and fonts.

## Style boards

When the user is exploring a look, make a board instead of one design:

```bash
python3 scripts/cardkit.py directions spec.json --moods warm,efficient,knowledge,story
```

The first card of the spec is rendered once per mood into one overview. Use it to:

1. Let the user react to concrete options rather than describe taste.
2. Narrow to one direction.
3. Write the choice into `brand-kit.json` (mood, palette, fonts) so everything after matches.

For a brand identity that will be printed or trademarked, a style board is early exploration only; the final mark is a job for a designer.

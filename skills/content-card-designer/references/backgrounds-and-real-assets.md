# Backgrounds and real assets

## The rule

Text is rendered by the browser. Images supply atmosphere and evidence. They never carry words, and real evidence is never redrawn.

## Real assets stay real

Screenshots, product photos, charts from the user, logos and numbers are placed as supplied:

- Do not recolor, retouch, regenerate or "clean up" them.
- Do not change a product's shape, label or color. If the background needs changing, change the background.
- Prefer a product image with a transparent background. A drop shadow added in CSS only affects the area outside the product.
- Claims on a product card (features, numbers, prices) come only from the user.
- Crop only when the user asked, and never through faces, key text on a screenshot or product details.

## When a background picture helps

Use one when the card needs atmosphere that flat color cannot give: a cover, a quote, a seasonal feel. Do not add one to a content-heavy card.

Sources, in order of preference: the user's own photos; images the user generates with any tool; stock images the user has the right to use. You can't make photographs or painterly illustrations yourself.

## Briefing a background for an image tool

If the user wants an AI-made background, write them a brief to use with the tool of their choice. Use this shape (in your own words for the scene):

```
<scene or subject>, <style>, <palette and light>, <mood>.
Composition: leave the <left third> calm and low in detail for text; subject on the <right>.
No text, letters, numbers, logos or watermarks anywhere.
<aspect ratio>, <intended use>.
```

Match the aspect ratio to the format and the empty zone to the card's `safe` side. Save the result next to the spec and reference it in `bg`.

## Text over a picture

- Put text on the quiet side (`safe`), not over the subject. Never cover a face or a product.
- Choose `ink` (`light` or `dark`) to contrast with the picture, and add `scrim` (a dark veil, 0 to 0.7) only as much as needed.
- The contrast gate samples the pixels behind each text box. If it fails, change the scrim, the side, the ink or the picture. It needs Pillow; without Pillow the report says text over photos was not verified, and you must say so.

## Product posters

A `product` card puts the supplied image on a solid color or a picture with a short title and up to three bullets. Keep the background simple so the product is the subject. Ask the user for the product facts; do not invent any.

## Disclosure

Some platforms ask creators to label AI-generated images or restrict automated posting. If the user uses an AI-made background, remind them to check the platform's current rules. Do not state specific rules from memory.

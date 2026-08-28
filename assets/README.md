# assets

Local visual assets used by the profile README. Swap files to customize — the README keeps the same relative paths, so nothing else needs to change.

## Slots

| Slot | Current file | Replace with |
|---|---|---|
| Hero banner | `banner.svg` | your own `banner.gif` (then update the `src` in `README.md`) |
| Wave divider | `divider.svg` | `divider.gif` |
| Animated emojis | — use `emojis/` | drop GIFs such as `hello.gif`, then reference them with `<img src="./assets/emojis/hello.gif" width="28" />` |
| Side decorations | — use `decorations/` | drop GIFs such as `left.gif` / `right.gif` and reference them in the README |

## Tips

- Keep paths relative, e.g. `./assets/banner.gif` — they resolve from the repo root.
- Prefer your own GIFs or royalty-free / CC0 ones; avoid hotlinking random GIFs (they break and can be removed without notice).
- Small GIFs (1048px or less wide, under ~2 MB) keep the profile fast.
- Replace the SVG files with GIFs is optional — the current SVGs already animate on their own.
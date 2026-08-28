#!/usr/bin/env python3
"""
Bake a flat, on-palette overlay onto every frame of assets/banner.gif.

Why flat compositing?
  Re-encoding the animation's RGB frames beats 6 MB; the reason the original
  GIF is only 2.7 MB is its per-frame encoding (local palettes / sub-images)
  that Pillow cannot reproduce. Alpha-blended overlays also turn the panel into
  nearest-palette noise, which explodes the file size again. So the overlay is
  drawn with a tiny set of solid colors, each inserted verbatim into the GIF's
  global palette, and composited by *replacing* palette indices - the animated
  background outside the overlay keeps its original colors.

  Caveat handled here: the original declares transparency (index 255), so
  Pillow decodes frames 1+ as RGBA and convert("P") would re-quantise them to
  Pillow's *own* palette. We therefore rebuild each such frame from its true
  RGB colours, picking the nearest entry of the (extended) global palette
  without dither. Frame 0 keeps its exact source indices.

  Result: assets/banner-final.gif at ~1.4x the original size, timing/loop
  preserved, and the background animation unchanged apart from 7 palette
  entries repurposed for the overlay colours (chosen to be rare and
  colour-close, so the stray re-coloured pixels are imperceptible).

  Antialiasing is achieved by supersampling the glyph masks (4x), downscaling
  and thresholding to binary - smooth silhouette, but still a single palette
  color. Design source: assets/banner-overlay.svg.

Usage:  python assets/generate-banner.py
"""

from __future__ import annotations

import math
import os
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "banner.gif")
OUT = os.path.join(ROOT, "banner-final.gif")
PREVIEW = os.path.join(ROOT, "banner-preview.png")

FONTS = {
    "title": [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf", "arialbd.ttf"],
    "role": [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf", "arial.ttf"],
    "mono": [r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf", "cour.ttf"],
    "mono_bold": [r"C:\Windows\Fonts\consolab.ttf", r"C:\Windows\Fonts\courbd.ttf", "courbd.ttf"],
}

# Overlay colors. Each entry is inserted verbatim into the GIF palette, so the
# overlay never introduces blended pixel noise. (Accent: purple -> cyan -> pink.)
PURPLE = (163, 113, 247)   # #a371f7
CYAN = (57, 197, 207)      # #39c5cf
PINK = (247, 120, 186)     # #f778ba
BACK = (21, 15, 38)        # panel / chip base (dark violet "glass")
SHEEN = (43, 30, 74)       # glass sheen strip on panel top
BORDER = (74, 58, 120)     # panel / chip border
LIGHT = (232, 232, 244)    # all text

ACCENTS = [PURPLE, CYAN, PINK, BACK, SHEEN, BORDER, LIGHT]


def pick_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONTS[kind]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise SystemExit(f"No usable font for '{kind}' (tried {FONTS[kind]})")


def star_points(cx, cy, r_long, r_short, rot=math.pi / 2):
    pts = []
    for i in range(8):
        ang = rot + i * math.pi / 4
        rr = r_long if i % 2 == 0 else r_short
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    return pts


def rounded_mask(W, H, box, radius):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius=radius, fill=255)
    return np.asarray(m, dtype=np.float64) / 255.0


def ring_mask(W, H, box, radius, width):
    outer = rounded_mask(W, H, box, radius)
    inner = rounded_mask(W, H, (box[0] + width, box[1] + width, box[2] - width, box[3] - width),
                         max(0, radius - width))
    return np.clip(outer - inner, 0.0, 1.0)


def build_overlay(W, H, ss=4):
    """Return (flat RGB image, alpha mask) at 1x.

    All text is supersampled `ss`x then thresholded back to binary so glyph
    edges look smooth while still using a single solid color.
    """
    flat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(flat)

    def solid_text(x, y, txt, kind, size, color, anchor="ls", halo=((0, 0),)):
        tmp = Image.new("L", (W * ss, H * ss), 0)
        td = ImageDraw.Draw(tmp)
        font_ss = pick_font(kind, int(size * ss))
        for (dx, dy) in halo:
            td.text((x * ss + dx, y * ss + dy), txt, font=font_ss, fill=255, anchor=anchor)
        td.text((x * ss, y * ss), txt, font=font_ss, fill=255, anchor=anchor)
        tmp = tmp.resize((W, H), Image.LANCZOS)
        m = np.asarray(tmp, dtype=np.float64) / 255.0
        # chromatic half-pixel alpha -> hard mask (keeps a single palette color)
        mask = Image.fromarray(np.where(m > 0.30, 255, 0).astype(np.uint8), "L")
        flat.paste(Image.new("RGBA", (W, H), color + (255,)), (0, 0), mask)

    def centered_baseline(cx, cy, txt, kind, size, color, halo=((0, 0),)):
        f = pick_font(kind, size)
        wch = sum(f.getlength(c) for c in txt)
        x = cx - wch / 2.0
        for c in txt:
            solid_text(x, cy, c, kind, size, color, anchor="ls", halo=halo)
            x += f.getlength(c)

    # panel (solid dark "glass" sheet)
    p_x, p_y, p_w, p_h, p_r = 216, 135, 768, 405, 54
    d.rounded_rectangle((p_x, p_y, p_x + p_w, p_y + p_h), radius=p_r, fill=BACK)
    d.rounded_rectangle((p_x, p_y, p_x + p_w, p_y + p_h), radius=p_r, outline=BORDER, width=2)
    # sheen strip along the top edge
    d.rectangle((p_x + 6, p_y + 4, p_x + p_w - 6, p_y + 10), fill=SHEEN)

    # accent bar (3 flat segments, purple -> cyan -> pink)
    bar_x, bar_y, bar_w, bar_h = 420, 138, 360, 5
    for i, col in enumerate((PURPLE, CYAN, PINK)):
        x0 = bar_x + i * bar_w // 3
        x1 = bar_x + (i + 1) * bar_w // 3
        d.rectangle((x0, bar_y, x1, bar_y + bar_h), fill=col)

    # texts
    centered_baseline(600, 273, "Lê Đình Bách", "title", 92, LIGHT,
                      halo=((0, 2), (0, -2), (2, 0), (-2, 0)))
    centered_baseline(600, 327, "SOFTWARE DEVELOPER · VIETNAM", "role", 31, LIGHT)
    centered_baseline(600, 376, "building things, breaking things, learning things.", "mono", 27, LIGHT)

    # chip
    chip_text = "@ledinhbach2k4 · EnviroMental"
    f_chip = pick_font("mono_bold", 27)
    chip_w = sum(f_chip.getlength(c) for c in chip_text) + 88
    chip_x0 = 600 - chip_w / 2.0
    chip_y0, chip_h = 419, 68
    d.rounded_rectangle((chip_x0, chip_y0, chip_x0 + chip_w, chip_y0 + chip_h), radius=34,
                        fill=BACK, outline=BORDER, width=2)
    d.ellipse((chip_x0 + 22, chip_y0 + 26, chip_x0 + 38, chip_y0 + 42), fill=CYAN)
    solid_text(chip_x0 + 48, chip_y0 + 34, chip_text, "mono_bold", 27, LIGHT, anchor="lm")

    # code decorations
    solid_text(150, 170, "</>", "mono", 46, PURPLE, anchor="ls")
    solid_text(1005, 505, "{ dev }", "mono", 38, CYAN, anchor="ls")

    # sparkles
    d.polygon(star_points(120, 315, 45, 15), fill=PURPLE)
    d.polygon(star_points(1092, 196, 18, 6), fill=PINK)

    # outer rounded frame (solid accent)
    ring = ring_mask(W, H, (3, 3, W - 3, H - 3), 36, 3)
    frame = np.zeros((H, W, 4), dtype=np.float64)
    frame[..., 0:3] = PURPLE
    frame[..., 3] = ring * 255
    flat.alpha_composite(Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), "RGBA"))

    arr = np.asarray(flat, dtype=np.float64)
    return arr[..., :3], (arr[..., 3] / 255.0)


def build_extended_palette(orig_palette, frame_index_arrays, accents):
    """Give each accent its own palette slot.

    GIF allows only 256 palette entries, so len(accents) original entries are
    repurposed. To keep the animation looking untouched, the slot chosen for
    each accent is the least-used entry among the ones whose colour is closest
    to that accent - recolouring the rare pixels that use it is then
    imperceptible.
    """
    pal = orig_palette.copy()
    usage = Counter()
    for arr in frame_index_arrays:
        for idx, n in zip(*np.unique(arr, return_counts=True)):
            usage[int(idx)] += int(n)

    available = [i for i in range(256) if i != 255]
    max_usage = max(usage.values()) or 1
    chosen = []
    for acc in accents:
        acc = np.array(acc, dtype=np.int32)
        arr = np.array(available, dtype=np.int32)
        dists = np.abs(pal[arr].astype(int) - acc).sum(axis=1)
        order = np.argsort(dists)[:60]                # keep only colour-closest
        cand = [arr[j] for j in order]
        # balance rarity (avoid restamping busy colours) against hue distance
        # (the recoloured strays must stay invisible).
        cand.sort(key=lambda i: 0.4 * (usage.get(int(i), 0) / max_usage)
                  + 0.6 * (int(np.abs(pal[i].astype(int) - acc).sum()) / 1530.0))
        idx = int(cand[0])
        pal[idx] = acc
        chosen.append(idx)
        available.remove(idx)
    return pal, chosen


def nearest_palette_index(rgb, palette):
    """Nearest index into `palette` (Nx3) for every pixel, no dithering.

    rgb: (H, W, 3) uint8 -> (H, W) int32 index array.  Processed in row blocks
    so the (H, W, N) distance tensor never exceeds ~100 MB.
    """
    pal = np.asarray(palette, dtype=np.int32)
    H, W = rgb.shape[:2]
    out = np.empty((H, W), dtype=np.int32)
    blk = max(1, 100_000_000 // (W * len(pal) * 4))     # rows per block
    for y0 in range(0, H, blk):
        y1 = min(H, y0 + blk)
        d = np.abs(rgb[y0:y1].astype(np.int32)[..., None, :] - pal[None, None, :, :]).sum(-1)
        out[y0:y1] = d.argmin(-1)
    return out


def main():
    src = Image.open(SRC)
    W, H = src.size
    print(f"source: {SRC} {W}x{H} frames={src.n_frames}")

    # decode true content per frame: exact indices where Pillow keeps P mode,
    # otherwise the accurate RGB colours (frames 1+ decode RGBA because the
    # original declares a transparency index).
    exact_idx = []
    true_rgb = []
    for i in range(src.n_frames):
        src.seek(i)
        if src.mode == "P":
            exact_idx.append(np.asarray(src.convert("P"), dtype=np.uint8).copy())
            true_rgb.append(None)
        else:
            exact_idx.append(None)
            true_rgb.append(np.asarray(src.convert("RGB"), dtype=np.uint8))

    src.seek(0)
    orig_palette = np.frombuffer(bytes(src.getpalette()), dtype=np.uint8).copy().reshape(256, 3)

    # palette-usage stats that reflect the real content
    usage_arrays = []
    for i in range(src.n_frames):
        if exact_idx[i] is not None:
            usage_arrays.append(exact_idx[i])
        else:
            usage_arrays.append(nearest_palette_index(true_rgb[i], orig_palette).astype(np.uint8))

    ext_palette, drops = build_extended_palette(orig_palette, usage_arrays, ACCENTS)
    print(f"freed palette entries {drops} for overlay colors {ACCENTS}")

    kept = np.array([i for i in range(256) if i not in drops], dtype=np.int32)   # 249 slots
    drop_remap = {}
    for d in drops:
        dists = np.abs(orig_palette[d].astype(int) - orig_palette[kept].astype(int)).sum(1)
        drop_remap[int(d)] = int(kept[dists.argmin()])

    ac_colors = np.array(ACCENTS, dtype=np.int32)
    ac_idx_arr = np.array([int(np.argmin(np.abs(ext_palette.astype(int) - c).sum(1))) for c in ACCENTS],
                          dtype=np.int32)

    print("building overlay ...")
    flat_rgb, ovmask = build_overlay(W, H)
    flat_rgb = flat_rgb.astype(np.int32)

    print("replacing palette indices in every frame ...")
    out_frames = []
    for i in range(src.n_frames):
        if exact_idx[i] is not None:
            base = exact_idx[i].astype(np.int32)
            for d, r in drop_remap.items():
                base = np.where(base == d, r, base)
        else:
            base = nearest_palette_index(true_rgb[i], ext_palette[kept]).astype(np.int32)
            base = kept[base]
        d6 = np.abs(flat_rgb[..., None, :] - ac_colors[None, None, :, :]).sum(-1)
        best = ac_idx_arr[d6.argmin(-1)]
        new_idx = np.where(ovmask > 0.5, best, base)
        f = Image.fromarray(new_idx.astype(np.uint8), "P")
        f.putpalette([int(c) for c in ext_palette.flatten().tolist()])
        out_frames.append(f)

    durations = [src.info.get("duration", 60)] * len(out_frames)
    loop = src.info.get("loop", 0)

    out_frames[0].save(OUT, save_all=True, append_images=out_frames[1:], duration=durations,
                       loop=loop, optimize=False)
    print(f"wrote {OUT}: {os.path.getsize(OUT) / 1024:.1f} KB")

    pv = out_frames[0].convert("RGB")
    if pv.width > 900:
        pv = pv.resize((900, int(pv.height * 900 / pv.width)), Image.LANCZOS)
    pv.save(PREVIEW)
    print(f"wrote {PREVIEW}: {os.path.getsize(PREVIEW) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
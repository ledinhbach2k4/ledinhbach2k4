#!/usr/bin/env python3
"""
Generate an animated GIF with a flat palette-based developer overlay.

Source:
    assets/banner.gif

Output:
    assets/banner-final.gif
    assets/banner-preview.png

The script is optimized for large animated GIFs by using a reduced
5-bit/channel RGB lookup table instead of comparing every pixel against
all 256 palette colors.
"""

from __future__ import annotations

import math
import os
import time
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = os.path.dirname(os.path.abspath(__file__))

SRC = os.path.join(ROOT, "banner.gif")
OUT = os.path.join(ROOT, "banner-final.gif")
PREVIEW = os.path.join(ROOT, "banner-preview.png")


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

FONTS = {
    "title": [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "arialbd.ttf",
    ],
    "role": [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "arial.ttf",
    ],
    "mono": [
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\cour.ttf",
        "cour.ttf",
    ],
    "mono_bold": [
        r"C:\Windows\Fonts\consolab.ttf",
        r"C:\Windows\Fonts\courbd.ttf",
        "courbd.ttf",
    ],
}


# ---------------------------------------------------------------------------
# Overlay palette
# ---------------------------------------------------------------------------

PURPLE = (163, 113, 247)   # #a371f7
CYAN = (57, 197, 207)      # #39c5cf
PINK = (247, 120, 186)     # #f778ba
BACK = (21, 15, 38)         # #150f26
SHEEN = (43, 30, 74)       # #2b1e4a
BORDER = (74, 58, 120)     # #4a3a78
LIGHT = (232, 232, 244)    # #e8e8f4

ACCENTS = [
    PURPLE,
    CYAN,
    PINK,
    BACK,
    SHEEN,
    BORDER,
    LIGHT,
]


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def pick_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONTS[kind]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue

    raise SystemExit(
        f"No usable font for '{kind}' "
        f"(tried {FONTS[kind]})"
    )


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def star_points(cx, cy, r_long, r_short, rot=math.pi / 2):
    pts = []

    for i in range(8):
        ang = rot + i * math.pi / 4
        rr = r_long if i % 2 == 0 else r_short

        pts.append(
            (
                cx + rr * math.cos(ang),
                cy + rr * math.sin(ang),
            )
        )

    return pts


def rounded_mask(W, H, box, radius):
    m = Image.new("L", (W, H), 0)

    ImageDraw.Draw(m).rounded_rectangle(
        box,
        radius=radius,
        fill=255,
    )

    return np.asarray(m, dtype=np.float32) / 255.0


def ring_mask(W, H, box, radius, width):
    outer = rounded_mask(W, H, box, radius)

    inner = rounded_mask(
        W,
        H,
        (
            box[0] + width,
            box[1] + width,
            box[2] - width,
            box[3] - width,
        ),
        max(0, radius - width),
    )

    return np.clip(outer - inner, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Build overlay
# ---------------------------------------------------------------------------

def build_overlay(W, H, ss=4):
    """
    Return:

        flat_rgb : H x W x 3 uint8
        ovmask   : H x W float32

    The overlay uses flat colors only, avoiding GIF dithering/noise.
    """

    flat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(flat)

    def solid_text(
        x,
        y,
        txt,
        kind,
        size,
        color,
        anchor="ls",
        halo=((0, 0),),
    ):
        tmp = Image.new(
            "L",
            (W * ss, H * ss),
            0,
        )

        td = ImageDraw.Draw(tmp)

        font_ss = pick_font(
            kind,
            int(size * ss),
        )

        for dx, dy in halo:
            td.text(
                (
                    int(x * ss + dx),
                    int(y * ss + dy),
                ),
                txt,
                font=font_ss,
                fill=255,
                anchor=anchor,
            )

        td.text(
            (
                int(x * ss),
                int(y * ss),
            ),
            txt,
            font=font_ss,
            fill=255,
            anchor=anchor,
        )

        tmp = tmp.resize(
            (W, H),
            Image.Resampling.LANCZOS,
        )

        m = np.asarray(
            tmp,
            dtype=np.float32,
        ) / 255.0

        # Binary threshold.
        # This keeps the result palette-friendly.
        mask = Image.fromarray(
            np.where(
                m > 0.30,
                255,
                0,
            ).astype(np.uint8),
            "L",
        )

        flat.paste(
            Image.new(
                "RGBA",
                (W, H),
                color + (255,),
            ),
            (0, 0),
            mask,
        )

    def centered_baseline(
        cx,
        cy,
        txt,
        kind,
        size,
        color,
        halo=((0, 0),),
    ):
        f = pick_font(
            kind,
            size,
        )

        widths = [
            f.getlength(c)
            for c in txt
        ]

        total_width = sum(widths)

        x = cx - total_width / 2.0

        for c, char_width in zip(txt, widths):
            solid_text(
                x,
                cy,
                c,
                kind,
                size,
                color,
                anchor="ls",
                halo=halo,
            )

            x += char_width

    # -----------------------------------------------------------------------
    # Main panel
    # -----------------------------------------------------------------------

    p_x = 216
    p_y = 135
    p_w = 768
    p_h = 405
    p_r = 54

    d.rounded_rectangle(
        (
            p_x,
            p_y,
            p_x + p_w,
            p_y + p_h,
        ),
        radius=p_r,
        fill=BACK,
    )

    d.rounded_rectangle(
        (
            p_x,
            p_y,
            p_x + p_w,
            p_y + p_h,
        ),
        radius=p_r,
        outline=BORDER,
        width=2,
    )

    # Glass sheen.
    d.rectangle(
        (
            p_x + 6,
            p_y + 4,
            p_x + p_w - 6,
            p_y + 10,
        ),
        fill=SHEEN,
    )

    # -----------------------------------------------------------------------
    # Accent bar
    # -----------------------------------------------------------------------

    bar_x = 420
    bar_y = 138
    bar_w = 360
    bar_h = 5

    for i, col in enumerate(
        (PURPLE, CYAN, PINK)
    ):
        x0 = bar_x + i * bar_w // 3
        x1 = bar_x + (i + 1) * bar_w // 3

        d.rectangle(
            (
                x0,
                bar_y,
                x1,
                bar_y + bar_h,
            ),
            fill=col,
        )

    # -----------------------------------------------------------------------
    # Text
    # -----------------------------------------------------------------------

    centered_baseline(
        600,
        273,
        "Lê Đình Bách",
        "title",
        92,
        LIGHT,
        halo=(
            (0, 2),
            (0, -2),
            (2, 0),
            (-2, 0),
        ),
    )

    centered_baseline(
        600,
        327,
        "LOWKEY · BUILDING RANDOM STUFF",
        "role",
        31,
        LIGHT,
    )

    centered_baseline(
        600,
        376,
        "turning random ideas into things on GitHub.",
        "mono",
        27,
        LIGHT,
    )

    # -----------------------------------------------------------------------
    # Chip
    # -----------------------------------------------------------------------

    chip_text = "@ledinhbach2k4 · EnviroMental"

    f_chip = pick_font(
        "mono_bold",
        27,
    )

    chip_w = (
        sum(
            f_chip.getlength(c)
            for c in chip_text
        )
        + 88
    )

    chip_x0 = 600 - chip_w / 2.0
    chip_y0 = 419
    chip_h = 68

    d.rounded_rectangle(
        (
            chip_x0,
            chip_y0,
            chip_x0 + chip_w,
            chip_y0 + chip_h,
        ),
        radius=34,
        fill=BACK,
        outline=BORDER,
        width=2,
    )

    d.ellipse(
        (
            chip_x0 + 22,
            chip_y0 + 26,
            chip_x0 + 38,
            chip_y0 + 42,
        ),
        fill=CYAN,
    )

    solid_text(
        chip_x0 + 48,
        chip_y0 + 34,
        chip_text,
        "mono_bold",
        27,
        LIGHT,
        anchor="lm",
    )

    # -----------------------------------------------------------------------
    # Code decorations
    # -----------------------------------------------------------------------

    solid_text(
        150,
        170,
        "</>",
        "mono",
        46,
        PURPLE,
        anchor="ls",
    )

    solid_text(
        1005,
        505,
        "{ dev }",
        "mono",
        38,
        CYAN,
        anchor="ls",
    )

    # -----------------------------------------------------------------------
    # Sparkles
    # -----------------------------------------------------------------------

    d.polygon(
        star_points(
            120,
            315,
            45,
            15,
        ),
        fill=PURPLE,
    )

    d.polygon(
        star_points(
            1092,
            196,
            18,
            6,
        ),
        fill=PINK,
    )

    # -----------------------------------------------------------------------
    # Outer frame
    # -----------------------------------------------------------------------

    ring = ring_mask(
        W,
        H,
        (
            3,
            3,
            W - 3,
            H - 3,
        ),
        36,
        3,
    )

    frame = np.zeros(
        (H, W, 4),
        dtype=np.uint8,
    )

    frame[..., 0] = PURPLE[0]
    frame[..., 1] = PURPLE[1]
    frame[..., 2] = PURPLE[2]
    frame[..., 3] = np.clip(
        ring * 255,
        0,
        255,
    ).astype(np.uint8)

    flat.alpha_composite(
        Image.fromarray(
            frame,
            "RGBA",
        )
    )

    arr = np.asarray(
        flat,
        dtype=np.uint8,
    )

    alpha = arr[..., 3].astype(
        np.float32
    ) / 255.0

    return (
        arr[..., :3],
        alpha,
    )


# ---------------------------------------------------------------------------
# Palette utilities
# ---------------------------------------------------------------------------

def normalize_palette(raw_palette):
    """
    Pillow palettes can theoretically be shorter than 768 bytes.
    Normalize to exactly 256 RGB entries.
    """

    raw = np.asarray(
        raw_palette,
        dtype=np.uint8,
    )

    if raw.size < 768:
        padded = np.zeros(
            768,
            dtype=np.uint8,
        )

        padded[: raw.size] = raw
        raw = padded

    return raw[:768].reshape(
        256,
        3,
    ).copy()


def build_rgb_lut(palette):
    """
    Build a 5-bit/channel RGB -> palette index LUT.

    32 * 32 * 32 = 32,768 RGB buckets.

    This replaces the expensive:

        H * W * 256

    calculation.

    The LUT is tiny and only needs to be built once per palette.
    """

    print("building 5-bit RGB palette LUT...")

    palette = np.asarray(
        palette,
        dtype=np.int16,
    )

    levels = np.arange(
        32,
        dtype=np.int16,
    )

    # Map 5-bit values to representative 8-bit RGB values.
    values = (
        levels * 255 + 15
    ) // 31

    r, g, b = np.meshgrid(
        values,
        values,
        values,
        indexing="ij",
    )

    colors = np.stack(
        (
            r.reshape(-1),
            g.reshape(-1),
            b.reshape(-1),
        ),
        axis=1,
    ).astype(np.int16)

    lut = np.empty(
        colors.shape[0],
        dtype=np.uint8,
    )

    # Process LUT colors in small chunks.
    # 32,768 * 256 is tiny compared to the old per-frame calculation.
    chunk = 2048

    for start in range(
        0,
        len(colors),
        chunk,
    ):
        end = min(
            len(colors),
            start + chunk,
        )

        c = colors[start:end]

        dist = np.abs(
            c[:, None, :] -
            palette[None, :, :]
        ).sum(axis=2)

        lut[start:end] = np.argmin(
            dist,
            axis=1,
        ).astype(np.uint8)

    print(
        f"palette LUT ready: {len(lut):,} RGB buckets"
    )

    return lut


def map_rgb_to_palette(
    rgb,
    lut,
):
    """
    Map RGB image to palette indices using the
    5-bit/channel LUT.

    Memory usage is approximately H*W instead of
    H*W*256.
    """

    rgb = np.asarray(
        rgb,
        dtype=np.uint8,
    )

    r = rgb[..., 0].astype(
        np.uint16
    ) >> 3

    g = rgb[..., 1].astype(
        np.uint16
    ) >> 3

    b = rgb[..., 2].astype(
        np.uint16
    ) >> 3

    key = (
        (r * 32 + g) * 32 + b
    )

    return lut[
        key
    ]


# ---------------------------------------------------------------------------
# Palette selection
# ---------------------------------------------------------------------------

def build_extended_palette(
    orig_palette,
    usage,
    accents,
):
    """
    Repurpose rare palette entries for overlay colors.

    Returns:

        extended_palette
        chosen_indices
    """

    pal = orig_palette.copy()

    available = [
        i
        for i in range(256)
        if i != 255
    ]

    max_usage = max(
        usage.values()
    ) if usage else 1

    chosen = []

    for acc in accents:
        acc_arr = np.array(
            acc,
            dtype=np.int32,
        )

        available_arr = np.array(
            available,
            dtype=np.int32,
        )

        distances = np.abs(
            pal[available_arr].astype(
                np.int32
            ) - acc_arr
        ).sum(axis=1)

        # Keep the closest candidates.
        order = np.argsort(
            distances
        )[:60]

        candidates = [
            int(available_arr[j])
            for j in order
        ]

        def score(index):
            usage_score = (
                usage.get(index, 0)
                / max_usage
            )

            color_score = (
                np.abs(
                    pal[index].astype(
                        np.int32
                    ) - acc_arr
                ).sum()
                / 1530.0
            )

            return (
                0.4 * usage_score
                + 0.6 * color_score
            )

        candidates.sort(
            key=score
        )

        idx = candidates[0]

        pal[idx] = np.array(
            acc,
            dtype=np.uint8,
        )

        chosen.append(idx)

        available.remove(idx)

    return pal, chosen


# ---------------------------------------------------------------------------
# Frame timing
# ---------------------------------------------------------------------------

def collect_frame_metadata(src):
    """
    Read per-frame duration and disposal information.
    """

    durations = []
    disposals = []

    for i in range(src.n_frames):
        src.seek(i)

        durations.append(
            src.info.get(
                "duration",
                60,
            )
        )

        disposals.append(
            src.info.get(
                "disposal",
                0,
            )
        )

    return durations, disposals


# ---------------------------------------------------------------------------
# Usage analysis
# ---------------------------------------------------------------------------

def collect_palette_usage(
    src,
    lut,
):
    """
    First pass.

    Decode frames one by one, convert to RGB,
    map them to the original global palette and
    accumulate usage counts.

    We intentionally do NOT keep all frames in RAM.
    """

    usage = Counter()

    total = src.n_frames

    print(
        "analyzing source palette usage..."
    )

    for i in range(total):
        src.seek(i)

        rgb = np.asarray(
            src.convert("RGB"),
            dtype=np.uint8,
        )

        indices = map_rgb_to_palette(
            rgb,
            lut,
        )

        values, counts = np.unique(
            indices,
            return_counts=True,
        )

        usage.update(
            dict(
                zip(
                    values.tolist(),
                    counts.tolist(),
                )
            )
        )

        del rgb
        del indices

        print(
            f"usage pass: frame {i + 1}/{total}"
        )

    return usage


# ---------------------------------------------------------------------------
# Overlay mapping
# ---------------------------------------------------------------------------

def build_overlay_indices(
    flat_rgb,
    ovmask,
    accents,
    chosen_indices,
):
    """
    Convert overlay colors to the exact palette slots selected
    by build_extended_palette().

    This is calculated ONCE, not once per frame.
    """

    H, W = ovmask.shape

    overlay_indices = np.zeros(
        (H, W),
        dtype=np.uint8,
    )

    # Every flat overlay pixel should correspond to one of ACCENTS.
    # Use exact RGB lookup rather than doing palette distance calculations.
    color_to_index = {
        tuple(color): int(index)
        for color, index in zip(
            accents,
            chosen_indices,
        )
    }

    # Only inspect pixels that actually belong to the overlay.
    mask = ovmask > 0.5

    if not np.any(mask):
        return overlay_indices

    colors = flat_rgb[mask]

    unique_colors, inverse = np.unique(
        colors,
        axis=0,
        return_inverse=True,
    )

    mapped = np.empty(
        len(unique_colors),
        dtype=np.uint8,
    )

    for i, color in enumerate(
        unique_colors
    ):
        key = tuple(
            int(v)
            for v in color
        )

        # All generated overlay colors should be exact palette colors.
        if key not in color_to_index:
            # Fallback: nearest accent.
            accent_arr = np.asarray(
                accents,
                dtype=np.int16,
            )

            color_arr = np.asarray(
                color,
                dtype=np.int16,
            )

            distances = np.abs(
                accent_arr - color_arr
            ).sum(axis=1)

            best = int(
                np.argmin(distances)
            )

            mapped[i] = int(
                chosen_indices[best]
            )
        else:
            mapped[i] = color_to_index[key]

    overlay_indices[mask] = mapped[
        inverse
    ]

    return overlay_indices


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    started = time.perf_counter()

    if not os.path.exists(SRC):
        raise SystemExit(
            f"Source GIF not found:\n{SRC}"
        )

    src = Image.open(SRC)

    W, H = src.size
    frame_count = src.n_frames

    print()
    print("=" * 70)
    print("Animated banner generator")
    print("=" * 70)
    print(
        f"source : {SRC}"
    )
    print(
        f"size   : {W}x{H}"
    )
    print(
        f"frames : {frame_count}"
    )
    print("=" * 70)
    print()

    # -----------------------------------------------------------------------
    # Source palette
    # -----------------------------------------------------------------------

    src.seek(0)

    raw_palette = src.getpalette()

    if raw_palette is None:
        raise SystemExit(
            "Source GIF has no global palette."
        )

    orig_palette = normalize_palette(
        raw_palette
    )

    # -----------------------------------------------------------------------
    # Frame metadata
    # -----------------------------------------------------------------------

    durations, disposals = collect_frame_metadata(
        src
    )

    loop = src.info.get(
        "loop",
        0,
    )

    print(
        f"loop: {loop}"
    )

    print(
        f"durations: "
        f"min={min(durations)}ms "
        f"max={max(durations)}ms"
    )

    # -----------------------------------------------------------------------
    # Build LUT
    # -----------------------------------------------------------------------

    lut = build_rgb_lut(
        orig_palette
    )

    # -----------------------------------------------------------------------
    # First pass: palette usage
    # -----------------------------------------------------------------------

    usage = collect_palette_usage(
        src,
        lut,
    )

    print()
    print(
        "source palette usage analyzed."
    )

    # -----------------------------------------------------------------------
    # Allocate palette slots for overlay
    # -----------------------------------------------------------------------

    ext_palette, chosen_indices = (
        build_extended_palette(
            orig_palette,
            usage,
            ACCENTS,
        )
    )

    print(
        "overlay palette slots:"
    )

    for color, index in zip(
        ACCENTS,
        chosen_indices,
    ):
        print(
            f"  index {index:3d} -> {color}"
        )

    # -----------------------------------------------------------------------
    # Build LUT for extended palette
    # -----------------------------------------------------------------------

    extended_lut = build_rgb_lut(
        ext_palette
    )

    # -----------------------------------------------------------------------
    # Build overlay
    # -----------------------------------------------------------------------

    print()
    print(
        "building overlay..."
    )

    flat_rgb, ovmask = build_overlay(
        W,
        H,
    )

    overlay_indices = build_overlay_indices(
        flat_rgb,
        ovmask,
        ACCENTS,
        chosen_indices,
    )

    # Release large overlay arrays we no longer need.
    del flat_rgb
    del ovmask

    print(
        "overlay ready."
    )

    # -----------------------------------------------------------------------
    # Second pass: generate frames
    # -----------------------------------------------------------------------

    print()
    print(
        "processing frames..."
    )

    out_frames = []

    src.seek(0)

    for i in range(frame_count):
        frame_start = time.perf_counter()

        src.seek(i)

        # Decode one frame only.
        rgb = np.asarray(
            src.convert("RGB"),
            dtype=np.uint8,
        )

        # Fast RGB -> palette conversion.
        base = map_rgb_to_palette(
            rgb,
            extended_lut,
        )

        # Composite overlay.
        mask = overlay_indices != 0

        if np.any(mask):
            base[mask] = overlay_indices[mask]

        frame = Image.fromarray(
            base,
            mode="P",
        )

        frame.putpalette(
            ext_palette.flatten().tolist()
        )

        out_frames.append(
            frame
        )

        elapsed = (
            time.perf_counter()
            - frame_start
        )

        print(
            f"processing frame "
            f"{i + 1}/{frame_count} "
            f"({elapsed:.2f}s)"
        )

        del rgb
        del base

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------

    print()
    print(
        "writing final GIF..."
    )

    out_frames[0].save(
        OUT,
        save_all=True,
        append_images=out_frames[1:],
        duration=durations,
        loop=loop,
        optimize=False,
        disposal=disposals,
    )

    output_size = os.path.getsize(
        OUT
    )

    # -----------------------------------------------------------------------
    # Validate output
    # -----------------------------------------------------------------------

    check = Image.open(
        OUT
    )

    check_frames = check.n_frames
    check_size = check.size

    print()
    print("=" * 70)
    print("OUTPUT VALIDATION")
    print("=" * 70)
    print(
        f"file   : {OUT}"
    )
    print(
        f"size   : {check_size[0]}x{check_size[1]}"
    )
    print(
        f"frames : {check_frames}"
    )
    print(
        f"loop   : {check.info.get('loop', 0)}"
    )
    print(
        f"file   : {output_size / 1024:.1f} KB"
    )
    print("=" * 70)

    if check_size != (W, H):
        raise SystemExit(
            "ERROR: output dimensions changed."
        )

    if check_frames != frame_count:
        raise SystemExit(
            "ERROR: output frame count changed."
        )

    check.close()

    # -----------------------------------------------------------------------
    # Preview
    # -----------------------------------------------------------------------

    preview = out_frames[0].convert(
        "RGB"
    )

    if preview.width > 900:
        preview = preview.resize(
            (
                900,
                int(
                    preview.height
                    * 900
                    / preview.width
                ),
            ),
            Image.Resampling.LANCZOS,
        )

    preview.save(
        PREVIEW
    )

    preview_size = os.path.getsize(
        PREVIEW
    )

    print(
        f"preview: {PREVIEW} "
        f"({preview_size / 1024:.1f} KB)"
    )

    total_time = (
        time.perf_counter()
        - started
    )

    print()
    print(
        f"completed in {total_time:.2f}s"
    )
    print()
    print(
        "Done."
    )


if __name__ == "__main__":
    main()
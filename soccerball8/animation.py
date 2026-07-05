"""Generates the intro animation frames: a soccer ball flies at the camera,
one white hexagon panel keeps zooming in until it fills the whole screen,
then the answer types itself on over the white.

Pure Pillow, no GPU/numpy required, so it stays cheap enough for a Pi Zero.
"""

import math
from typing import Iterator, List, Tuple

from PIL import Image, ImageDraw, ImageFont

PITCH_GREEN = (35, 110, 60)
BALL_WHITE = (245, 245, 245)
HEX_BLACK = (20, 20, 20)
TEXT_BLACK = (15, 15, 15)


def _ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


def _build_ball_texture(size: int = 900) -> Tuple[Image.Image, Tuple[float, float]]:
    """Draws a stylised 2D soccer ball: a white disc with black hexagon panels.
    Returns the texture and the pixel centre of the panel we'll zoom into."""
    img = Image.new("RGB", (size, size), PITCH_GREEN)
    draw = ImageDraw.Draw(img)
    center = (size / 2, size / 2)
    radius = size / 2 - 4

    draw.ellipse(
        [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius],
        fill=BALL_WHITE, outline=HEX_BLACK, width=max(2, size // 200),
    )

    hex_radius = radius * 0.30
    target_center = center
    ring_positions: List[Tuple[float, float]] = [(0.0, 0.0)]
    for i in range(6):
        angle = math.radians(60 * i)
        ring_positions.append((math.cos(angle) * hex_radius * 1.8, math.sin(angle) * hex_radius * 1.8))

    for i, (dx, dy) in enumerate(ring_positions):
        cx, cy = center[0] + dx, center[1] + dy
        draw.regular_polygon(
            (cx, cy, hex_radius), n_sides=6, rotation=30,
            outline=HEX_BLACK, width=max(2, size // 220),
        )
        if i == 3:  # pick one ring hexagon as the panel we'll zoom into
            target_center = (cx, cy)

    return img, target_center


def iter_ball_approach_frames(width: int, height: int, frames: int = 18) -> Iterator[Image.Image]:
    """Ball flies toward the camera from a small dot to filling the frame."""
    texture, _target = _build_ball_texture()

    for i in range(frames):
        t = _ease_in_out(i / max(frames - 1, 1))
        scale = 0.05 + t * 0.95  # grows from tiny to full-frame
        ball_size = max(4, int(min(width, height) * 1.4 * scale))
        ball = texture.resize((ball_size, ball_size), Image.LANCZOS)

        frame = Image.new("RGB", (width, height), PITCH_GREEN)
        px = width // 2 - ball_size // 2
        py = height // 2 - ball_size // 2
        frame.paste(ball, (px, py))
        yield frame


def iter_hexagon_zoom_frames(width: int, height: int, frames: int = 14) -> Iterator[Image.Image]:
    """Keep zooming into a single hexagon panel until it whites out the screen."""
    texture, target = _build_ball_texture()
    tex_size = texture.size[0]
    tx, ty = target
    max_crop = tex_size * 0.9
    min_crop = tex_size * 0.02

    for i in range(frames):
        t = _ease_in_out(i / max(frames - 1, 1))
        crop_size = max(min_crop, max_crop * (1 - t))
        half = crop_size / 2
        left = max(0, min(tex_size - crop_size, tx - half))
        top = max(0, min(tex_size - crop_size, ty - half))
        box = (int(left), int(top), int(left + crop_size), int(top + crop_size))
        cropped = texture.crop(box).resize((width, height), Image.LANCZOS)
        yield cropped

    # Hold on a pure white frame so the cut to text is seamless.
    yield Image.new("RGB", (width, height), BALL_WHITE)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> List[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _render_text_frame(width: int, height: int, visible_text: str, font) -> Image.Image:
    frame = Image.new("RGB", (width, height), BALL_WHITE)
    draw = ImageDraw.Draw(frame)
    bbox = draw.multiline_textbbox((0, 0), visible_text or " ", font=font, spacing=8, align="center")
    text_h = bbox[3] - bbox[1]
    draw.multiline_text(
        (width / 2, (height - text_h) / 2), visible_text, font=font,
        fill=TEXT_BLACK, anchor="ma", align="center", spacing=8,
    )
    return frame


def iter_typewriter_frames(
    width: int, height: int, text: str, chars_per_frame: int = 1
) -> Iterator[Image.Image]:
    """Reveal `text` on a white background, a few characters at a time."""
    font_size = max(14, width // 10)
    font = _load_font(font_size)
    scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = _wrap_text(scratch, text, font, width - 24)
    full_text = "\n".join(lines)

    for i in range(1, len(full_text) + 1, chars_per_frame):
        yield _render_text_frame(width, height, full_text[:i], font)

    yield _render_text_frame(width, height, full_text, font)


def iter_full_sequence(width: int, height: int, answer_text: str) -> Iterator[Image.Image]:
    yield from iter_ball_approach_frames(width, height)
    yield from iter_hexagon_zoom_frames(width, height)
    yield from iter_typewriter_frames(width, height, answer_text)

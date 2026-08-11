from flask import Flask, request, Response
from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
import os

app = Flask(__name__)

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Set this in the container environment:
# PUBLIC_BASE_URL=https://homebox.atlee.io
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")


def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def to_int(value, default):
    try:
        return int(float(value))
    except Exception:
        return default


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def ellipsize_to_width(draw, text, font, max_width):
    text = (text or "").strip()
    if not text:
        return ""

    if text_size(draw, text, font)[0] <= max_width:
        return text

    ellipsis = "..."
    if text_size(draw, ellipsis, font)[0] > max_width:
        return ""

    trimmed = text
    while trimmed:
        candidate = trimmed.rstrip() + ellipsis
        if text_size(draw, candidate, font)[0] <= max_width:
            return candidate
        trimmed = trimmed[:-1]

    return ellipsis


def fit_font(draw, text, max_width, start_size, bold=False, min_size=18):
    path = FONT_BOLD if bold else FONT_REG
    size = start_size
    while size >= min_size:
        font = get_font(path, size)
        if text_size(draw, text, font)[0] <= max_width:
            return font
        size -= 2
    return get_font(path, min_size)


def basic_wrap_text(draw, text, font, max_width):
    text = (text or "").strip()
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    lines = []
    current = ""

    for word in words:
        test_line = word if not current else f"{current} {word}"

        if text_size(draw, test_line, font)[0] <= max_width:
            current = test_line
            continue

        if current:
            lines.append(current)
            current = ""

        # Handle extremely long single words
        if text_size(draw, word, font)[0] > max_width:
            lines.append(ellipsize_to_width(draw, word, font, max_width))
        else:
            current = word

    if current:
        lines.append(current)

    return lines


def wrap_text_max_lines(draw, text, font, max_width, max_lines):
    lines = basic_wrap_text(draw, text, font, max_width)

    if len(lines) <= max_lines:
        return lines

    kept = lines[: max_lines - 1]
    remaining = " ".join(lines[max_lines - 1 :])
    kept.append(ellipsize_to_width(draw, remaining, font, max_width))
    return kept


def fit_wrapped_text(draw, text, max_width, start_size, max_lines=2, bold=False, min_size=18):
    path = FONT_BOLD if bold else FONT_REG

    for size in range(start_size, min_size - 1, -2):
        font = get_font(path, size)
        lines = basic_wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return lines, font

    font = get_font(path, min_size)
    lines = wrap_text_max_lines(draw, text, font, max_width, max_lines)
    return lines, font


def fit_single_line_text(draw, text, max_width, start_size, bold=False, min_size=18):
    text = (text or "").strip()
    if not text:
        return "", get_font(FONT_BOLD if bold else FONT_REG, min_size)

    path = FONT_BOLD if bold else FONT_REG

    for size in range(start_size, min_size - 1, -2):
        font = get_font(path, size)
        if text_size(draw, text, font)[0] <= max_width:
            return text, font

    font = get_font(path, min_size)
    return ellipsize_to_width(draw, text, font, max_width), font


def normalize_qr_url(raw_url: str) -> str:
    raw_url = (raw_url or "").strip()

    if not raw_url:
        return raw_url

    if raw_url.startswith("http://") or raw_url.startswith("https://") or raw_url.startswith("mailto:"):
        return raw_url

    if raw_url.startswith("//"):
        if PUBLIC_BASE_URL.startswith("https://"):
            return "https:" + raw_url
        return "http:" + raw_url

    if PUBLIC_BASE_URL:
        if not raw_url.startswith("/"):
            raw_url = "/" + raw_url
        return PUBLIC_BASE_URL + raw_url

    return raw_url


def make_qr(data, size):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(data or "")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.Resampling.NEAREST)


def is_location(url):
    u = (url or "").lower()
    return "/location/" in u or "/locations/" in u


def should_suppress_secondary_text(text):
    cleaned = (text or "").strip().lower()
    generic_values = {
        "",
        "location",
        "homebox location",
        "item",
        "homebox item",
    }
    return cleaned in generic_values


def render_location_label(title, description, additional, qr_url):
    # 4x6 landscape at 300 DPI
    W, H = 1800, 1200
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    margin = 70
    gap = 60
    qr_size = 760

    qr = make_qr(qr_url, qr_size)
    qr_x = margin
    qr_y = (H - qr_size) // 2
    img.paste(qr, (qr_x, qr_y))

    right_x = qr_x + qr_size + gap
    right_w = W - right_x - margin

    title = (title or "Location").strip()

    secondary = ""
    if not should_suppress_secondary_text(additional):
        secondary = additional.strip()
    elif not should_suppress_secondary_text(description):
        secondary = description.strip()

    # Title: wrap up to 2 lines, shrink if needed
    title_lines, title_font = fit_wrapped_text(
        draw=draw,
        text=title,
        max_width=right_w,
        start_size=130,
        max_lines=2,
        bold=True,
        min_size=42,
    )

    # Secondary: also wrap up to 2 lines
    secondary_lines = []
    secondary_font = None
    if secondary:
        secondary_lines, secondary_font = fit_wrapped_text(
            draw=draw,
            text=secondary,
            max_width=right_w,
            start_size=58,
            max_lines=2,
            bold=False,
            min_size=24,
        )

    # More generous line spacing
    _, title_ref_h = text_size(draw, "Ag", title_font)
    title_line_gap = max(26, int(title_ref_h * 0.30)) if len(title_lines) > 1 else 0

    secondary_line_gap = 0
    if secondary_font and secondary_lines:
        _, secondary_ref_h = text_size(draw, "Ag", secondary_font)
        secondary_line_gap = max(10, int(secondary_ref_h * 0.22)) if len(secondary_lines) > 1 else 0

    between_blocks_gap = 42 if secondary_lines else 0

    title_line_metrics = [text_size(draw, line, title_font) for line in title_lines]
    title_block_h = sum(h for _, h in title_line_metrics) + (title_line_gap * (len(title_lines) - 1))

    secondary_block_h = 0
    secondary_line_metrics = []
    if secondary_lines and secondary_font:
        secondary_line_metrics = [text_size(draw, line, secondary_font) for line in secondary_lines]
        secondary_block_h = sum(h for _, h in secondary_line_metrics) + (
            secondary_line_gap * (len(secondary_lines) - 1)
        )

    block_h = title_block_h + between_blocks_gap + secondary_block_h
    block_top = qr_y + (qr_size - block_h) // 2

    y = block_top

    for i, line in enumerate(title_lines):
        lw, lh = text_size(draw, line, title_font)
        draw.text(
            (right_x + (right_w - lw) // 2, y),
            line,
            fill="black",
            font=title_font,
        )
        y += lh
        if i < len(title_lines) - 1:
            y += title_line_gap

    if secondary_lines and secondary_font:
        y += between_blocks_gap
        for i, line in enumerate(secondary_lines):
            lw, lh = text_size(draw, line, secondary_font)
            draw.text(
                (right_x + (right_w - lw) // 2, y),
                line,
                fill="black",
                font=secondary_font,
            )
            y += lh
            if i < len(secondary_lines) - 1:
                y += secondary_line_gap

    return img


def render_item_label(title, description, additional, qr_url, width, height):
    W = max(width, 320)
    H = max(height, 180)
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    margin = max(8, int(H * 0.05))
    gap = max(8, int(H * 0.04))
    qr_size = min(H - (margin * 2), int(W * 0.32))

    qr = make_qr(qr_url, qr_size)
    qr_x = margin
    qr_y = (H - qr_size) // 2
    img.paste(qr, (qr_x, qr_y))

    text_x = qr_x + qr_size + gap
    text_w = W - text_x - margin

    title = (title or "Item").strip()

    body_lines = []
    if description and not should_suppress_secondary_text(description):
        body_lines.append(description.strip())
    if additional and not should_suppress_secondary_text(additional):
        body_lines.append(additional.strip())

    title_text, title_font = fit_single_line_text(
        draw=draw,
        text=title,
        max_width=text_w,
        start_size=int(H * 0.18),
        bold=True,
        min_size=16,
    )
    body_font = get_font(FONT_REG, max(14, int(H * 0.11)))

    tw, th = text_size(draw, title_text, title_font)
    total_h = th

    line_sizes = []
    for line in body_lines[:2]:
        fitted = ellipsize_to_width(draw, line, body_font, text_w)
        lw, lh = text_size(draw, fitted, body_font)
        line_sizes.append((fitted, lw, lh))
        total_h += gap + lh

    y = (H - total_h) // 2
    draw.text((text_x, y), title_text, fill="black", font=title_font)
    y += th

    for line, lw, lh in line_sizes:
        y += gap
        draw.text((text_x, y), line, fill="black", font=body_font)
        y += lh

    return img


@app.get("/")
def generate():
    raw_url = request.args.get("URL", "")
    qr_url = normalize_qr_url(raw_url)

    title = request.args.get("TitleText", "")
    description = request.args.get("DescriptionText", "")
    additional = request.args.get("AdditionalInformation", "")

    width = to_int(request.args.get("Width", "696"), 696)
    height = to_int(request.args.get("Height", "200"), 200)

    if is_location(qr_url):
        img = render_location_label(title, description, additional, qr_url)
    else:
        img = render_item_label(title, description, additional, qr_url, width, height)

    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(300, 300))
    return Response(buf.getvalue(), mimetype="image/png")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8787"))
    app.run(host="0.0.0.0", port=port)

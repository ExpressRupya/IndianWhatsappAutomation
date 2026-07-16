import logging
import requests
from io import BytesIO
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

TEMP_DIR = Path(__file__).resolve().parent.parent / "temp_images"
TEMP_DIR.mkdir(exist_ok=True)

BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "express_logo.png"

CARD_W, CARD_H = 800, 600
_OG_CACHE = {}
_LOGO_IMG = None

_FONT_CACHE = {}


def _get_logo():
    global _LOGO_IMG
    if _LOGO_IMG is not None:
        return _LOGO_IMG
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        w, h = logo.size
        target_w = 160
        target_h = int(h * target_w / w)
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        _LOGO_IMG = logo
        return logo
    except Exception as e:
        logger.warning(f"Could not load logo: {e}")
        _LOGO_IMG = False
        return None

def _get_font(size, bold=False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = []
    if bold:
        candidates.extend([
            "C:/Windows/Fonts/seguisb.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/consolab.ttf",
        ])
    candidates.extend([
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/consola.ttf",
    ])
    for path in candidates:
        p = Path(path)
        if p.exists():
            try:
                font = ImageFont.truetype(str(p), size)
                _FONT_CACHE[key] = font
                return font
            except Exception:
                continue
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


_COLORS = {
    "bg": (15, 23, 42),
    "bg_card": (30, 41, 59),
    "accent_blue": (37, 99, 235),
    "accent_green": (34, 197, 94),
    "accent_amber": (245, 158, 11),
    "accent_purple": (139, 92, 246),
    "text_white": (248, 250, 252),
    "text_gray": (148, 163, 184),
    "text_muted": (100, 116, 139),
    "border": (51, 65, 85),
}


def _category_color(category):
    return _COLORS["accent_green"] if category == "land" else _COLORS["accent_blue"]


def _truncate_text(text, font, max_width, draw):
    if not text:
        return text
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return text
    while text:
        test = text[:-1]
        bbox = draw.textbbox((0, 0), test + "...", font=font)
        if bbox[2] - bbox[0] <= max_width:
            return test + "..."
        text = test
    return ""


def _wrap_text(text, font, max_width, draw, max_lines=4):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) >= max_lines and len(words) > 1:
        last = lines[-1]
        if len(last) > 3:
            lines[-1] = last[:-1] + "..."
    return lines


def fetch_og_image(article_url):
    if article_url in _OG_CACHE:
        return _OG_CACHE[article_url]
    try:
        resp = requests.get(
            article_url, timeout=12,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        for selector in [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]',
            'meta[property="og:image:secure_url"]',
        ]:
            meta = soup.select_one(selector)
            if meta and meta.get("content"):
                img_url = meta["content"]
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                if not img_url.startswith("http"):
                    continue
                try:
                    img_resp = requests.get(img_url, timeout=10)
                    img_resp.raise_for_status()
                    data = img_resp.content
                    if len(data) > 1024:
                        _OG_CACHE[article_url] = data
                        return data
                except Exception:
                    continue
    except Exception:
        pass
    _OG_CACHE[article_url] = None
    return None


def _overlay_on_bg(img_data, article):
    img = Image.open(BytesIO(img_data)).convert("RGB")
    img = ImageOps.fit(img, (CARD_W, CARD_H), Image.LANCZOS)
    overlay = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for y in range(CARD_H // 2, CARD_H):
        alpha = int(180 * (y - CARD_H // 2) / (CARD_H // 2))
        draw.rectangle([(0, y), (CARD_W, y)], fill=(0, 0, 0, min(alpha, 200)))

    extra = ImageDraw.Draw(overlay)
    extra.rectangle([(0, CARD_H - 120), (CARD_W, CARD_H)], fill=(0, 0, 0, 200))

    blended = Image.alpha_composite(overlay, Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0)))
    img.paste(Image.new("RGB", (CARD_W, CARD_H), (0, 0, 0)), (0, 0), blended)
    img = Image.blend(img, Image.new("RGB", (CARD_W, CARD_H), (0, 0, 0)), 0.15)

    draw = ImageDraw.Draw(img)
    _draw_card_overlay(draw, article, img_for_paste=img)
    return img


def _draw_card_overlay(draw, article, img_for_paste=None):
    title = article.get("title", "Data Centre News")
    company = article.get("company_matched", "Industry News")
    category = article.get("category", "project")
    source = article.get("source", "")
    matched_keywords = article.get("matched_keywords", [])

    kw_text = "; ".join(matched_keywords[:3]) if matched_keywords else ""

    cat_bg = _category_color(category)
    cat_label = category.upper()

    title_font = _get_font(34, bold=True)
    company_font = _get_font(22, bold=True)
    body_font = _get_font(18)
    small_font = _get_font(15)
    badge_font = _get_font(16, bold=True)

    margin = 30

    logo = _get_logo()
    logo_y = margin
    if logo and img_for_paste is not None:
        img_for_paste.paste(logo, (margin, logo_y), logo)
        logo_right = margin + logo.width + 10
    else:
        logo_font = _get_font(14, bold=True)
        draw.text((margin, margin + 4), "Express Rupya", fill=_COLORS["text_gray"], font=logo_font)
        logo_right = margin + 120

    category_badge_size = draw.textbbox((0, 0), cat_label, font=badge_font)
    badge_w = category_badge_size[2] - category_badge_size[0] + 20
    badge_h = category_badge_size[3] - category_badge_size[1] + 10
    badge_x = CARD_W - margin - badge_w
    badge_y = margin
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=6, fill=cat_bg
    )
    draw.text(
        (badge_x + 10, badge_y + 5),
        cat_label, fill=_COLORS["text_white"], font=badge_font
    )

    company_y = margin + (logo.height + 10 if logo else 40)
    company_label = _truncate_text(company, company_font, CARD_W - 2 * margin, draw)
    draw.text((margin, company_y), company_label, fill=_COLORS["accent_amber"], font=company_font)

    separator_y = company_y + 40
    draw.line([(margin, separator_y), (CARD_W - margin, separator_y)], fill=_COLORS["border"], width=1)

    title_y = separator_y + 20
    max_title_width = CARD_W - 2 * margin
    title_lines = _wrap_text(title, title_font, max_title_width, draw, max_lines=4)
    for i, line in enumerate(title_lines):
        draw.text((margin, title_y + i * 42), line, fill=_COLORS["text_white"], font=title_font)

    snippet = article.get("snippet", "")
    snippet_y = title_y + min(len(title_lines), 4) * 42 + 15
    if snippet and snippet_y < CARD_H - 80:
        snippet_lines = _wrap_text(snippet, body_font, CARD_W - 2 * margin, draw, max_lines=2)
        for i, line in enumerate(snippet_lines):
            draw.text((margin, snippet_y + i * 26), line, fill=_COLORS["text_gray"], font=body_font)

    footer_y = CARD_H - 40
    source_date = f"{source}  |  {datetime.now().strftime('%d %B %Y')}" if source else datetime.now().strftime('%d %B %Y')
    draw.text((margin, footer_y), source_date, fill=_COLORS["text_muted"], font=small_font)

    if kw_text:
        kw_font = _get_font(13)
        kw_x = margin
        kw_y = footer_y - 24
        draw.text((kw_x, kw_y), f"Keywords: {kw_text}", fill=_COLORS["text_muted"], font=kw_font)


def _generate_card(article):
    img = Image.new("RGB", (CARD_W, CARD_H), _COLORS["bg"])
    draw = ImageDraw.Draw(img)

    card_margin = 20
    card_rect = [card_margin, card_margin, CARD_W - card_margin, CARD_H - card_margin]
    draw.rounded_rectangle(card_rect, radius=16, fill=_COLORS["bg_card"])

    inner = ImageDraw.Draw(img)

    accent_line_y = card_margin + 50
    draw.rectangle(
        [card_margin + 30, accent_line_y, card_margin + 80, accent_line_y + 4],
        fill=_COLORS["accent_blue"]
    )

    class MiniDraw:
        def textbbox(self, xy, text, font=None):
            return inner.textbbox(xy, text, font=font)
        def text(self, xy, text, fill, font=None):
            inner.text(xy, text, fill=fill, font=font)
        def line(self, xy, fill=None, width=0):
            inner.line(xy, fill=fill, width=width)
        def rounded_rectangle(self, xy, radius=0, fill=None):
            inner.rounded_rectangle(xy, radius=radius, fill=fill)
        def rectangle(self, xy, fill=None):
            inner.rectangle(xy, fill=fill)

    inner_draw = MiniDraw()

    _draw_card_overlay(
        inner_draw,
        {**article, "title": article.get("title", ""), "snippet": article.get("snippet", "")},
        img_for_paste=img,
    )

    return img


def generate_article_card(article, index=0):
    og_data = fetch_og_image(article.get("link", ""))
    if og_data:
        try:
            img = _overlay_on_bg(og_data, article)
            logger.info(f"Using OG image for article {index}: {article.get('title', '')[:50]}")
        except Exception as e:
            logger.warning(f"OG overlay failed for article {index}, fallback to generated card: {e}")
            img = _generate_card(article)
    else:
        logger.info(f"No OG image found for article {index}, generating card")
        img = _generate_card(article)

    filepath = TEMP_DIR / f"article_{index}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    img.save(filepath, "PNG")
    logger.info(f"Image saved: {filepath}")
    return str(filepath)


def cleanup_temp_images():
    count = 0
    for f in TEMP_DIR.glob("article_*.png"):
        try:
            f.unlink()
            count += 1
        except Exception:
            pass
    if count:
        logger.info(f"Cleaned up {count} temp images")

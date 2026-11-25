from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

from .models import GlobalSettings, Product
from .pricing import compute_prices

COLS = 3

MARGIN = 10 * mm
GUTTER = 4 * mm
BORDER_GAP = 1.5 * mm  # gap between outer and inner border (double border look)
PAD_V = 10 * mm  # vertical padding above/below text block (1 cm)
PAD_H = 6 * mm

FONT_NAME_BOLD = "Helvetica-Bold"
FONT_NAME_REGULAR = "Helvetica"


TC_FONT_SIZE = 6.5
TC_OFFSET = 2.5 * mm  # distance from inner border to TC text baseline


def fmt_ars(value: int) -> str:
    return f"${value:,.0f}".replace(",", ".")


def fmt_rate(value: float) -> str:
    """Argentine format: thousands '.', decimals ',' (decimals only if non-zero)."""
    if abs(value - round(value)) < 0.005:
        return f"${value:,.0f}".replace(",", ".")
    return f"${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def wrap_text(text: str, font: str, size: int, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        trial = f"{current} {w}".strip()
        if stringWidth(trial, font, size) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines or [""]


def _compute_block(product: Product, settings: GlobalSettings, inner_w: float) -> dict:
    contado, cuota, n_cuotas = compute_prices(product, settings)

    name = product.name.upper()
    name_size = 9
    while name_size > 6:
        name_lines = wrap_text(name, FONT_NAME_BOLD, name_size, inner_w)
        if len(name_lines) <= 3:
            break
        name_size -= 1
    name_lines = wrap_text(name, FONT_NAME_BOLD, name_size, inner_w)

    contado_text = f"Contado {fmt_ars(contado)}"
    contado_size = 26
    while contado_size > 14 and stringWidth(contado_text, FONT_NAME_BOLD, contado_size) > inner_w:
        contado_size -= 1

    if product.tipo_cobro_text:
        cuotas_lines = wrap_text(product.tipo_cobro_text, FONT_NAME_REGULAR, 13, inner_w)
    elif n_cuotas and n_cuotas > 0:
        cuotas_lines = [f"{n_cuotas} Cuotas de {fmt_ars(cuota)}"]
    else:
        cuotas_lines = []

    # distance from last name baseline to contado baseline: name descent + gap +
    # contado cap height, so large contado text never overlaps the name
    name_to_contado = name_size * 0.25 + 3 * mm + contado_size * 0.75

    block_h = len(name_lines) * name_size * 1.15
    block_h += name_to_contado - name_size * 1.15
    block_h += contado_size * 1.3
    block_h += len(cuotas_lines) * 13 * 1.2

    return {
        "contado": contado,
        "name_lines": name_lines,
        "name_size": name_size,
        "contado_size": contado_size,
        "cuotas_lines": cuotas_lines,
        "name_to_contado": name_to_contado,
        "block_h": block_h,
        "tc_text": f"TC USD {fmt_rate(settings.exchange_rate)}" if product.show_tc else None,
    }


def generate_pdf(products: list[Product], settings: GlobalSettings, output_path: str) -> None:
    checked = [p for p in products if p.checked and not p.deleted]
    page_w, page_h = A4
    cell_w = (page_w - 2 * MARGIN - (COLS - 1) * GUTTER) / COLS
    inner_w = cell_w - 2 * PAD_H
    top = page_h - MARGIN
    bottom = MARGIN

    c = canvas.Canvas(output_path, pagesize=A4)
    col_tops = [top] * COLS

    for product in checked:
        block = _compute_block(product, settings, inner_w)
        card_h = block["block_h"] + 2 * PAD_V

        for _ in range(max(1, product.copies)):
            col = max(range(COLS), key=lambda i: col_tops[i])
            card_y = col_tops[col] - card_h
            if card_y < bottom:
                c.showPage()
                col_tops = [top] * COLS
                col = 0
                card_y = col_tops[col] - card_h

            x = MARGIN + col * (cell_w + GUTTER)
            _draw_sign(c, block, x, card_y, cell_w, card_h)
            col_tops[col] = card_y - GUTTER

    c.save()


def _draw_sign(c: canvas.Canvas, block: dict, x: float, y: float, w: float, h: float) -> None:
    # outer border
    c.rect(x, y, w, h)
    # inner border (double border look)
    gap = BORDER_GAP
    c.rect(x + gap, y + gap, w - 2 * gap, h - 2 * gap)

    cx = x + w / 2
    name_size = block["name_size"]
    cur_y = y + h - PAD_V - name_size

    c.setFont(FONT_NAME_BOLD, name_size)
    for i, line in enumerate(block["name_lines"]):
        if i:
            cur_y -= name_size * 1.15
        c.drawCentredString(cx, cur_y, line)

    cur_y -= block["name_to_contado"]

    contado_size = block["contado_size"]
    c.setFont(FONT_NAME_BOLD, contado_size)
    c.drawCentredString(cx, cur_y, f"Contado {fmt_ars(block['contado'])}")
    cur_y -= contado_size * 1.3

    c.setFont(FONT_NAME_REGULAR, 13)
    for line in block["cuotas_lines"]:
        c.drawCentredString(cx, cur_y, line)
        cur_y -= 13 * 1.2

    # exchange rate reference, small at the bottom (fits inside bottom padding)
    if block["tc_text"]:
        c.setFont(FONT_NAME_REGULAR, TC_FONT_SIZE)
        c.drawCentredString(cx, y + gap + TC_OFFSET, block["tc_text"])

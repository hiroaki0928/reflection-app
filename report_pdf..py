from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


PAGE_W, PAGE_H = A4


def _register_japanese_font():
    candidates = [
        "HeiseiKakuGo-W5",
        "HeiseiMin-W3",
    ]

    for font_name in candidates:
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))
            return font_name
        except Exception:
            continue

    return "Helvetica"


def _safe_text(value):
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def _string_width(text, font_name, font_size):
    return pdfmetrics.stringWidth(str(text), font_name, font_size)


def _wrap_text(text, font_name, font_size, max_width):
    text = _safe_text(text)
    if text == "":
        return [""]

    paragraphs = text.split("\n")
    lines = []

    for para in paragraphs:
        if para.strip() == "":
            lines.append("")
            continue

        current = ""
        for ch in para:
            trial = current + ch
            if _string_width(trial, font_name, font_size) <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)

    return lines if lines else [""]


def _estimate_block_height(text, font_name, font_size, max_width, line_gap=1.16, extra=0):
    lines = _wrap_text(text, font_name, font_size, max_width)
    line_h = font_size * line_gap
    return len(lines) * line_h + extra


def _truncate_text_to_fit(text, font_name, font_size, max_width, max_lines):
    lines = _wrap_text(text, font_name, font_size, max_width)
    if len(lines) <= max_lines:
        return text

    trimmed = lines[:max_lines]
    if trimmed:
        last = trimmed[-1]
        if len(last) >= 2:
            last = last[:-1] + "…"
        else:
            last = last + "…"
        trimmed[-1] = last

    return "\n".join(trimmed)


def _get_size_presets():
    return [
        {"title": 16, "meta": 9.5, "section": 11, "lesson_title": 9.8, "body": 9.0},
        {"title": 15, "meta": 9.0, "section": 10.5, "lesson_title": 9.2, "body": 8.4},
        {"title": 14, "meta": 8.5, "section": 10.0, "lesson_title": 8.8, "body": 7.8},
        {"title": 13, "meta": 8.0, "section": 9.5, "lesson_title": 8.2, "body": 7.2},
        {"title": 12, "meta": 7.5, "section": 9.0, "lesson_title": 7.8, "body": 6.7},
    ]


def _estimate_total_height(report_data, font_name, sizes):
    margin_x = 36
    content_w = PAGE_W - margin_x * 2

    h = 0
    h += sizes["title"] * 1.8
    h += 42

    h += _estimate_block_height(report_data.get("unit_question", ""), font_name, sizes["body"], content_w - 14, extra=34)
    h += _estimate_block_height(report_data.get("first_text", ""), font_name, sizes["body"], content_w - 14, extra=34)

    lessons_df = report_data.get("lessons")
    h += sizes["section"] * 2.2

    if lessons_df is not None and len(lessons_df) > 0:
        for i, (_, row) in enumerate(lessons_df.iterrows(), start=1):
            h += sizes["lesson_title"] * 1.5
            h += _estimate_block_height("本時の問い：" + str(row.get("本時の問い", "")).strip(), font_name, sizes["body"], content_w - 14, extra=2)
            h += _estimate_block_height("それに対する答え：" + str(row.get("それに対する答え", "")).strip(), font_name, sizes["body"], content_w - 14, extra=8)
            h += 6
    else:
        h += sizes["body"] * 1.5

    h += _estimate_block_height(report_data.get("last_text", ""), font_name, sizes["body"], content_w - 14, extra=34)

    ai_text = f"単元全体の評価：{report_data.get('unit_star', '未評価')}\n{report_data.get('unit_comment', '')}"
    h += _estimate_block_height(ai_text, font_name, sizes["body"], content_w - 14, extra=34)

    h += 20
    return h


def build_unit_report_pdf(report_data):
    font_name = _register_japanese_font()
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    margin_x = 36
    margin_top = 34
    margin_bottom = 28
    content_w = PAGE_W - margin_x * 2
    available_h = PAGE_H - margin_top - margin_bottom

    chosen = _get_size_presets()[-1]
    for preset in _get_size_presets():
        if _estimate_total_height(report_data, font_name, preset) <= available_h:
            chosen = preset
            break

    title_size = chosen["title"]
    meta_size = chosen["meta"]
    section_size = chosen["section"]
    lesson_title_size = chosen["lesson_title"]
    body_size = chosen["body"]

    def draw_section_box(y_top, title, text, body_font_size):
        box_padding = 7
        text_width = content_w - box_padding * 2

        text = _safe_text(text) or "未入力"
        text_lines = _wrap_text(text, font_name, body_font_size, text_width)
        line_h = body_font_size * 1.16
        box_h = 24 + len(text_lines) * line_h + 8

        c.setLineWidth(0.8)
        c.rect(margin_x, y_top - box_h, content_w, box_h)

        c.setFont(font_name, section_size)
        c.drawString(margin_x + box_padding, y_top - 15, title)

        c.setFont(font_name, body_font_size)
        y = y_top - 30
        for line in text_lines:
            c.drawString(margin_x + box_padding, y, line)
            y -= line_h

        return y_top - box_h - 8

    c.setTitle("社会科 単元レポート")
    y = PAGE_H - margin_top

    c.setFont(font_name, title_size)
    c.drawCentredString(PAGE_W / 2, y, "社会科 単元レポート")
    y -= title_size * 1.7

    c.setLineWidth(0.9)
    c.rect(margin_x, y - 32, content_w, 32)

    c.setFont(font_name, meta_size)
    student_name = _safe_text(report_data.get("student_name", ""))
    student_id = _safe_text(report_data.get("student_id", ""))
    field_name = _safe_text(report_data.get("field_name", ""))
    unit_name = _safe_text(report_data.get("unit_name", ""))

    c.drawString(margin_x + 8, y - 12, f"名前：{student_name}")
    c.drawString(margin_x + content_w / 2, y - 12, f"番号：{student_id}")
    c.drawString(margin_x + 8, y - 24, f"分野：{field_name}")
    c.drawString(margin_x + content_w / 2, y - 24, f"大単元：{unit_name}")
    y -= 42

    y = draw_section_box(y, "大単元の問い", report_data.get("unit_question", ""), body_size)
    y = draw_section_box(y, "最初の考え", report_data.get("first_text", ""), body_size)

    # 下部に「最後の考え」「AIからのまとめ」を固定配置するため、必要スペースを先に確保
    ai_text = f"単元全体の評価：{report_data.get('unit_star', '未評価')}\n{report_data.get('unit_comment', '')}"
    final_text = _safe_text(report_data.get("last_text", "")) or "未入力"

    final_h = _estimate_block_height(final_text, font_name, body_size, content_w - 14, extra=34)
    ai_h = _estimate_block_height(ai_text, font_name, body_size, content_w - 14, extra=34)

    bottom_reserved = final_h + ai_h + 16
    lesson_bottom_y = margin_bottom + bottom_reserved

    # 各授業の振り返り枠
    lesson_top_y = y
    lesson_box_h = max(60, lesson_top_y - lesson_bottom_y)

    c.setLineWidth(0.8)
    c.rect(margin_x, lesson_bottom_y, content_w, lesson_box_h)

    c.setFont(font_name, section_size)
    c.drawString(margin_x + 7, lesson_top_y - 15, "各授業の振り返り")
    y = lesson_top_y - 28

    lessons_df = report_data.get("lessons")
    lesson_area_width = content_w - 14

    if lessons_df is None or len(lessons_df) == 0:
        c.setFont(font_name, body_size)
        c.drawString(margin_x + 7, y, "この大単元の振り返りはまだありません。")
    else:
        lesson_count = len(lessons_df)

        for i, (_, row) in enumerate(lessons_df.iterrows(), start=1):
            lesson_name = _safe_text(row.get("授業名", "")) or f"授業{i}"
            question_text = _safe_text(row.get("本時の問い", "")) or "未入力"
            answer_text = _safe_text(row.get("それに対する答え", "")) or "未入力"

            remaining_rows = lesson_count - i + 1
            now_remaining_area = max(40, y - lesson_bottom_y - 4)
            target_each = max(34, now_remaining_area / max(1, remaining_rows))

            header_h = lesson_title_size * 1.45
            body_line_h = body_size * 1.14
            usable_text_h = max(20, target_each - header_h - 8)

            q_max_lines = max(1, int(usable_text_h * 0.35 / body_line_h))
            a_max_lines = max(1, int(usable_text_h * 0.65 / body_line_h))

            q_text = _truncate_text_to_fit(
                "本時の問い：" + question_text,
                font_name,
                body_size,
                lesson_area_width,
                q_max_lines,
            )
            a_text = _truncate_text_to_fit(
                "それに対する答え：" + answer_text,
                font_name,
                body_size,
                lesson_area_width,
                a_max_lines,
            )

            c.setFont(font_name, lesson_title_size)
            c.drawString(margin_x + 7, y, f"{i}. {lesson_name}")
            y -= header_h

            c.setFont(font_name, body_size)

            q_lines = _wrap_text(q_text, font_name, body_size, lesson_area_width)
            for line in q_lines:
                c.drawString(margin_x + 12, y, line)
                y -= body_line_h

            a_lines = _wrap_text(a_text, font_name, body_size, lesson_area_width)
            for line in a_lines:
                c.drawString(margin_x + 12, y, line)
                y -= body_line_h

            if i < lesson_count and y > lesson_bottom_y + 8:
                c.line(margin_x + 7, y + 2, PAGE_W - margin_x - 7, y + 2)
                y -= 5

    # 下部固定
    final_y_top = lesson_bottom_y - 8
    final_y_after = draw_section_box(final_y_top, "最後の考え", report_data.get("last_text", ""), body_size)
    draw_section_box(final_y_after, "AIからのまとめ", ai_text, body_size)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
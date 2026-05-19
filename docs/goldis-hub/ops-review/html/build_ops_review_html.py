#!/usr/bin/env python3
"""
Build script for Goldis Hub Operational Review HTML packets.

Reads markdown source files from ops-review/ and generates
print-friendly RTL Persian HTML files for manager pre-read sessions.

Usage:
    python build_ops_review_html.py

Output:
    html/index.html
    html/session-01-pre-read.html
    html/session-02-pre-read.html
    html/session-03-pre-read.html
"""

import os
import re
import markdown

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OPS_DIR = os.path.dirname(BASE_DIR)
HTML_DIR = BASE_DIR

SESSIONS = [
    {
        "num": 1,
        "title": "فروش مشتری، Wallet و بازخرید آنلاین",
        "topic": "بررسی روال های خرید و فروش از دید مشتری نهایی",
        "duration": "۲.۵ ساعت",
        "participants": "مدیر فروش، مدیر مالی، مسئول پشتیبانی، مسئول انبار مرکزی، نماینده خزانه داری",
        "units": "فروش + مالی + پشتیبانی + انبار",
        "session_file": "session-01-customer-sales-wallet-buyback.md",
        "sheets": [
            ("01", "خرید شمش فیزیکی از سایت", "01-physical-bar-purchase-site.md"),
            ("02", "خرید طلای دیجیتال", "02-digital-gold-buy.md"),
            ("03", "فروش طلای دیجیتال", "03-digital-gold-sell.md"),
            ("04", "خرید فیزیکی با موجودی Wallet", "04-physical-purchase-from-wallet.md"),
            ("05", "بازخرید سفارش تحویل نشده (امانی)", "05-buyback-undelivered.md"),
        ],
    },
    {
        "num": 2,
        "title": "POS، مارکت پلیس، شارژ، برداشت و بازخرید حضوری",
        "topic": "بررسی روال های فروش حضوری، بازخرید حضوری، مارکت پلیس، شارژ و برداشت Wallet",
        "duration": "۲ ساعت",
        "participants": "مدیر شبکه نمایندگان، مسئول مارکت پلیس، مدیر مالی، مسئول تسویه و برداشت",
        "units": "نمایندگان + مالی + مارکت پلیس + پشتیبانی",
        "session_file": "session-02-pos-marketplace-topup-withdrawal.md",
        "sheets": [
            ("06", "بازخرید حضوری", "06-buyback-in-person.md"),
            ("07", "فروش حضوری POS (نماینده)", "07-pos-sale.md"),
            ("08", "فروش از طریق مارکتپلیس", "08-marketplace-sale.md"),
            ("09", "شارژ کیف پول ریالی", "09-rial-wallet-topup.md"),
            ("10", "برداشت ریال از کیف پول", "10-rial-withdrawal.md"),
        ],
    },
    {
        "num": 3,
        "title": "خزانه، تسویه بین شرکتی، انبار، تحویل و کمیسیون",
        "topic": "بررسی روال های پشت صحنه: مدیریت خزانه، تسویه، انبار، تحویل و کمیسیون نمایندگان",
        "duration": "۳ ساعت",
        "participants": "مدیر خزانه، مدیر حسابداری، مدیر انبار مرکزی، مسئول لجستیک، مدیر شبکه نمایندگان، مدیر عملیات",
        "units": "خزانه + حسابداری + انبار + لجستیک + نمایندگان",
        "session_file": "session-03-treasury-inventory-fulfillment-commission.md",
        "sheets": [
            ("11", "خرید طلای خام از بازار (Hedge Buy)", "11-hedge-buy-and-bulk-gold-intake.md"),
            ("12", "تسویه بین شرکتی", "12-inter-company-settlement.md"),
            ("13", "انتقال موجودی بین انبارها", "13-inventory-transfer.md"),
            ("14", "فولفیلمنت و تحویل کالا", "14-fulfillment-delivery.md"),
            ("15", "تسویه کمیسیون نمایندگان", "15-dealer-commission-settlement.md"),
        ],
    },
]

FA_NUM = "۰۱۲۳۴۵۶۷۸۹"


def to_fa_num(s):
    result = str(s)
    for i, c in enumerate("0123456789"):
        result = result.replace(c, FA_NUM[i])
    return result


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def fix_list_breaks(md_text):
    """Insert blank line between bold-titled lines and list items that follow.

    Markdown requires a blank line before a list. Session overview files have
    patterns like:
        **راهنمای ارائه (۵ دقیقه):**
        - item one
    Without a blank line, the parser treats them as one paragraph.
    """
    lines = md_text.split("\n")
    result = []
    for i, line in enumerate(lines):
        result.append(line)
        if i + 1 < len(lines):
            stripped = line.strip()
            next_stripped = lines[i + 1].strip()
            if (
                stripped.startswith("**") and stripped.endswith(":**")
                and (next_stripped.startswith("- ") or re.match(r"^\d+\.\s", next_stripped))
            ):
                result.append("")
            elif (
                stripped.startswith("**") and ":**" in stripped
                and (next_stripped.startswith("- ") or re.match(r"^\d+\.\s", next_stripped))
            ):
                result.append("")
    return "\n".join(result)


CODE_REPLACEMENTS = {
    "inter_company:settle": "مجوز تسویه بین شرکتی",
    "OPEN_ISSUES_LOG.md": "لاگ مسائل باز",
    "OPEN_ISSUES_LOG": "لاگ مسائل باز",
    "CHANGE_REQUESTS_LOG.md": "لاگ درخواست تغییرات",
    "CHANGE_REQUESTS_LOG": "لاگ درخواست تغییرات",
    "FLOW_REVIEW_STATUS.md": "جدول وضعیت روال ها",
    "FLOW_REVIEW_STATUS": "جدول وضعیت روال ها",
    "MEETING_MINUTES_TEMPLATE.md": "قالب صورتجلسه",
    "delivered_at": "تاریخ تحویل",
    "flows/": "مستندات فنی روال ها",
    "03-schema-index.md": "فهرست جداول دیتابیس",
    "04-api-index.md": "فهرست واسط های برنامه نویسی",
    "review-sheets": "برگه های بررسی",
    "ops-review/": "بسته بررسی عملیاتی",
}


def sanitize_for_managers(md_text):
    """Remove backtick code spans and replace known technical terms with
    business-friendly Persian equivalents before markdown conversion."""
    for code, replacement in CODE_REPLACEMENTS.items():
        md_text = md_text.replace(f"`{code}`", replacement)
    md_text = re.sub(r"`([^`]+)`", r"\1", md_text)
    return md_text


def strip_code_tags(html):
    """Remove any remaining <code> tags from generated HTML."""
    html = re.sub(r"<code>([^<]*)</code>", r"\1", html)
    return html


def md_to_html(md_text):
    md_text = re.sub(r"^---$", "", md_text, flags=re.MULTILINE)
    md_text = fix_list_breaks(md_text)
    md_text = sanitize_for_managers(md_text)
    html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code"],
        output_format="html5",
    )
    html = convert_checkboxes(html)
    html = strip_code_tags(html)
    return html


def convert_checkboxes(html):
    html = re.sub(
        r"<li>\s*\[ \]\s*",
        '<li class="checklist-item-li"><span class="checklist-box"></span> ',
        html,
    )
    html = re.sub(
        r"<li>\s*\[x\]\s*",
        '<li class="checklist-item-li"><span class="checklist-box" style="background:#b8860b;"></span> ',
        html,
        flags=re.IGNORECASE,
    )
    return html


def html_wrapper(title, body, session_num=None):
    footer_session = f"جلسه {to_fa_num(session_num)}" if session_num else ""
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="assets/print.css">
</head>
<body>
{body}
<div class="page-footer no-print" style="margin-top:3em; text-align:center; color:#aaa; font-size:0.85em;">
  Goldis Hub &mdash; Operational Review &mdash; {footer_session} &mdash; v1.0
</div>
</body>
</html>
"""


def build_cover_page(session):
    num_fa = to_fa_num(session["num"])
    return f"""<div class="cover-page">
  <div class="brand-title">Goldis Hub</div>
  <div class="brand-title" style="font-size:1.4em; margin-bottom:0.5em;">گلدیس هاب</div>
  <div class="sub-title">بسته پیش مطالعه جلسه بررسی عملیاتی</div>
  <div class="session-title">جلسه {num_fa}: {session["title"]}</div>

  <div class="cover-info">
    <div><span class="label">موضوع جلسه:</span> {session["topic"]}</div>
    <div><span class="label">مدت تقریبی:</span> {session["duration"]}</div>
    <div><span class="label">تاریخ جلسه:</span> ................</div>
    <div><span class="label">شرکت کنندگان:</span> ................</div>
    <div><span class="label">تهیه شده برای:</span> مدیران واحدهای درگیر در عملیات گلدیس هاب</div>
  </div>

  <div class="cover-instruction">
    لطفا قبل از جلسه، بخش های مربوط به واحد خودتان را مطالعه کنید و سوالات یا اصلاحات پیشنهادی را یادداشت کنید.
  </div>
</div>
<div class="page-break"></div>
"""


def build_session_overview(session):
    md_path = os.path.join(OPS_DIR, "sessions", session["session_file"])
    md_content = read_file(md_path)
    html_content = md_to_html(md_content)
    return f"""<div class="session-overview">
{html_content}
</div>
<div class="page-break"></div>
"""


def build_review_sheet(sheet_num, sheet_title, sheet_file, session_num):
    md_path = os.path.join(OPS_DIR, "review-sheets", sheet_file)
    md_content = read_file(md_path)
    html_content = md_to_html(md_content)
    num_fa = to_fa_num(sheet_num)
    session_fa = to_fa_num(session_num)

    return f"""<div class="review-sheet" id="flow-{sheet_num}">
{html_content}

<div class="decision-box">
  <div class="decision-label">تصمیم های پیشنهادی برای ثبت در جلسه</div>
</div>

<div class="notes-box">
  <div class="notes-label">یادداشت مدیر</div>
</div>

<div class="page-footer" style="font-size:0.8em; color:#aaa; border-top:1px solid #eee; padding-top:4px; margin-top:1em;">
  Goldis Hub &mdash; Operational Review &mdash; جلسه {session_fa} &mdash; روال {num_fa} &mdash; v1.0
</div>
</div>
"""


def build_final_checklist(session_num):
    num_fa = to_fa_num(session_num)
    items = [
        "همه روال های این جلسه بررسی شد",
        "مسئول هر مرحله مشخص شد",
        "تاییدهای دستی و اتومات مشخص شد",
        "مدارک لازم مشخص شد",
        "ریسک های مالی و عملیاتی بررسی شد",
        "مسائل باز در لاگ مسائل باز ثبت شد",
        "درخواست تغییرات در لاگ درخواست تغییرات ثبت شد",
        "وضعیت روال ها در جدول وضعیت روال ها بروزرسانی شد",
        "روال های تایید شده مشخص شدند",
        "روال های نیازمند اصلاح مشخص شدند",
    ]

    checklist_html = "\n".join(
        f'<div class="checklist-item"><span class="checklist-box"></span><span class="checklist-text">{item}</span></div>'
        for item in items
    )

    blank_areas = [
        "تصمیمات مهم جلسه",
        "مسائل باز",
        "درخواست تغییرات",
        "اقدام های بعدی",
    ]

    blanks_html = "\n".join(
        f"""<div class="blank-area">
  <div class="area-label">{area}</div>
</div>"""
        for area in blank_areas
    )

    return f"""<div class="final-checklist">
<h1>چک لیست نهایی جلسه {num_fa}</h1>

<div class="checklist-group">
{checklist_html}
</div>

<hr>

{blanks_html}

<div class="page-footer" style="font-size:0.8em; color:#aaa; border-top:1px solid #eee; padding-top:4px; margin-top:2em;">
  Goldis Hub &mdash; Operational Review &mdash; جلسه {num_fa} &mdash; چک لیست نهایی &mdash; v1.0
</div>
</div>
"""


def build_session_html(session):
    parts = []
    parts.append(build_cover_page(session))
    parts.append(build_session_overview(session))
    for sheet_num, sheet_title, sheet_file in session["sheets"]:
        parts.append(build_review_sheet(sheet_num, sheet_title, sheet_file, session["num"]))
    parts.append(build_final_checklist(session["num"]))

    body = "\n".join(parts)
    title = f"جلسه {to_fa_num(session['num'])}: {session['title']} — بررسی عملیاتی گلدیس هاب"
    return html_wrapper(title, body, session_num=session["num"])


def build_index_html():
    rows = ""
    cards = ""
    for s in SESSIONS:
        num_fa = to_fa_num(s["num"])
        flows = " / ".join(f"روال {to_fa_num(sh[0])}" for sh in s["sheets"])
        rows += f"""<tr>
  <td style="text-align:center; font-weight:700;">{num_fa}</td>
  <td>{s["title"]}</td>
  <td style="font-size:0.85em;">{flows}</td>
  <td style="font-size:0.9em;">{s["units"]}</td>
  <td style="font-size:0.85em;">{s["participants"]}</td>
  <td style="text-align:center;">{s["duration"]}</td>
</tr>
"""
        cards += f"""<div class="session-card">
  <h2>جلسه {num_fa}: {s["title"]}</h2>
  <p>{s["topic"]}</p>
  <p><strong>مدت:</strong> {s["duration"]} &nbsp;|&nbsp; <strong>واحدها:</strong> {s["units"]}</p>
  <p><strong>شرکت کنندگان پیشنهادی:</strong> {s["participants"]}</p>
  <a href="session-{s['num']:02d}-pre-read.html">باز کردن بسته پیش مطالعه</a>
</div>
"""

    body = f"""<div class="index-header">
  <h1>بسته پیش مطالعه جلسات بررسی عملیاتی</h1>
  <div style="font-size:1.6em; font-weight:800; color:#b8860b; margin-bottom:0.3em;">Goldis Hub — گلدیس هاب</div>
  <p>این بسته شامل ۳ جلسه بررسی عملیاتی برای ۱۵ روال اصلی سیستم گلدیس هاب است.<br>
  هر جلسه یک فایل HTML جداگانه دارد که قابل چاپ یا ذخیره به PDF است.</p>
</div>

<hr>

<h2>جلسات بررسی</h2>

{cards}

<hr>

<h2>خلاصه جلسات</h2>

<table>
<thead>
<tr>
  <th>جلسه</th>
  <th>موضوع</th>
  <th>روال ها</th>
  <th>واحدهای اصلی</th>
  <th>شرکت کنندگان پیشنهادی</th>
  <th>مدت</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>

<hr>

<div class="instructions-box">
  <h3>راهنمای استفاده</h3>
  <ol>
    <li>هر لینک جلسه را باز کنید</li>
    <li>از منوی مرورگر Print را انتخاب کنید (Ctrl+P یا Cmd+P)</li>
    <li>گزینه <strong>Save as PDF</strong> را انتخاب کنید</li>
    <li>تنظیمات پیشنهادی:
      <ul>
        <li><strong>کاغذ:</strong> A4</li>
        <li><strong>جهت:</strong> عمودی (Portrait)</li>
        <li><strong>حاشیه:</strong> پیش فرض یا سفارشی</li>
        <li><strong>مقیاس:</strong> ۹۰٪ تا ۱۰۰٪</li>
        <li><strong>Background graphics:</strong> فعال</li>
      </ul>
    </li>
  </ol>
</div>

<div class="page-footer" style="text-align:center; margin-top:2em; color:#aaa; font-size:0.85em;">
  Goldis Hub &mdash; Operational Review Package &mdash; v1.0
</div>
"""
    return html_wrapper("بسته پیش مطالعه جلسات بررسی عملیاتی — گلدیس هاب", body)


def main():
    print("Building Goldis Hub Operational Review HTML packets...")
    print(f"Source: {OPS_DIR}")
    print(f"Output: {HTML_DIR}")
    print()

    index_html = build_index_html()
    index_path = os.path.join(HTML_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print("  [OK] index.html")

    for session in SESSIONS:
        session_html = build_session_html(session)
        filename = f"session-{session['num']:02d}-pre-read.html"
        filepath = os.path.join(HTML_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(session_html)

        sheet_count = len(session["sheets"])
        print(f"  [OK] {filename} ({sheet_count} review sheets)")

    print()
    print("Done! All files generated successfully.")


if __name__ == "__main__":
    main()

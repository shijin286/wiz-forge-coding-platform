"""PDF export of a review (score, metrics, AI summary, findings, fixes and the source code)."""

from datetime import timezone

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from .analysis import SUPPORTED_LANGUAGES
from .analysis.base import SEVERITIES
from .models import Review

SEVERITY_RGB = {
    "critical": (225, 29, 72), "high": (234, 88, 12), "medium": (202, 138, 4),
    "low": (37, 99, 235), "info": (100, 116, 139),
}
BRAND = (5, 150, 105)
INK = (15, 23, 42)
MUTED = (100, 116, 139)
CODE_LINES_LIMIT = 400  # keep very large files from producing huge PDFs


def _t(text: str | None) -> str:
    """The built-in PDF fonts are Latin-1 only; replace anything else instead of failing."""
    replacements = {"→": "->", "–": "-", "—": "-", "‘": "'", "’": "'",
                    "“": '"', "”": '"', "…": "...", "•": "-", "\t": "    "}
    text = text or ""
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


class _ReportPDF(FPDF):
    def __init__(self, title: str):
        super().__init__(format="A4")
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(16, 16, 16)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, _t(f"WizForge AI  |  {self.report_title}"), align="L")
        self.cell(0, 6, f"Page {self.page_no()}/{{nb}}", align="R")

    def heading(self, text: str) -> None:
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*INK)
        self.cell(0, 8, _t(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(226, 232, 240)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def body(self, text: str, size: float = 10, color=INK, style: str = "") -> None:
        self.set_font("Helvetica", style, size)
        self.set_text_color(*color)
        self.multi_cell(0, 5, _t(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def build_report(review: Review) -> bytes:
    pdf = _ReportPDF(review.title)
    pdf.alias_nb_pages()
    pdf.add_page()

    # header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 5, "WIZFORGE AI  -  CODE REVIEW REPORT", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 9, _t(review.title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    created = review.created_at.replace(tzinfo=review.created_at.tzinfo or timezone.utc)
    pdf.body(f"{SUPPORTED_LANGUAGES.get(review.language, review.language)}  |  "
             f"{created.strftime('%d %b %Y, %H:%M UTC')}", size=9, color=MUTED)

    # score + metrics
    pdf.heading("Summary")
    m = review.metrics or {}
    counts = {s: sum(1 for f in review.findings if f.severity == s) for s in SEVERITIES}
    rows = [
        ("Quality score", f"{review.quality_score}/100  (grade {review.grade})"),
        ("Score after fixes", f"{review.fixed_score}/100  (grade {review.fixed_grade})"
         if review.fixed_score is not None else "-"),
        ("Lines of code", str(m.get("lines_of_code", "-"))),
        ("Functions", str(m.get("functions", "-"))),
        ("Average complexity", str(m.get("avg_complexity", "-"))),
        ("Findings", ", ".join(f"{n} {s}" for s, n in counts.items() if n) or "none"),
    ]
    for label, value in rows:
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(*MUTED)
        pdf.cell(48, 6, label)
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, _t(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if review.ai_status == "completed" and review.ai_summary:
        pdf.heading("AI summary")
        pdf.body(review.ai_summary)
        pdf.body("AI findings are potential issues, not guaranteed defects.", size=8, color=MUTED, style="I")

    # findings
    pdf.heading(f"Findings ({len(review.findings)})")
    if not review.findings:
        pdf.body("No issues found.", color=MUTED)
    ordered = sorted(review.findings, key=lambda f: (SEVERITIES.index(f.severity), f.line or 0))
    for f in ordered:
        if pdf.get_y() > pdf.h - 40:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*SEVERITY_RGB.get(f.severity, MUTED))
        pdf.cell(18, 5, f.severity.upper())
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "B", 10)
        source = f"AI, {f.confidence} confidence" if f.source == "ai" else f.rule_id
        location = f"line {f.line}" if f.line else "file"
        pdf.multi_cell(0, 5, _t(f"{f.title}   ({location}, {source})"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(pdf.l_margin + 18)
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(*INK)
        pdf.multi_cell(0, 4.5, _t(f.message), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if f.suggestion:
            pdf.set_x(pdf.l_margin + 18)
            pdf.set_text_color(*BRAND)
            pdf.multi_cell(0, 4.5, _t(f"Fix: {f.suggestion}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    if review.fixes_applied:
        pdf.heading("Automatic fixes")
        for fix in review.fixes_applied:
            where = f"line {fix['line']}: " if fix.get("line") else ""
            pdf.body(f"- {where}{fix['description']}", size=9)

    # source listing
    pdf.add_page()
    pdf.heading("Source code")
    lines = review.code.splitlines()
    pdf.set_font("Courier", size=7.5)
    width = len(str(len(lines)))
    for i, line in enumerate(lines[:CODE_LINES_LIMIT], start=1):
        flagged = any(f.line == i for f in review.findings)
        pdf.set_text_color(*(SEVERITY_RGB["critical"] if flagged else INK))
        pdf.multi_cell(0, 3.6, _t(f"{i:>{width}} | {line}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if len(lines) > CODE_LINES_LIMIT:
        pdf.body(f"... {len(lines) - CODE_LINES_LIMIT} more lines not shown", size=8, color=MUTED)

    return bytes(pdf.output())

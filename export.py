"""PDF report generation using fpdf2."""

from __future__ import annotations

from datetime import date
from fpdf import FPDF

from profile import (
    StudentProfile,
    GradeDetailLog,
    ActivityLog,
    GamificationProfile,
    TopicProgressStore,
    MisconceptionLog,
    MISCONCEPTION_PATTERNS,
)
from subject_config import get_syllabus_topics


def _safe(text: str) -> str:
    """Replace unicode chars that latin-1 Helvetica can't handle."""
    return (
        text
        .replace("\u2014", "-")   # em-dash
        .replace("\u2013", "-")   # en-dash
        .replace("\u2018", "'")   # left single quote
        .replace("\u2019", "'")   # right single quote
        .replace("\u201c", '"')   # left double quote
        .replace("\u201d", '"')   # right double quote
        .replace("\u2026", "...")  # ellipsis
        .replace("\u2022", "-")   # bullet
    )


def generate_pdf_report(
    profile: StudentProfile,
    grade_log: GradeDetailLog,
    activity_log: ActivityLog,
    gamification: GamificationProfile,
    topic_progress: TopicProgressStore,
    misconception_log: MisconceptionLog,
) -> bytes:
    """Generate a multi-page PDF progress report and return as bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    _render_cover(pdf, profile, grade_log, gamification, activity_log)
    _render_subjects(pdf, profile, grade_log, topic_progress)
    _render_analysis(pdf, grade_log, profile)
    _render_recommendations(pdf, profile, grade_log, misconception_log, topic_progress)

    return pdf.output()


# ── Helpers ────────────────────────────────────────────────────


def _header(pdf: FPDF, title: str) -> None:
    """Add a page with a header bar."""
    pdf.add_page()
    pdf.set_fill_color(79, 70, 229)
    pdf.rect(0, 0, 210, 12, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(10, 2)
    pdf.cell(0, 8, _safe(title), align="L")
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(18)


def _section_title(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def _body(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, _safe(text))
    pdf.ln(2)


def _cell(pdf: FPDF, w, h, text, **kwargs) -> None:
    """Safe cell that strips non-latin-1 chars."""
    pdf.cell(w, h, _safe(str(text)), **kwargs)


# ── Page 1: Cover & Summary ────────────────────────────────────


def _render_cover(
    pdf: FPDF,
    profile: StudentProfile,
    grade_log: GradeDetailLog,
    gam: GamificationProfile,
    activity_log: ActivityLog,
) -> None:
    pdf.add_page()

    # Title block
    pdf.set_fill_color(79, 70, 229)
    pdf.rect(0, 0, 210, 55, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(15, 12)
    pdf.cell(0, 10, "IB Study Companion")
    pdf.set_font("Helvetica", "", 14)
    pdf.set_xy(15, 25)
    pdf.cell(0, 8, "Progress Report")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(15, 38)
    pdf.cell(0, 6, f"Generated {date.today().strftime('%d %B %Y')}")
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(65)

    # Student info
    _section_title(pdf, "Student Information")
    pdf.set_font("Helvetica", "", 10)
    countdown = profile.exam_countdown()
    predicted_total = profile.compute_predicted_total(grade_log)

    info_lines = [
        f"Name: {profile.name}",
        f"Exam Session: {profile.exam_session}",
        f"Days Remaining: {countdown['days']}",
        f"Target Total: {profile.target_total_points}/45 points",
        f"Predicted Total: {predicted_total}/45 points",
    ]
    for line in info_lines:
        pdf.cell(0, 6, _safe(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Gamification summary
    _section_title(pdf, "Study Progress")
    gam_lines = [
        f"Level: {gam.level}  |  Total XP: {gam.total_xp}",
        f"Current Streak: {gam.current_streak} days  |  Longest: {gam.longest_streak} days",
        f"Questions Answered: {gam.total_questions_answered}",
        f"Flashcards Reviewed: {gam.total_flashcards_reviewed}",
        f"Badges Earned: {len(gam.badges)}",
    ]
    pdf.set_font("Helvetica", "", 10)
    for line in gam_lines:
        pdf.cell(0, 6, _safe(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Activity summary
    _section_title(pdf, "Study Consistency")
    days_30 = activity_log.days_active_last_n(30)
    days_7 = activity_log.days_active_last_n(7)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Days Active (last 30): {days_30}/30", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Days Active (last 7): {days_7}/7", new_x="LMARGIN", new_y="NEXT")


# ── Page 2: Subject Breakdown ──────────────────────────────────


def _render_subjects(
    pdf: FPDF,
    profile: StudentProfile,
    grade_log: GradeDetailLog,
    tp_store: TopicProgressStore,
) -> None:
    _header(pdf, "Subject Breakdown")

    gaps = profile.compute_gaps(grade_log)
    subject_stats = grade_log.subject_stats()

    # Table header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(241, 245, 249)
    col_w = [50, 15, 18, 22, 15, 25, 25, 20]
    headers = ["Subject", "Level", "Target", "Predicted", "Gap", "Status", "Coverage", "Trend"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for g in gaps:
        entries = grade_log.by_subject(g["subject"])

        # Trend
        trend = "-"
        if len(entries) >= 6:
            half = len(entries) // 2
            first_avg = sum(e.grade for e in entries[:half]) / half
            second_avg = sum(e.grade for e in entries[half:]) / (len(entries) - half)
            if second_avg - first_avg > 0.5:
                trend = "Up"
            elif first_avg - second_avg > 0.5:
                trend = "Down"
            else:
                trend = "Stable"

        # Coverage
        topics = get_syllabus_topics(g["subject"])
        coverage_str = "-"
        if topics:
            tp = tp_store.get(g["subject"])
            coverage_str = f"{tp.overall_coverage(topics):.0f}%"

        row = [
            g["subject"][:20],
            g["level"],
            str(g["target"]),
            str(g["predicted"]) if g["predicted"] else "-",
            f"{g['gap']:+d}" if g["status"] != "no_data" else "-",
            g["status"].replace("_", " ").title(),
            coverage_str,
            trend,
        ]
        for i, val in enumerate(row):
            pdf.cell(col_w[i], 6, _safe(val), border=1, align="C")
        pdf.ln()

    pdf.ln(6)

    # Per-subject grade history
    for s in profile.subjects:
        entries = grade_log.by_subject(s.name)
        if not entries:
            continue
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, f"{s.name} ({s.level}) - Last 10 Grades", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        recent = entries[-10:]
        grades_str = ", ".join(str(e.grade) for e in recent)
        avg = sum(e.grade for e in recent) / len(recent)
        pdf.cell(0, 5, f"Grades: {grades_str}  (avg: {avg:.1f})", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)


# ── Page 3: Performance Analysis ──────────────────────────────


def _render_analysis(
    pdf: FPDF,
    grade_log: GradeDetailLog,
    profile: StudentProfile,
) -> None:
    _header(pdf, "Performance Analysis")

    ct_stats = grade_log.command_term_stats()

    if ct_stats:
        _section_title(pdf, "Command Term Performance")

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(241, 245, 249)
        ct_col_w = [50, 30, 20, 30, 30]
        ct_headers = ["Command Term", "Avg %", "Count", "Avg Grade", "Status"]
        for i, h in enumerate(ct_headers):
            pdf.cell(ct_col_w[i], 7, h, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        sorted_cts = sorted(ct_stats.items(), key=lambda x: x[1]["avg_percentage"])
        for ct, stats in sorted_cts:
            status = "Strong" if stats["avg_percentage"] >= 70 else "Needs Work" if stats["avg_percentage"] < 55 else "Adequate"
            row = [
                ct[:22],
                f"{stats['avg_percentage']:.0f}%",
                str(stats["count"]),
                f"{stats['avg_grade']:.1f}",
                status,
            ]
            for i, val in enumerate(row):
                pdf.cell(ct_col_w[i], 6, _safe(val), border=1, align="C")
            pdf.ln()

        pdf.ln(4)

    # Weakest command terms
    weak_cts = [ct for ct, s in ct_stats.items() if s["avg_percentage"] < 60 and s["count"] >= 2]
    if weak_cts:
        _section_title(pdf, "Weakest Command Terms")
        pdf.set_font("Helvetica", "", 10)
        for ct in weak_cts[:3]:
            s = ct_stats[ct]
            pdf.cell(0, 6, f"  - {ct}: {s['avg_percentage']:.0f}% avg across {s['count']} attempts", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Overall stats
    entries = grade_log.entries
    if entries:
        _section_title(pdf, "Overall Statistics")
        pdf.set_font("Helvetica", "", 10)
        total = len(entries)
        avg_pct = sum(e.percentage for e in entries) / total
        avg_grade = sum(e.grade for e in entries) / total
        high_grade = max(e.grade for e in entries)
        pdf.cell(0, 6, f"Total Questions Graded: {total}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Average Percentage: {avg_pct:.0f}%", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Average Grade: {avg_grade:.1f}/7", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Highest Grade Achieved: {high_grade}/7", new_x="LMARGIN", new_y="NEXT")


# ── Page 4: Recommendations ──────────────────────────────────


def _render_recommendations(
    pdf: FPDF,
    profile: StudentProfile,
    grade_log: GradeDetailLog,
    misconception_log: MisconceptionLog,
    topic_progress=None,
) -> None:
    _header(pdf, "Recommendations & Weak Areas")

    # Misconceptions
    misconceptions = misconception_log.active_misconceptions()
    if misconceptions:
        _section_title(pdf, "Recurring Misconception Patterns")
        pdf.set_font("Helvetica", "", 10)
        for m in misconceptions[:5]:
            pattern_def = MISCONCEPTION_PATTERNS.get(m["pattern_id"], {})
            name = pattern_def.get("name", m["pattern_id"])
            desc = pattern_def.get("description", "")
            pdf.cell(0, 6, _safe(f"  - {name} (seen {m['count']}x in {m['subject']})"), new_x="LMARGIN", new_y="NEXT")
            if desc:
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(0, 5, _safe(f"    {desc}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
        pdf.ln(4)

    # Gap-based recommendations
    gaps = profile.compute_gaps(grade_log)
    behind = [g for g in gaps if g["status"] == "behind"]
    if behind:
        _section_title(pdf, "Priority Subjects")
        pdf.set_font("Helvetica", "", 10)
        for g in behind:
            pdf.cell(
                0, 6,
                _safe(f"  - {g['subject']} ({g['level']}): predicted {g['predicted']}, target {g['target']} ({g['gap']:+d} gap)"),
                new_x="LMARGIN", new_y="NEXT",
            )
        pdf.ln(4)

    # Study allocation suggestion
    _section_title(pdf, "Suggested Study Allocation")
    pdf.set_font("Helvetica", "", 10)
    total_gap = sum(max(g["gap"], 0) for g in gaps if g["status"] != "no_data")
    for g in gaps:
        if g["status"] == "no_data":
            pct = round(100 / len(gaps)) if gaps else 0
        elif total_gap > 0 and g["gap"] > 0:
            pct = round((g["gap"] / total_gap) * 100)
        else:
            pct = round(100 / len(gaps)) if gaps else 0
        pdf.cell(0, 6, _safe(f"  - {g['subject']}: ~{pct}% of study time"), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # Syllabus coverage
    _section_title(pdf, "Syllabus Coverage Summary")
    pdf.set_font("Helvetica", "", 10)
    for s in profile.subjects:
        topics = get_syllabus_topics(s.name)
        if not topics or not topic_progress:
            continue
        tp_subj = topic_progress.get(s.name)
        overall = tp_subj.overall_coverage(topics)
        pdf.cell(0, 6, _safe(f"  {s.name}: {overall:.0f}% covered"), new_x="LMARGIN", new_y="NEXT")

        # List uncovered topics
        uncovered = []
        for t in topics:
            if not tp_subj.topics.get(t.id):
                uncovered.append(t.name)
        if uncovered:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(150, 150, 150)
            uncovered_str = ", ".join(uncovered[:5])
            if len(uncovered) > 5:
                uncovered_str += f" (+{len(uncovered) - 5} more)"
            pdf.cell(0, 5, _safe(f"    Not yet covered: {uncovered_str}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 10)
        pdf.ln(1)

    # Footer
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "Generated by IB Study Companion - AI-powered exam preparation platform", align="C")
    pdf.set_text_color(0, 0, 0)

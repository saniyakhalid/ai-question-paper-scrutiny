import os
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class PDFReportExporter:
    @staticmethod
    def create_pdf_report(report_data: dict) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=15,
            leading=18,
            textColor=colors.HexColor('#1E3A8A'),
            alignment=1,
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#475569'),
            alignment=1,
            spaceAfter=10
        )
        h2_style = ParagraphStyle(
            'H2Heading',
            parent=styles['Heading2'],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#334155')
        )
        th_style = ParagraphStyle(
            'TH',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            fontName='Helvetica-Bold'
        )

        story = []

        # Header
        story.append(Paragraph("AUTONOMOUS ENGINEERING COLLEGE &bull; EXAMINATION CELL", title_style))
        story.append(Paragraph("AI-Based Question Paper Scrutiny & Moderation Decision Support Report", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=12))

        # Paper Metadata Table
        score_val = report_data.get('overall_score')
        score_display = f"{score_val:.1f} / 100" if isinstance(score_val, (int, float)) else "N/A"
        status_val = report_data.get('status', 'PENDING_REVIEW')

        paper_info = [
            [
                Paragraph("<b>Paper Title:</b>", body_style), Paragraph(str(report_data.get("paper_title") or f"Paper #{report_data.get('paper_id')}"), body_style),
                Paragraph("<b>Subject:</b>", body_style), Paragraph(f"{report_data.get('subject_code','')} - {report_data.get('subject_name','')}", body_style)
            ],
            [
                Paragraph("<b>Academic Year:</b>", body_style), Paragraph(str(report_data.get("academic_year", "2025-2026")), body_style),
                Paragraph("<b>Examination Type:</b>", body_style), Paragraph(str(report_data.get("exam_type", "Regular")), body_style)
            ],
            [
                Paragraph("<b>Scrutiny Score:</b>", body_style), Paragraph(f"<b><font color='#1E3A8A'>{score_display}</font></b>", body_style),
                Paragraph("<b>Paper Status:</b>", body_style), Paragraph(f"<b>{status_val}</b>", body_style)
            ]
        ]
        info_table = Table(paper_info, colWidths=[85, 185, 85, 185])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 10))

        # Rule Validation Section
        story.append(Paragraph("1. Institutional Examination Rule Verification", h2_style))
        rule_rows = [[
            Paragraph("Category", th_style),
            Paragraph("Rule Name", th_style),
            Paragraph("Expected", th_style),
            Paragraph("Actual", th_style),
            Paragraph("Status", th_style)
        ]]
        for r in report_data.get("rule_results", []):
            st = str(r.get("status", "PASS")).upper()
            st_color = '#059669' if st == 'PASS' else ('#D97706' if st == 'WARNING' else '#DC2626')
            rule_rows.append([
                Paragraph(str(r.get("category", "")), body_style),
                Paragraph(str(r.get("rule_name", "")), body_style),
                Paragraph(str(r.get("expected_value", "")), body_style),
                Paragraph(str(r.get("actual_value", "")), body_style),
                Paragraph(f"<b><font color='{st_color}'>{st}</font></b>", body_style)
            ])
        rule_table = Table(rule_rows, colWidths=[70, 160, 110, 130, 70])
        rule_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(rule_table)
        story.append(Spacer(1, 10))

        # Question Breakdown Section
        story.append(Paragraph("2. Question Breakdown, Cognitive Level & Syllabus Mapping", h2_style))
        q_rows = [[
            Paragraph("Q.No", th_style),
            Paragraph("Marks", th_style),
            Paragraph("Bloom", th_style),
            Paragraph("CO", th_style),
            Paragraph("Unit / Topic", th_style),
            Paragraph("Statement Excerpt", th_style)
        ]]
        for q in report_data.get("questions_breakdown", []):
            marks_str = str(q.get("marks")) if q.get("marks") is not None else "—"
            q_rows.append([
                Paragraph(f"<b>{q.get('q_num', '')}</b>", body_style),
                Paragraph(marks_str, body_style),
                Paragraph(str(q.get("bloom", "—")), body_style),
                Paragraph(str(q.get("co", "—")), body_style),
                Paragraph(str(q.get("unit_topic", "—")), body_style),
                Paragraph(str(q.get("question_text", ""))[:90], body_style),
            ])
        q_table = Table(q_rows, colWidths=[50, 40, 60, 50, 140, 200])
        q_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(q_table)
        story.append(Spacer(1, 12))

        # Final Moderator Decision & Feedback
        story.append(Paragraph("3. Moderator Review, Quality Feedback & Decision", h2_style))
        decision_val = report_data.get('decision', 'PENDING REVIEW')
        dec_color = '#059669' if 'APPROV' in decision_val else ('#DC2626' if 'REJECT' in decision_val else '#D97706')

        dec_info = [
            [
                Paragraph("<b>Final Decision:</b>", body_style),
                Paragraph(f"<b><font color='{dec_color}' size='10'>{decision_val}</font></b>", body_style)
            ],
            [
                Paragraph("<b>Moderator Remarks:</b>", body_style),
                Paragraph(str(report_data.get('remarks') or "Awaiting Moderator Review."), body_style)
            ],
            [
                Paragraph("<b>Required Action:</b>", body_style),
                Paragraph(str(report_data.get('required_action') or "No specific action required."), body_style)
            ],
            [
                Paragraph("<b>Reviewed By:</b>", body_style),
                Paragraph(str(report_data.get('moderator_name') or "Chief Examination Moderator"), body_style)
            ],
            [
                Paragraph("<b>Review Timestamp:</b>", body_style),
                Paragraph(str(report_data.get('moderated_at') or "Awaiting final review timestamp"), body_style)
            ]
        ]

        dec_table = Table(dec_info, colWidths=[110, 430])
        dec_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF3C7')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F59E0B')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(dec_table)
        story.append(Spacer(1, 15))

        # Signatures Area
        sig_info = [
            [
                Paragraph("<b>Course Faculty Signature</b><br/><br/>_______________________", body_style),
                Paragraph("<b>Subject Expert Signature</b><br/><br/>_______________________", body_style),
                Paragraph("<b>Examination Cell Controller</b><br/><br/>_______________________", body_style)
            ]
        ]
        sig_table = Table(sig_info, colWidths=[180, 180, 180])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(KeepTogether(sig_table))

        doc.build(story)
        return buffer.getvalue()


def generate_reportlab_pdf(
    paper_dict: dict,
    report_dict: dict,
    subject_dict: dict,
    questions: list,
    rules: list,
    findings: list,
    moderator_review: dict,
    output_path: str
) -> str:
    """Convenience function to generate institutional PDF directly to a file."""
    sub_code = (subject_dict or {}).get("code", "")
    sub_name = (subject_dict or {}).get("name", "")
    
    # Prepare question breakdown
    q_breakdown = []
    for q in questions or []:
        q_breakdown.append({
            "q_num": q.get("question_number", ""),
            "marks": q.get("marks"),
            "bloom": q.get("bloom_level") or "—",
            "co": q.get("co_code") or "—",
            "unit_topic": q.get("topic_name") or (f"Unit {q.get('detected_unit_number')}" if q.get('detected_unit_number') else "—"),
            "question_text": q.get("question_text", "")
        })

    # Prepare report data
    report_data = {
        "paper_id": (paper_dict or {}).get("id"),
        "paper_title": (paper_dict or {}).get("title"),
        "subject_code": sub_code,
        "subject_name": sub_name,
        "academic_year": (paper_dict or {}).get("academic_year", "2025-2026"),
        "exam_type": (paper_dict or {}).get("exam_type", "Regular"),
        "overall_score": (report_dict or {}).get("overall_score") or (paper_dict or {}).get("overall_score"),
        "status": (paper_dict or {}).get("status", "PENDING_REVIEW"),
        "rule_results": rules or [],
        "questions_breakdown": q_breakdown,
        "decision": (moderator_review or {}).get("new_status") or (paper_dict or {}).get("status", "PENDING REVIEW"),
        "remarks": (moderator_review or {}).get("remarks") or (paper_dict or {}).get("moderator_feedback"),
        "required_action": (moderator_review or {}).get("required_action"),
        "moderator_name": (moderator_review or {}).get("moderator_name")
    }

    pdf_bytes = PDFReportExporter.create_pdf_report(report_data)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    return output_path


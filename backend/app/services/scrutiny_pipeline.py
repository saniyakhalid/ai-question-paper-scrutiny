"""
End-to-end scrutiny pipeline powered by MongoDB:
extract -> parse -> AI semantic mapping -> deterministic rule engine -> persist report & score.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING

from app.db.mongo import get_mongo_db, get_next_sequence, serialize_doc, serialize_docs
from app.services.extraction_service import DocumentExtractionService, ScannedDocumentException
from app.services.question_parser import QuestionParserService
from app.services.gemini_service import gemini_service
from app.services.similarity_service import similarity_service
from app.services.report_service import report_service
from app.services.solving_time_service import SolvingTimeEstimationService
from app.rules.rule_engine import rule_engine

logger = logging.getLogger(__name__)


def _safe_marks(value):
    if value is None:
        return None
    try:
        iv = int(value)
        return iv if iv > 0 else None
    except (TypeError, ValueError):
        return None


def extract_and_store_questions(db: Database, paper: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts text, parses structure, stores hierarchical questions in MongoDB.
    Handles scanned documents and enforces zero hallucination / no fake 5M marks.
    """
    paper_id = paper.get("id")
    file_path = paper.get("file_path") or paper.get("filepath") or ""
    file_type = paper.get("file_type") or ""

    try:
        raw_text = DocumentExtractionService.extract_text(file_path, file_type)
    except ScannedDocumentException as sde:
        db.question_papers.update_one(
            {"id": paper_id},
            {"$set": {"status": "EXTRACTION_FAILED", "instructions_json": [f"ERROR: {str(sde)}"]}}
        )
        return {
            "ok": False,
            "parsed_count": 0,
            "error": str(sde),
            "detailed": {"raw_text": "", "instructions": [], "questions": []},
        }
    except Exception as exc:
        db.question_papers.update_one(
            {"id": paper_id},
            {"$set": {"status": "FAILED", "instructions_json": [f"ERROR: {str(exc)}"]}}
        )
        return {
            "ok": False,
            "parsed_count": 0,
            "error": f"Failed to extract document: {exc}",
            "detailed": {"raw_text": "", "instructions": [], "questions": []},
        }

    detailed = QuestionParserService.parse_paper_detailed(raw_text)

    db.question_papers.update_one(
        {"id": paper_id},
        {"$set": {
            "raw_text": detailed.get("raw_text") or raw_text,
            "normalized_text": detailed.get("normalized_text"),
            "instructions_json": detailed.get("instructions") or []
        }}
    )

    # Clear previous questions for clean re-extraction
    db.extracted_questions.delete_many({"paper_id": paper_id})

    items = detailed.get("all_items") or detailed.get("questions") or []
    analyzable = detailed.get("questions") or []
    if not analyzable:
        db.question_papers.update_one({"id": paper_id}, {"$set": {"status": "EXTRACTION_FAILED"}})
        return {
            "ok": False,
            "parsed_count": 0,
            "error": (
                "No examination questions could be reliably extracted from this document. "
                "Please verify the uploaded paper or review the extraction preview."
            ),
            "detailed": detailed,
        }

    parent_id_by_number: Dict[str, int] = {}
    parsed_count = 0

    # Pass 1: Insert QUESTION_GROUP rows first to establish parent IDs
    for q_data in items:
        q_type = q_data.get("question_type") or "QUESTION"
        if q_type != "QUESTION_GROUP":
            continue
        q_num = q_data.get("question_number") or q_data.get("original_number") or "Q?"
        grp_id = get_next_sequence("extracted_questions")
        grp_doc = {
            "id": grp_id,
            "paper_id": paper_id,
            "question_number": q_num,
            "original_number": q_num,
            "sub_question": None,
            "question_text": q_data.get("question_text") or "",
            "original_text": q_data.get("original_text") or q_data.get("raw_text") or "",
            "marks": _safe_marks(q_data.get("marks")),
            "internal_choice": False,
            "section_name": q_data.get("section_name") or q_data.get("section") or "GENERAL",
            "question_type": "QUESTION_GROUP",
            "choice_group_id": None,
            "parent_question_id": None,
            "parse_confidence": q_data.get("parse_confidence", 1.0),
            "marks_confidence": q_data.get("marks_confidence"),
            "metadata_confidence": q_data.get("metadata_confidence"),
            "co_code": q_data.get("co_code"),
            "bloom_level": q_data.get("bloom_level"),
            "raw_text": q_data.get("raw_text"),
            "normalized_text": q_data.get("normalized_text"),
            "sequence_order": q_data.get("sequence_order") or 1,
            "is_unit_selected": True,
            "unit_validation_status": "VALID"
        }
        db.extracted_questions.insert_one(grp_doc)
        parent_id_by_number[q_num] = grp_id
        parsed_count += 1

    # Pass 2: Insert SUBQUESTION and regular QUESTION rows, linking parent_question_id
    for q_data in items:
        q_type = q_data.get("question_type") or "QUESTION"
        if q_type == "QUESTION_GROUP":
            continue
        q_num = q_data.get("question_number") or q_data.get("original_number") or "Q?"
        q_id = get_next_sequence("extracted_questions")
        parent_num = q_data.get("parent_number")
        parent_q_id = parent_id_by_number.get(parent_num) if parent_num else None

        q_doc = {
            "id": q_id,
            "paper_id": paper_id,
            "question_number": q_num,
            "original_number": q_num,
            "sub_question": q_data.get("sub_question"),
            "parent_number": parent_num,
            "question_text": q_data.get("question_text") or "",
            "original_text": q_data.get("original_text") or q_data.get("raw_text") or "",
            "marks": _safe_marks(q_data.get("marks")),
            "internal_choice": bool(q_data.get("internal_choice", False)),
            "section_name": q_data.get("section_name") or q_data.get("section") or "GENERAL",
            "question_type": q_type,
            "choice_group_id": q_data.get("choice_group_id"),
            "parent_question_id": parent_q_id,
            "parse_confidence": q_data.get("parse_confidence", 1.0),
            "marks_confidence": q_data.get("marks_confidence"),
            "metadata_confidence": q_data.get("metadata_confidence"),
            "co_code": q_data.get("co_code"),
            "bloom_level": q_data.get("bloom_level"),
            "raw_text": q_data.get("raw_text"),
            "normalized_text": q_data.get("normalized_text"),
            "sequence_order": q_data.get("sequence_order") or 1,
            "is_unit_selected": True,
            "unit_validation_status": "VALID"
        }
        db.extracted_questions.insert_one(q_doc)
        parsed_count += 1

    db.question_papers.update_one({"id": paper_id}, {"$set": {"status": "EXTRACTED"}})
    return {"ok": True, "parsed_count": parsed_count, "error": None, "detailed": detailed}


def run_scrutiny_analysis(db: Database, paper: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes complete scrutiny analysis (AI + deterministic rules + similarity) and persists
    ScrutinyReport, findings, rule results, and scrutiny score directly in MongoDB.
    """
    paper_id = paper.get("id")
    if paper.get("validation_status") != "VALID_MATCH":
        return {
            "ok": False,
            "error": "Scrutiny is blocked because subject/document validation did not pass.",
            "validation_status": paper.get("validation_status") or "NOT_VALIDATED",
        }
    db.question_papers.update_one({"id": paper_id}, {"$set": {"status": "ANALYZING"}})

    try:
        all_questions = list(
            db.extracted_questions.find({"paper_id": paper_id}).sort("sequence_order", ASCENDING)
        )
        all_q_dicts = [
            {
                "id": q.get("id"),
                "question_number": q.get("original_number") or q.get("question_number"),
                "question_text": q.get("question_text", ""),
                "marks": q.get("marks"),
                "co_code": q.get("co_code"),
                "bloom_level": q.get("bloom_level"),
                "section_name": q.get("section_name", "GENERAL"),
                "question_type": q.get("question_type", "QUESTION"),
                "parent_number": q.get("parent_number") or (
                    re.match(r"^(Q\.\s*\d+)", q.get("original_number") or q.get("question_number", "")).group(1)
                    if re.match(r"^(Q\.\s*\d+)", q.get("original_number") or q.get("question_number", ""))
                    else None
                ),
                "internal_choice": q.get("internal_choice", False),
                "choice_group_id": q.get("choice_group_id"),
                "parse_confidence": q.get("parse_confidence", 1.0),
            }
            for q in all_questions
        ]
        analyzable = [
            q for q in all_questions
            if (q.get("question_type") or "QUESTION") in ("QUESTION", "SUBQUESTION", None)
        ]

        if not analyzable:
            db.question_papers.update_one({"id": paper_id}, {"$set": {"status": "EXTRACTION_FAILED"}})
            return {
                "ok": False,
                "error": "No examination questions found for scrutiny. Review extraction preview.",
            }

        q_dicts = [q for q in all_q_dicts if (q.get("question_type") or "QUESTION") in ("QUESTION", "SUBQUESTION", None)]

        subject_id = paper.get("subject_id")
        subject = db.subjects.find_one({"id": subject_id}) or {}
        subject_code = subject.get("code", "SUB")
        subject_name = subject.get("name", "Subject")

        # Load syllabus and COs strictly for this subject
        cos_docs = list(db.course_outcomes.find({"subject_id": subject_id}))
        course_outcomes = [
            {"co_code": c.get("co_code"), "description": c.get("description", "")}
            for c in cos_docs
        ]

        units_docs = list(db.syllabus_units.find({"subject_id": subject_id}).sort("unit_number", ASCENDING))
        syllabus_units = []
        for u in units_docs:
            topics = u.get("topics") or []
            if not topics:
                top_docs = list(db.syllabus_topics.find({"unit_id": u.get("id")}))
                topics = [{"topic_name": t.get("topic_name", "")} for t in top_docs]
            syllabus_units.append({
                "unit_number": u.get("unit_number"),
                "title": u.get("title", ""),
                "topics": topics,
            })

        selected_units = paper.get("selected_units_json") or [u["unit_number"] for u in syllabus_units]

        # AI Semantic Analysis
        try:
            ai_results = gemini_service.analyze_paper_questions(
                subject_code=subject_code,
                subject_name=subject_name,
                course_outcomes=course_outcomes,
                syllabus_units=syllabus_units,
                questions=q_dicts,
                selected_units=selected_units,
            )
        except Exception as e:
            logger.exception("AI analysis exception, falling back to heuristic")
            ai_results = gemini_service._semantic_heuristic_analysis(
                subject_code,
                subject_name,
                course_outcomes,
                syllabus_units,
                q_dicts,
                selected_units,
            )

        ai_by_num = {r.get("question_number"): r for r in (ai_results or [])}
        analysis_mode = (
            "gemini"
            if ai_results and all(r.get("analysis_mode") == "gemini" for r in ai_results)
            else "offline_heuristic"
        )
        bloom_findings = []
        co_findings = []
        syllabus_findings = []
        valid_units = set(selected_units) if selected_units else {u["unit_number"] for u in syllabus_units}
        selected_set = set(selected_units) if selected_units else valid_units

        # Determine candidate COs for active unit scope
        if selected_set:
            candidate_cos = [
                c for c in course_outcomes
                if (re.search(r"\d+", str(c.get("co_code", ""))) and int(re.search(r"\d+", str(c.get("co_code", ""))).group()) in selected_set)
                or (c.get("unit_number") in selected_set)
            ]
            if not candidate_cos:
                candidate_cos = course_outcomes[:len(selected_units)]
        else:
            candidate_cos = course_outcomes

        # Update questions in MongoDB
        for q in analyzable:
            q_num = q.get("original_number") or q.get("question_number")
            ai = ai_by_num.get(q_num, {})

            bloom = q.get("bloom_level") or ai.get("bloom_level")
            unit = ai.get("unit_number")
            if unit is not None and valid_units and unit not in valid_units:
                unit = None
            topic = ai.get("topic_name")

            raw_co = q.get("co_code")
            ai_co = ai.get("co_code")
            co = ai_co or raw_co
            if candidate_cos:
                candidate_co_codes = {c.get("co_code") for c in candidate_cos}
                if co not in candidate_co_codes:
                    if raw_co in candidate_co_codes:
                        co = raw_co
                    elif ai_co in candidate_co_codes:
                        co = ai_co
                    elif unit:
                        unit_co = next((c.get("co_code") for c in candidate_cos if re.search(r"\d+", str(c.get("co_code", ""))) and int(re.search(r"\d+", str(c.get("co_code", ""))).group()) == unit), None)
                        co = unit_co or candidate_cos[0].get("co_code")
                    else:
                        co = candidate_cos[0].get("co_code")
            if co and not str(co).upper().startswith("CO"):
                co = None

            if unit is None:
                val_status = "UNMAPPED"
                is_sel = True
            else:
                val_status = "VALID"
                is_sel = True

            db.extracted_questions.update_one(
                {"id": q["id"]},
                {"$set": {
                    "bloom_level": bloom,
                    "co_code": co,
                    "detected_unit_number": unit,
                    "topic_name": topic,
                    "unit_validation_status": val_status,
                    "is_unit_selected": is_sel,
                }}
            )

            bloom_findings.append({
                "question_id": q["id"],
                "bloom_level": bloom,
                "confidence": ai.get("confidence")
            })
            co_findings.append({
                "question_id": q["id"],
                "co_code": co,
                "confidence": ai.get("confidence")
            })
            syllabus_findings.append({
                "question_id": q["id"],
                "unit_number": unit,
                "topic_name": topic,
                "confidence": ai.get("confidence")
            })

        exam_pattern = db.examination_patterns.find_one({"subject_id": subject_id}) or {}

        # Comprehensive Similarity Search (Subject-Isolated Previous Papers + Other Papers + In-Paper Duplicates)
        prev_papers = list(db.previous_papers.find({"subject_id": subject_id}))
        prev_paper_map = {p.get("id"): p for p in prev_papers}
        prev_ids = [p.get("id") for p in prev_papers]
        prev_qs = list(db.previous_questions.find({"paper_id": {"$in": prev_ids}})) if prev_ids else []

        other_submitted_papers = list(db.question_papers.find({"subject_id": subject_id, "id": {"$ne": paper_id}}))
        other_submitted_ids = [op.get("id") for op in other_submitted_papers]
        other_qs = list(db.extracted_questions.find({
            "paper_id": {"$in": other_submitted_ids},
            "question_type": {"$ne": "QUESTION_GROUP"}
        })) if other_submitted_ids else []

        comparison_pool = []
        for pq in prev_qs:
            parent_p = prev_paper_map.get(pq.get("paper_id")) or {}
            title = parent_p.get("title") or "Historical Question Paper"
            acad_year = parent_p.get("academic_year")
            exam_type = parent_p.get("exam_type")
            details = []
            if exam_type:
                details.append(exam_type)
            if acad_year:
                details.append(acad_year)
            paper_label = f"{title} ({', '.join(details)})" if details else title

            comparison_pool.append({
                "id": pq.get("id"),
                "question_text": pq.get("question_text", ""),
                "paper_title": paper_label,
                "source_type": "PREVIOUS_PAPER",
            })
        for oq in other_qs:
            parent_p = next((op for op in other_submitted_papers if op.get("id") == oq.get("paper_id")), None)
            title = parent_p.get("title") if parent_p else "Other Submitted Paper"
            comparison_pool.append({
                "id": oq.get("id"),
                "question_text": oq.get("question_text", ""),
                "paper_title": f"Paper #{oq.get('paper_id')} ({title})",
                "source_type": "SUBMITTED_PAPER",
            })

        sim_results = []
        similarity_available = bool(comparison_pool) or len(q_dicts) > 1
        configured_similarity_threshold = exam_pattern.get("similarity_threshold")
        similarity_threshold = (
            float(configured_similarity_threshold) / 100.0
            if configured_similarity_threshold is not None
            else None
        )

        # 1. Compare against historical and other submitted papers
        if comparison_pool:
            for q in q_dicts:
                matches = similarity_service.find_similar_questions(
                    q["question_text"], comparison_pool, threshold=similarity_threshold
                )
                if matches:
                    for m in matches:
                        sim_results.append({
                            "question_id": q["id"],
                            "question_number": q.get("question_number"),
                            "matched_previous_question_id": m.get("matched_previous_question_id"),
                            "matched_question_text": m.get("matched_question_text"),
                            "matched_paper_title": m.get("matched_paper_title"),
                            "similarity_score": m.get("similarity_score", 0.0),
                            "explanation": m.get("explanation", ""),
                        })

        # 2. In-Paper Duplicate / Repetition Detection across different questions
        for i, q1 in enumerate(q_dicts):
            q1_text = (q1.get("question_text") or "").strip()
            if not q1_text or len(q1_text.split()) < 3:
                continue
            for j in range(i + 1, len(q_dicts)):
                q2 = q_dicts[j]
                q2_text = (q2.get("question_text") or "").strip()
                if not q2_text or len(q2_text.split()) < 3:
                    continue
                in_paper_matches = similarity_service.find_similar_questions(
                    q1_text, [{"id": q2["id"], "question_text": q2_text, "paper_title": "Current Paper"}],
                    threshold=0.75
                )
                if in_paper_matches:
                    m = in_paper_matches[0]
                    score = m.get("similarity_score", 0.0)
                    sim_results.append({
                        "question_id": q1["id"],
                        "question_number": q1.get("question_number"),
                        "matched_previous_question_id": q2["id"],
                        "matched_question_text": q2_text,
                        "matched_paper_title": f"Internal Paper Repetition (with {q2.get('question_number')})",
                        "similarity_score": score,
                        "explanation": f"High internal similarity ({round(score*100, 1)}%) detected with Question {q2.get('question_number')} in this same question paper. Flagged for review to ensure question diversity."
                    })

        # Determine declared marks
        declared_marks = None
        if paper.get("examination_id"):
            exam = db.examinations.find_one({"id": paper["examination_id"]})
            if exam and exam.get("total_marks"):
                declared_marks = exam["total_marks"]
        if not declared_marks and paper.get("raw_text"):
            p_det = QuestionParserService.parse_paper_detailed(paper["raw_text"])
            declared_marks = p_det.get("declared_total_marks")
        configured_total_marks = exam_pattern.get("total_marks")
        if configured_total_marks is None:
            configured_total_marks = subject.get("total_marks")
        if declared_marks is not None and not paper.get("examination_id"):
            configured_total_marks = declared_marks
        duration_mins = exam_pattern.get("duration_minutes")
        if duration_mins is None:
            duration_mins = subject.get("duration_minutes")

        bloom_names = {
            "K1": "Remember", "K2": "Understand", "K3": "Apply",
            "K4": "Analyze", "K5": "Evaluate", "K6": "Create",
        }
        seen_timing_choices = set()
        timing_inputs = []
        for q in q_dicts:
            if (q.get("question_type") or "").upper() == "QUESTION_GROUP":
                continue
            choice_id = q.get("choice_group_id")
            if choice_id:
                if choice_id in seen_timing_choices:
                    continue
                seen_timing_choices.add(choice_id)
            elif q.get("internal_choice"):
                q_id_key = f"{q.get('parent_number')}_{q.get('sub_question') or q.get('question_number')}"
                if q_id_key in seen_timing_choices:
                    continue
                seen_timing_choices.add(q_id_key)
            bloom = q.get("bloom_level") or ai_by_num.get(q.get("question_number"), {}).get("bloom_level")
            timing_inputs.append((q, bloom))

        group_caps = {}
        for q in all_q_dicts:
            if (q.get("question_type") or "").upper() == "QUESTION_GROUP":
                q_num = q.get("question_number", "")
                if q.get("marks") is not None:
                    group_caps[q_num] = q.get("marks")

        if duration_mins is not None and all(q.get("marks") is not None and bloom for q, bloom in timing_inputs):
            group_estimates = {}
            standalone_estimates = []
            for q, bloom in timing_inputs:
                p_est = SolvingTimeEstimationService.estimate_question_time(
                    int(q["marks"]), bloom_names.get(str(bloom).upper(), str(bloom))
                )
                parent_num = q.get("parent_number")
                if not parent_num:
                    m_p = re.match(r"^(Q(?:uestion)?\s*[\.\-]?\s*\d+)", str(q.get("question_number", "")), re.I)
                    if m_p:
                        raw_p = m_p.group(1)
                        for gm_key in group_caps:
                            if re.sub(r"[\s\.\-_]", "", gm_key).upper() == re.sub(r"[\s\.\-_]", "", raw_p).upper():
                                parent_num = gm_key
                                break
                if parent_num and parent_num in group_caps:
                    group_estimates.setdefault(parent_num, []).append((q.get("marks", 0), p_est))
                else:
                    standalone_estimates.append(p_est)

            total_timing_list = []
            for g_num, items in group_estimates.items():
                g_cap = group_caps.get(g_num)
                g_sum_marks = sum(m for m, est in items)
                g_sum_time = sum(est for m, est in items if est is not None)
                if g_cap is not None and g_sum_marks > g_cap and g_sum_marks > 0:
                    total_timing_list.append(g_sum_time * (g_cap / g_sum_marks))
                else:
                    total_timing_list.append(g_sum_time)
            total_timing_list.extend([e for e in standalone_estimates if e is not None])
            estimated_solving_time = sum(total_timing_list) if total_timing_list and all(v is not None for v in standalone_estimates) else None
        else:
            estimated_solving_time = None

        subj_config = {
            "total_marks": configured_total_marks,
            "declared_total_marks": declared_marks,
            "duration_minutes": duration_mins,
            "min_co_coverage_pct": exam_pattern.get("min_co_coverage_pct"),
            "min_unit_coverage_pct": exam_pattern.get("min_unit_coverage_pct"),
            "min_higher_order_bloom_pct": exam_pattern.get("min_higher_order_bloom_pct"),
            "internal_choice_required": exam_pattern.get("internal_choice_required"),
            "course_outcomes": course_outcomes,
            "syllabus_units": syllabus_units,
        }

        evaluated_rules = rule_engine.validate_paper(
            questions=all_q_dicts,
            subject_config=subj_config,
            bloom_findings=bloom_findings,
            co_findings=co_findings,
            syllabus_findings=syllabus_findings,
            estimated_solving_time_minutes=estimated_solving_time,
            selected_units=selected_units,
        )

        if similarity_available:
            similarity_rule_status = "WARNING" if sim_results else "PASS"
            similarity_rule_message = (
                f"{len(sim_results)} possible similar question(s) found in the selected subject's previous papers; moderator review is required."
                if sim_results else "No above-threshold similar questions were found in the available subject-specific previous papers."
            )
            similarity_actual = f"Compared with {len(prev_qs)} historical question(s); {len(sim_results)} possible match(es)."
        else:
            similarity_rule_status = "NOT_EVALUATED"
            similarity_rule_message = (
                "Subject-specific historical questions are unavailable or could not be compared."
            )
            similarity_actual = "Historical comparison unavailable."
        active_similarity_threshold = similarity_service.threshold if similarity_threshold is None else similarity_threshold
        evaluated_rules.append({
            "rule_name": "Previous Paper Similarity Check",
            "category": "SIMILARITY",
            "expected": f"Flag TF-IDF similarity >= {active_similarity_threshold * 100:.1f}% (review aid, not plagiarism determination)",
            "actual": similarity_actual,
            "status": similarity_rule_status,
            "message": similarity_rule_message,
        })

        findings_score_payload = []
        for q in analyzable:
            q_num = q.get("original_number") or q.get("question_number")
            ai = ai_by_num.get(q_num, {})
            findings_score_payload.extend([
                {"question_id": q["id"], "finding_type": "BLOOM", "ai_value": q.get("bloom_level")},
                {"question_id": q["id"], "finding_type": "CO", "ai_value": q.get("co_code")},
                {"question_id": q["id"], "finding_type": "GRAMMAR", "ai_value": ai.get("grammar_status", "NOT_EVALUATED")},
                {"question_id": q["id"], "finding_type": "QUALITY", "ai_value": ai.get("quality_status", "NOT_EVALUATED")},
            ])

        score_breakdown = report_service.calculate_score_breakdown(
            evaluated_rules, findings_score_payload, sim_results, similarity_available
        )
        scrutiny_score = score_breakdown["overall_score"]
        analysis_notice = (
            "Offline academic analysis completed: Bloom and CO mappings, active unit validation, academic grammar checking, and rule compliance evaluated."
            if analysis_mode == "offline_heuristic"
            else "Gemini analysis ran for this report. Review the evidence and findings before making a moderator decision."
        )

        # Version management for ScrutinyReport
        prev_report = db.scrutiny_reports.find_one({"paper_id": paper_id}, sort=[("version", DESCENDING)])
        version = (prev_report.get("version", 0) + 1) if prev_report else 1

        rep_id = get_next_sequence("scrutiny_reports")
        report_doc = {
            "id": rep_id,
            "paper_id": paper_id,
            "version": version,
            "overall_score": scrutiny_score,
            "score_breakdown": score_breakdown,
            "evidence_coverage_pct": score_breakdown["evidence_coverage_pct"],
            "analysis_mode": analysis_mode,
            "analysis_notice": analysis_notice,
            "solving_time_minutes": estimated_solving_time,
            "compliance_summary": (
                f"Scrutiny checks completed for {len(analyzable)} examination questions for {subject_code}. "
                f"Evidence coverage: {score_breakdown['evidence_coverage_pct']}% of the configured scoring rubric."
            ),
            "compliance_status": score_breakdown["rating"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.scrutiny_reports.insert_one(report_doc)

        # Insert Rule Results
        for r in evaluated_rules:
            db.rule_results.insert_one({
                "report_id": rep_id,
                "category": r.get("category", "GENERAL"),
                "rule_name": r.get("rule_name", ""),
                "expected_value": str(r.get("expected", "")),
                "actual_value": str(r.get("actual", "")),
                "status": r.get("status", "PASS"),
                "message": r.get("message", "Rule satisfied"),
            })

        # Insert Scrutiny Findings
        for q in analyzable:
            q_num = q.get("original_number") or q.get("question_number")
            ai = ai_by_num.get(q_num, {})
            findings_data = [
                ("BLOOM", q.get("bloom_level"), ai.get("confidence"), ai.get("reasoning") or "Cognitive level classification", None),
                ("CO", q.get("co_code"), ai.get("confidence"), ai.get("reasoning") or "Course outcome alignment", None),
                (
                    "SYLLABUS",
                    f"Unit {q.get('detected_unit_number')}" if q.get("detected_unit_number") is not None else "Unmapped",
                    ai.get("confidence"),
                    "Syllabus coverage check",
                    None
                ),
                ("GRAMMAR", ai.get("grammar_status", "PASS"), ai.get("confidence"), ai.get("reasoning") or "Question grammar and syntax evaluated.", ai.get("issues")),
                ("QUALITY", ai.get("quality_status", "PASS"), ai.get("confidence"), ai.get("reasoning") or "Question language clarity evaluated.", None),
            ]
            for ftype, val, conf, reas, iss in findings_data:
                db.scrutiny_findings.insert_one({
                    "id": get_next_sequence("scrutiny_findings"),
                    "report_id": rep_id,
                    "question_id": q["id"],
                    "finding_type": ftype,
                    "ai_value": str(val) if val is not None else "N/A",
                    "confidence": float(conf) if conf is not None else None,
                    "reasoning": reas or "",
                    "suggested_improvement": ai.get("suggested_improvement"),
                    "issues": iss or [],
                })

        # Insert Similarity Results (cleaned on re-run)
        db.similarity_results.delete_many({"report_id": rep_id})
        for s in sim_results:
            db.similarity_results.insert_one({
                "id": get_next_sequence("similarity_results"),
                "report_id": rep_id,
                "question_id": s["question_id"],
                "question_number": s.get("question_number"),
                "matched_previous_question_id": s.get("matched_previous_question_id"),
                "matched_question_text": s.get("matched_question_text"),
                "matched_paper_title": s.get("matched_paper_title"),
                "similarity_score": s.get("similarity_score", 0.0),
                "explanation": s.get("explanation", ""),
            })

        # Atomically update paper status and score
        db.question_papers.update_one(
            {"id": paper_id},
            {"$set": {
                "status": "PENDING_REVIEW",
                "overall_score": scrutiny_score,
            }}
        )

        return {
            "ok": True,
            "report_id": rep_id,
            "overall_score": scrutiny_score,
            "status": "PENDING_REVIEW",
            "similarity_matches": len(sim_results),
            "questions_analyzed": len(analyzable),
            "error": None,
        }

    except Exception as e:
        logger.exception("Scrutiny pipeline failed")
        db.question_papers.update_one(
            {"id": paper_id},
            {"$set": {"status": "FAILED"}}
        )
        return {"ok": False, "error": f"Scrutiny pipeline failed: {e}"}

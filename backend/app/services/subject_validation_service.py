"""
Validates that an uploaded question paper matches the selected subject workspace.
Prevents cross-subject uploads (e.g. DBMS paper uploaded under ML subject).
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional, Set

from pymongo.database import Database

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "about", "after", "also", "been", "before", "being", "between", "both",
    "come", "could", "each", "explain", "from", "have", "into", "just",
    "like", "make", "marks", "more", "must", "only", "other", "paper",
    "question", "questions", "section", "shall", "should", "such", "than",
    "that", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "using", "very", "what", "when", "where", "which",
    "while", "with", "would", "write", "your", "answer", "attempt",
    "compulsory", "following", "given", "total", "marks", "hours",
    "examination", "semester", "subject", "code", "year", "time",
    "engineering", "technology", "computer", "science", "system", "systems",
    "introduction", "fundamentals", "basic", "basics", "advanced", "study",
}


def _mismatch_message(selected_code: str, selected_name: str, detected_label: str) -> str:
    return (
        f"Subject is not as per selected. The uploaded document appears to belong to "
        f"[{detected_label}], but you selected [{selected_code} - {selected_name}]. "
        f"Please select the correct subject workspace or upload the matching question paper."
    )


def _normalize_code(code: Optional[str]) -> str:
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


def _tokenize(text: str) -> Set[str]:
    words = re.findall(r"\b[a-zA-Z]{4,}\b", (text or "").lower())
    return {w for w in words if w not in STOP_WORDS}


def _subject_name_tokens(name: str) -> Set[str]:
    return {
        w.lower()
        for w in re.findall(r"[A-Za-z]{4,}", name or "")
        if w.lower() not in STOP_WORDS
    }


def _build_subject_keywords(db: Database, subject_id: int) -> Set[str]:
    """Build distinctive keyword set from subject metadata and syllabus."""
    subject = db.subjects.find_one({"id": subject_id}) or {}
    keywords: Set[str] = set()

    for part in re.findall(r"[A-Za-z]{3,}", subject.get("name") or ""):
        if part.lower() not in STOP_WORDS:
            keywords.add(part.lower())

    code = _normalize_code(subject.get("code"))
    if code:
        keywords.add(code.lower())
        alpha = re.sub(r"[0-9]", "", code.lower())
        if len(alpha) >= 2:
            keywords.add(alpha)

    units = list(db.syllabus_units.find({"subject_id": subject_id}))
    for unit in units:
        for word in re.findall(r"[A-Za-z]{4,}", unit.get("title") or ""):
            keywords.add(word.lower())
        topics = unit.get("topics") or []
        if not topics:
            topics = list(db.syllabus_topics.find({"unit_id": unit.get("id")}))
        for topic in topics:
            t_name = topic.get("topic_name") if isinstance(topic, dict) else str(topic)
            for word in re.findall(r"[A-Za-z]{4,}", t_name or ""):
                keywords.add(word.lower())

    for co in db.course_outcomes.find({"subject_id": subject_id}):
        for word in re.findall(r"[A-Za-z]{4,}", co.get("description") or ""):
            keywords.add(word.lower())

    return keywords


def _score_document_against_keywords(doc_tokens: Set[str], keywords: Set[str]) -> float:
    if not keywords or not doc_tokens:
        return 0.0
    overlap = len(doc_tokens & keywords)
    return overlap / max(len(keywords), 1)


def _find_subject_by_code(db: Database, code: str) -> Optional[Dict[str, Any]]:
    norm = _normalize_code(code)
    if not norm:
        return None
    for subj in db.subjects.find():
        if _normalize_code(subj.get("code")) == norm:
            return subj
    return None


def validate_filename_against_subject(
    db: Database,
    subject_id: int,
    filename: str,
) -> Dict[str, Any]:
    """Return filename clues without treating a filename as proof of subject identity."""
    selected = db.subjects.find_one({"id": subject_id})
    if not selected:
        return {"valid": False, "message": "Selected subject not found."}

    fname = (filename or "").lower()
    for subj in db.subjects.find():
        sid = subj.get("id")
        if sid == subject_id:
            continue

        code = (subj.get("code") or "").lower()
        name = (subj.get("name") or "").lower()
        if code and len(code) >= 3 and code in fname:
            return {"valid": True, "filename_subject_hint": sid, "check": "filename_hint"}
        if name and len(name) >= 6 and name in fname:
            return {"valid": True, "filename_subject_hint": sid, "check": "filename_hint"}

    return {"valid": True, "check": "filename_uninformative"}


def validate_paper_subject(
    db: Database,
    subject_id: int,
    raw_text: str,
    questions: List[Dict[str, Any]],
    detected_subject_code: Optional[str] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns {"valid": bool, "message": str, ...}.
    Rejects when document clearly belongs to a different subject than selected.
    """
    selected = db.subjects.find_one({"id": subject_id})
    if not selected:
        return {"valid": False, "message": "Selected subject not found."}

    selected_code = selected.get("code", "")
    selected_name = selected.get("name", "")

    filename_hint = validate_filename_against_subject(db, subject_id, filename) if filename else None

    # 1. Header subject code mismatch (strong signal)
    if detected_subject_code:
        detected_norm = _normalize_code(detected_subject_code)
        selected_norm = _normalize_code(selected_code)
        if detected_norm and selected_norm and detected_norm != selected_norm:
            matched = _find_subject_by_code(db, detected_subject_code)
            if matched and matched.get("id") != subject_id:
                label = f"{matched.get('code')} - {matched.get('name')}"
                return {
                    "valid": False,
                    "outcome": "mismatch",
                    "message": _mismatch_message(selected_code, selected_name, label),
                    "detected_subject_code": detected_subject_code,
                    "matched_subject_id": matched.get("id"),
                    "check": "header_code",
                }

    # 2. Build document token corpus
    corpus_parts = [raw_text or ""]
    for q in questions:
        corpus_parts.append(q.get("question_text") or "")
        corpus_parts.append(q.get("original_text") or "")
    doc_tokens = _tokenize(" ".join(corpus_parts))

    if len(doc_tokens) < 5:
        return {
            "valid": False,
            "outcome": "inconclusive",
            "message": (
                f"Subject is not as per selected. Could not extract enough content from the document "
                f"to verify it belongs to [{selected_code} - {selected_name}]. "
                f"Please upload a valid question paper for the selected subject."
            ),
            "selected_score": 0.0,
            "check": "insufficient_text",
        }

    # 2b. Extract header Course/Subject name (e.g. 'Course: Operating Systems', 'Subject: Database Management')
    header_chunk = (raw_text or "")[:1500]
    course_match = re.search(
        r"(?:Course|Subject|Paper)\s*(?:Name|Title)?\s*[:\-]\s*([^\n\r,;]{3,60})",
        header_chunk,
        re.IGNORECASE,
    )
    if course_match:
        detected_course_raw = course_match.group(1).strip()
        detected_course_tokens = _subject_name_tokens(detected_course_raw)
        selected_tokens = _subject_name_tokens(selected_name)
        if detected_course_tokens:
            selected_name_hits = len(detected_course_tokens & selected_tokens)
            other_matched = None
            other_name_hits = 0
            for subj in db.subjects.find():
                if subj.get("id") == subject_id:
                    continue
                s_tokens = _subject_name_tokens(subj.get("name") or "")
                hits = len(s_tokens & detected_course_tokens)
                if hits > other_name_hits:
                    other_matched = subj
                    other_name_hits = hits

            # A generic shared word (for example, "learning") must not hide a
            # stronger match between the document title and another subject.
            if selected_name_hits == 0 or other_name_hits > selected_name_hits:
                label = f"{other_matched.get('code')} - {other_matched.get('name')}" if other_matched else detected_course_raw
                return {
                    "valid": False,
                    "outcome": "mismatch",
                    "message": _mismatch_message(selected_code, selected_name, label),
                    "detected_label": label,
                    "check": "header_course_title",
                }

    # 3. Score against all configured subjects
    all_subjects = list(db.subjects.find())
    scores: Dict[int, float] = {}
    subject_meta: Dict[int, Dict[str, Any]] = {}
    subject_matches: Dict[int, Set[str]] = {}

    for subj in all_subjects:
        sid = subj.get("id")
        keywords = _build_subject_keywords(db, sid)
        scores[sid] = _score_document_against_keywords(doc_tokens, keywords)
        subject_meta[sid] = subj
        subject_matches[sid] = doc_tokens & keywords

    selected_score = scores.get(subject_id, 0.0)
    best_id = max(scores, key=lambda k: scores[k]) if scores else subject_id
    best_score = scores.get(best_id, 0.0)
    best_subj = subject_meta.get(best_id, {})

    # 4. Cross-subject content mismatch
    best_matches = subject_matches.get(best_id, set())
    selected_matches = subject_matches.get(subject_id, set())

    # Two or more distinct syllabus terms are required before content can identify
    # another subject. This avoids rejecting a paper based on one shared keyword.
    if best_id != subject_id and len(best_matches) >= 2:
        margin = best_score - selected_score
        ratio = best_score / max(selected_score, 0.001)
        if len(selected_matches) < 2 or margin >= 0.015 or ratio >= 1.25:
            label = f"{best_subj.get('code')} - {best_subj.get('name')}"
            return {
                "valid": False,
                "outcome": "mismatch",
                "message": _mismatch_message(selected_code, selected_name, label),
                "detected_subject_id": best_id,
                "selected_score": round(selected_score, 4),
                "best_score": round(best_score, 4),
                "matched_keywords_count": len(best_matches),
                "check": "content_mismatch",
            }

    # 5. Subject identity mentioned prominently in the actual document is strong
    # contradictory evidence; a single shared term is not enough.
    corpus_lower = " ".join(corpus_parts).lower()
    selected_name_tokens = _subject_name_tokens(selected_name)
    for subj in all_subjects:
        if subj.get("id") == subject_id:
            continue
        other_tokens = _subject_name_tokens(subj.get("name") or "")
        distinctive = [t for t in other_tokens if t not in selected_name_tokens and len(t) >= 5]
        hits = sum(1 for t in distinctive if re.search(rf"\b{re.escape(t)}\b", corpus_lower))
        if hits >= 2:
            label = f"{subj.get('code')} - {subj.get('name')}"
            return {
                "valid": False,
                "outcome": "mismatch",
                "message": _mismatch_message(selected_code, selected_name, label),
                "detected_subject_id": subj.get("id"),
                "check": "subject_name_in_text",
            }

    # Content that cannot establish either selected-subject relevance or a clear
    # alternative remains inconclusive and is rejected before scrutiny.
    if len(selected_matches) < 2:
        return {
            "valid": False,
            "outcome": "inconclusive",
            "message": (
                f"Could not confirm that the uploaded document belongs to "
                f"[{selected_code} - {selected_name}]. Add the official syllabus and upload a readable paper with sufficient subject content."
            ),
            "selected_score": round(selected_score, 4),
            "matched_keywords_count": len(selected_matches),
            "check": "insufficient_subject_evidence",
            "filename_subject_hint": filename_hint.get("filename_subject_hint") if filename_hint else None,
        }

    return {
        "valid": True,
        "outcome": "accepted",
        "message": "Subject validation passed.",
        "selected_score": round(selected_score, 4),
        "best_score": round(best_score, 4),
        "matched_keywords_count": len(selected_matches),
        "check": "subject_content_match",
    }

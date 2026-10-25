"""
Deterministic academic question-paper parser for autonomous engineering colleges.

Classification Layer:
  DOCUMENT
    ├── HEADER / EXAM METADATA
    ├── GENERAL INSTRUCTIONS
    ├── SECTION HEADERS
    ├── QUESTION GROUP (e.g. Q.1 Solve the following questions [16])
    ├── QUESTIONS & SUBQUESTIONS (e.g. Q.1(a) [8], Q.1(b) [8])
    ├── INTERNAL CHOICES (e.g. OR alternatives)
    └── FOOTER (e.g. quotes, notices)

Source of truth for question numbers, marks, printed CO/Bloom, sections, and hierarchy.
NEVER invents marks (returns None when not confidently detected).
NEVER treats general instructions as examination questions.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class QuestionParserService:
    """
    Deterministic question paper parser.
    """

    PARSE_CONFIDENCE_THRESHOLD = 0.75

    INSTRUCTION_PHRASES = [
        "all questions are compulsory",
        "answer all questions",
        "attempt all questions",
        "make suitable assumptions",
        "assume suitable data",
        "use standard assumptions",
        "figures to the right indicate",
        "figures to the rights indicate",
        "figures in brackets indicate",
        "course outcome [co]",
        "course outcome",
        "bloom's taxonomy",
        "blooms taxonomy",
        "bloom’s taxonomy",
        "draw neat diagrams",
        "use of calculator",
        "short marking scheme",
        "marking scheme [ms]",
        "marking scheme",
        "k1-remembering",
        "k1- remembering",
        "answer any four",
        "answer any three",
        "answer any two",
        "answer any one",
        "co and bl are indicated",
        "the row below the question statement",
        "instructions to candidates",
        "instructions:",
        "instruction:",
        "note:",
        "hand-hygiene",
        "social-distancing",
        "time allowed",
        "duration of examination",
    ]

    HEADER_PHRASES = [
        "adcet",
        "annasaheb dange",
        "page no:",
        "page no",
        "urn :",
        "urn:-",
        "autonomous institute",
        "affiliated to",
        "engineering and technology",
        "shikshan sanstha",
        "accredited by naac",
        "mid semester examination",
        "end semester examination",
        "end-semester examination",
        "day and date",
        "time:-",
        "total marks:-",
        "total marks:",
        "max marks",
        "maximum marks",
        "[next page]",
        "ey-100",
        "ey-657",
        "gx-050",
        "academic year",
        "b. tech",
        "b.tech",
        "odd semester",
        "even semester",
        "branch:",
        "subject:",
        "time:",
        "autonomous engineering college",
    ]

    FOOTER_PHRASES = [
        "the time you spend on skills",
        "use face-mask",
        "follow hand-hygiene",
        "maintain social-distancing",
        "protect from covid",
    ]

    TABLE_HEADERS = {
        "marks",
        "co",
        "bl",
        "marks co bl",
        "marks co/bl",
        "ey-co bl",
        "unit no.",
        "unit no",
        "q.no",
        "q. no",
        "question",
    }

    @staticmethod
    def normalize_co_code(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        r = raw.strip().upper().replace("[", "").replace("]", "")
        m = re.search(r"(?:CO\s*[-_]?\s*(\d+)|_(\d+)$|^(\d+)$)", r)
        if m:
            num = m.group(1) or m.group(2) or m.group(3)
            return f"CO{num}"
        if r.startswith("CO"):
            return r
        return None

    @staticmethod
    def normalize_bloom_level(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        r = raw.strip().upper().replace("[", "").replace("]", "")
        m = re.match(r"^K([1-6])$", r)
        if m:
            return f"K{m.group(1)}"
        mapping = {
            "REMEMBERING": "K1",
            "REMEMBER": "K1",
            "UNDERSTANDING": "K2",
            "UNDERSTAND": "K2",
            "APPLYING": "K3",
            "APPLY": "K3",
            "ANALYZING": "K4",
            "ANALYZE": "K4",
            "EVALUATING": "K5",
            "EVALUATE": "K5",
            "CREATING": "K6",
            "CREATE": "K6",
        }
        return mapping.get(r)

    @classmethod
    def is_instruction_text(cls, text: str) -> bool:
        low = (text or "").strip().lower()
        if not low:
            return False
        if re.match(
            r"^(?:instructions?(?:\s+to\s+candidates?)?|note|important|general\s+instructions?)\s*[:.\-]?\s*$",
            low,
        ):
            return True
        return any(p in low for p in cls.INSTRUCTION_PHRASES)

    @classmethod
    def is_header_or_footer(cls, text: str) -> bool:
        low = (text or "").strip().lower()
        if not low:
            return False
        # Do not treat real question lines as headers
        if re.match(r"^Q\s*[\.\-]?\s*\d+", text, re.I) or re.match(
            r"^(?:Q\d+[\.\-]?)?\(?[a-h]\)", text, re.I
        ):
            return False
        if re.match(r"^mse\s+[a-z]+[.,]?\s*\d{4}", low):
            return True
        if any(p in low for p in cls.HEADER_PHRASES):
            return True
        return any(fp in low for fp in cls.FOOTER_PHRASES)

    @classmethod
    def extract_metadata_and_clean(
        cls, lines: List[str]
    ) -> Tuple[List[str], Optional[int], Optional[str], Optional[str], float]:
        """
        Scans lines for marks, CO, and Bloom tokens anywhere in the question block,
        cleans them out, and returns: (cleaned_lines, marks, co_code, bloom_level, marks_conf)
        Never invents marks (returns None if not detected).
        """
        marks: Optional[int] = None
        co_code: Optional[str] = None
        bloom_level: Optional[str] = None
        marks_conf = 0.0

        filtered: List[str] = []
        for l in lines:
            s = l.strip()
            if not s:
                continue
            if s.lower() in cls.TABLE_HEADERS:
                continue
            if cls.is_header_or_footer(s):
                continue
            if re.match(r"^MS\s*[\-–—\:]", s, re.I):
                continue
            filtered.append(s)

        # 1. Multi-line scan: 3 consecutive lines e.g. "08", "[1]", "K3" or "08", "K3", "CO1"
        cleaned: List[str] = []
        i = 0
        while i < len(filtered):
            if i + 2 < len(filtered) and marks is None:
                m_mk = re.match(r"^\[?(\d{1,2})\s*(?:Marks?|M)?\]?$", filtered[i], re.I)
                # Check order 1: Marks -> CO -> Bloom
                m_co1 = re.match(r"^\[?([A-Za-z0-9_]+)\]?$", filtered[i + 1])
                m_bl1 = re.match(r"^\[?(K[1-6])\]?$", filtered[i + 2], re.I)
                # Check order 2: Marks -> Bloom -> CO
                m_bl2 = re.match(r"^\[?(K[1-6])\]?$", filtered[i + 1], re.I)
                m_co2 = re.match(r"^\[?([A-Za-z0-9_]+)\]?$", filtered[i + 2])

                if m_mk and m_co1 and m_bl1:
                    cand_co = cls.normalize_co_code(m_co1.group(1))
                    cand_bl = cls.normalize_bloom_level(m_bl1.group(1))
                    if cand_co and cand_bl:
                        marks = int(m_mk.group(1))
                        co_code = cand_co
                        bloom_level = cand_bl
                        marks_conf = 0.98
                        i += 3
                        continue
                elif m_mk and m_bl2 and m_co2:
                    cand_bl = cls.normalize_bloom_level(m_bl2.group(1))
                    cand_co = cls.normalize_co_code(m_co2.group(1))
                    if cand_co and cand_bl:
                        marks = int(m_mk.group(1))
                        bloom_level = cand_bl
                        co_code = cand_co
                        marks_conf = 0.98
                        i += 3
                        continue

            # 2. 2 consecutive lines: e.g. "08 [1]" and "K3" or "08" and "[1] K3" or "08 K3" and "CO1"
            if i + 1 < len(filtered) and marks is None:
                # 2a. Marks+CO on line 1, Bloom on line 2
                m_mk_co = re.match(
                    r"^\[?(\d{1,2})\s*(?:Marks?|M)?\]?\s+\[?([A-Za-z0-9_]+)\]?$",
                    filtered[i],
                    re.I,
                )
                m_bl = re.match(r"^\[?(K[1-6])\]?$", filtered[i + 1], re.I)
                if m_mk_co and m_bl:
                    cand_co = cls.normalize_co_code(m_mk_co.group(2))
                    cand_bl = cls.normalize_bloom_level(m_bl.group(1))
                    if cand_co and cand_bl:
                        marks = int(m_mk_co.group(1))
                        co_code = cand_co
                        bloom_level = cand_bl
                        marks_conf = 0.96
                        i += 2
                        continue

                # 2b. Marks+Bloom on line 1, CO on line 2
                m_mk_bl = re.match(
                    r"^\[?(\d{1,2})\s*(?:Marks?|M)?\]?\s+\[?(K[1-6])\]?$",
                    filtered[i],
                    re.I,
                )
                m_co = re.match(r"^\[?([A-Za-z0-9_]+)\]?$", filtered[i + 1])
                if m_mk_bl and m_co:
                    cand_bl = cls.normalize_bloom_level(m_mk_bl.group(2))
                    cand_co = cls.normalize_co_code(m_co.group(1))
                    if cand_co and cand_bl:
                        marks = int(m_mk_bl.group(1))
                        bloom_level = cand_bl
                        co_code = cand_co
                        marks_conf = 0.96
                        i += 2
                        continue

                # 2c. Marks on line 1, CO+Bloom or Bloom+CO on line 2
                m_mk_only = re.match(r"^\[?(\d{1,2})\s*(?:Marks?|M)?\]?$", filtered[i], re.I)
                m_meta2 = re.match(
                    r"^\[?(?:CO\s*)?([A-Za-z0-9_]+)\]?\s+\[?(K[1-6])\]?$|^\[?(K[1-6])\]?\s+\[?(?:CO\s*)?([A-Za-z0-9_]+)\]?$",
                    filtered[i + 1],
                    re.I,
                )
                if m_mk_only and m_meta2:
                    cand_co = cls.normalize_co_code(m_meta2.group(1) or m_meta2.group(4))
                    cand_bl = cls.normalize_bloom_level(m_meta2.group(2) or m_meta2.group(3))
                    if cand_co and cand_bl:
                        marks = int(m_mk_only.group(1))
                        co_code = cand_co
                        bloom_level = cand_bl
                        marks_conf = 0.96
                        i += 2
                        continue

            curr = filtered[i]

            # 3. Leading metadata prefix e.g. "8 K3 CO1 Unit 1 - Topic Statement..." or "8 CO1 K3 Statement..."
            m_lead = re.match(
                r"^\[?(\d{1,2})\s*(?:Marks?|M)?\]?\s+"
                r"(?:\[?(K[1-6])\]?\s+\[?(?:CO\s*)?([A-Za-z0-9_]+)\]?|\[?(?:CO\s*)?([A-Za-z0-9_]+)\]?\s+\[?(K[1-6])\]?)"
                r"(?:\s+Unit\s*\d+\s*[\-–—:][^\w\n]*[A-Za-z0-9\s,/\(\)\-_]*?\s*[\-–—]?\s*)?"
                r"(.*)$",
                curr,
                re.I,
            )
            if m_lead and marks is None:
                cand_bl = cls.normalize_bloom_level(m_lead.group(2) or m_lead.group(5))
                cand_co = cls.normalize_co_code(m_lead.group(3) or m_lead.group(4))
                if cand_co and cand_bl:
                    marks = int(m_lead.group(1))
                    bloom_level = cand_bl
                    co_code = cand_co
                    marks_conf = 0.98
                    rest = m_lead.group(6).strip()
                    # Strip lingering topic prefix before real question action verb if present
                    rest = re.sub(
                        r"^[A-Za-z0-9\s,/\(\)\-_–—:]*?\b(?=(?:List|Explain|Encrypt|Using|Perform|Define|Calculate|Describe|What|Why|How|Determine|State|Write|Compare|Solve|Differentiate|Illustrate)\b)",
                        "",
                        rest,
                        flags=re.I,
                    ).strip(" -:–—")
                    if rest:
                        cleaned.append(rest)
                    i += 1
                    continue

            # 4. Single-line composite: e.g. "08 [1] K3", "08 [CO1] [K2]", "08 K3 CO1", "[5] CO1 K3"
            m_comp = re.search(
                r"\[?(\d{1,2})\s*(?:Marks?|M)?\]?\s+\[?(?:CO\s*)?([A-Za-z0-9_]+)\]?\s+\[?(K[1-6])\]?",
                curr,
                re.I,
            ) or re.search(
                r"\[?(\d{1,2})\s*(?:Marks?|M)?\]?\s+\[?(K[1-6])\]?\s+\[?(?:CO\s*)?([A-Za-z0-9_]+)\]?",
                curr,
                re.I,
            )
            if m_comp and marks is None:
                cand_co = cls.normalize_co_code(m_comp.group(2) if m_comp.lastindex == 3 and not m_comp.group(2).upper().startswith("K") else m_comp.group(3))
                cand_bl = cls.normalize_bloom_level(m_comp.group(3) if cand_co != m_comp.group(3) else m_comp.group(2))
                if not cand_co or not cand_bl:
                    cand_bl = cls.normalize_bloom_level(m_comp.group(2))
                    cand_co = cls.normalize_co_code(m_comp.group(3))
                if cand_co and cand_bl:
                    marks = int(m_comp.group(1))
                    co_code = cand_co
                    bloom_level = cand_bl
                    marks_conf = 0.95
                    curr = (curr[: m_comp.start()] + " " + curr[m_comp.end() :]).strip()
                    if curr:
                        cleaned.append(curr)
                    i += 1
                    continue

            # 5. Standalone line marks only: "[16]", "[08]", "08 Marks", "5M", "[5]"
            if marks is None:
                m_mk_only = (
                    re.match(r"^\[\s*(\d{1,2})\s*(?:Marks?|M)?\s*\]$", curr, re.I)
                    or re.match(r"^\(\s*(\d{1,2})\s*(?:Marks?|M)?\s*\)$", curr, re.I)
                    or re.match(r"^(\d{1,2})\s*(?:Marks?|M)$", curr, re.I)
                )
                if m_mk_only:
                    marks = int(m_mk_only.group(1))
                    marks_conf = 0.92
                    i += 1
                    continue

            cleaned.append(curr)
            i += 1

        # 6. Trailing inline marks/metadata strip from final lines
        final_lines: List[str] = []
        for l in cleaned:
            # Inline trailing marks
            if marks is None:
                m_end_mk = (
                    re.search(r"\[\s*(\d{1,2})\s*(?:Marks?|M)?\s*\]\s*$", l, re.I)
                    or re.search(r"\(\s*(\d{1,2})\s*(?:Marks?|M)?\s*\)\s*$", l, re.I)
                    or re.search(r"\b(\d{1,2})\s*(?:Marks?|M)\s*$", l, re.I)
                )
                if m_end_mk:
                    marks = int(m_end_mk.group(1))
                    marks_conf = 0.90
                    l = l[: m_end_mk.start()].strip()

            # Clean trailing CO/Bloom or Bloom/CO tokens if remaining
            m_end_co_bl = re.search(
                r"\s*\[?(CO\s*\d+|[A-Za-z0-9_]+)\]?\s+\[?(K[1-6])\]?\s*$", l, re.I
            ) or re.search(
                r"\s*\[?(K[1-6])\]?\s+\[?(CO\s*\d+|[A-Za-z0-9_]+)\]?\s*$", l, re.I
            )
            if m_end_co_bl:
                cand_a = m_end_co_bl.group(1)
                cand_b = m_end_co_bl.group(2)
                if co_code is None:
                    co_code = cls.normalize_co_code(cand_a) or cls.normalize_co_code(cand_b)
                if bloom_level is None:
                    bloom_level = cls.normalize_bloom_level(cand_b) or cls.normalize_bloom_level(cand_a)
                l = l[: m_end_co_bl.start()].strip()

            if l:
                final_lines.append(l)

        return final_lines, marks, co_code, bloom_level, marks_conf

    @classmethod
    def parse_paper_detailed(cls, raw_text: str) -> Dict[str, Any]:
        """
        Parses raw text into structured question groups, questions, subquestions,
        filtered instructions, and metadata.
        """
        raw_text = raw_text or ""
        raw_lines = [l.strip() for l in raw_text.replace("\r\n", "\n").split("\n") if l.strip()]

        instructions: List[str] = []
        questions: List[Dict[str, Any]] = []
        question_groups: List[Dict[str, Any]] = []
        header_metadata: Dict[str, Any] = {}
        declared_total: Optional[int] = None
        detected_subject: Optional[str] = None

        declared_duration: Optional[int] = None
        # Detect declared total marks, duration & subject code in header lines across all lines
        for l in raw_lines:
            if declared_total is None:
                m_tot = re.search(r"Total\s*Marks\s*[:\-–—\s]+\s*(\d+)", l, re.I)
                if m_tot:
                    declared_total = int(m_tot.group(1))
            if detected_subject is None:
                # Subject code usually has numbers + 3+ letters + numbers, e.g. [2CSPC401], [CS301], [3CSPC201]
                m_sub = re.search(r"\[([0-9A-Z]{2,}[A-Z]+[0-9A-Z]*)\]", l)
                if m_sub and m_sub.group(1).upper() not in {"MSE", "ESE", "ISE", "CIE", "TH", "PR"} and not re.match(r"^K[1-6]$", m_sub.group(1), re.I) and not re.match(r"^\d+$", m_sub.group(1)):
                    detected_subject = m_sub.group(1)
            if declared_duration is None:
                m_range = re.search(
                    r"Time\s*[:\-–—\s]+\s*(\d{1,2})[:.](\d{2})\s*(AM|PM)\s*to\s*(\d{1,2})[:.](\d{2})\s*(AM|PM)",
                    l,
                    re.I,
                )
                if m_range:
                    h1, m1, p1, h2, m2, p2 = m_range.groups()
                    try:
                        t1 = datetime.strptime(f"{h1}:{m1} {p1.upper()}", "%I:%M %p")
                        t2 = datetime.strptime(f"{h2}:{m2} {p2.upper()}", "%I:%M %p")
                        diff_mins = int((t2 - t1).total_seconds() / 60)
                        if diff_mins > 0:
                            declared_duration = diff_mins
                    except Exception:
                        pass
                if declared_duration is None:
                    m_hrs = re.search(
                        r"(?:Time|Duration)\s*[:\-–—\s]+\s*(\d+(?:\.\d+)?)\s*(?:Hours?|Hrs?|H)\b",
                        l,
                        re.I,
                    )
                    if m_hrs:
                        declared_duration = int(float(m_hrs.group(1)) * 60)
                if declared_duration is None:
                    m_mins = re.search(
                        r"(?:Time|Duration)\s*[:\-–—\s]+\s*(\d+)\s*(?:Minutes?|Mins?|M)\b",
                        l,
                        re.I,
                    )
                    if m_mins:
                        declared_duration = int(m_mins.group(1))

        header_metadata["declared_total_marks"] = declared_total
        header_metadata["declared_duration_minutes"] = declared_duration
        header_metadata["subject_code_detected"] = detected_subject

        current_parent_num: Optional[str] = None
        current_q_num: Optional[str] = None
        current_sub_q: Optional[str] = None
        current_lines: List[str] = []
        current_raw_lines: List[str] = []
        current_section = "GENERAL"
        pending_is_choice = False
        is_choice = False
        seq = 1

        def flush():
            nonlocal current_q_num, current_sub_q, current_lines, current_raw_lines
            nonlocal is_choice, pending_is_choice, seq

            if not current_q_num or not current_lines:
                current_q_num = None
                current_sub_q = None
                current_lines = []
                current_raw_lines = []
                is_choice = False
                return

            clean_lines, marks, co, bl, mk_conf = cls.extract_metadata_and_clean(current_lines)
            q_text = " ".join(clean_lines).strip()
            raw_joined = " ".join(current_raw_lines).strip()

            # If the accumulated text is pure instruction, filter it out
            if not q_text or cls.is_instruction_text(q_text):
                if q_text and cls.is_instruction_text(q_text):
                    instructions.append(q_text)
                current_q_num = None
                current_sub_q = None
                current_lines = []
                current_raw_lines = []
                is_choice = False
                return

            # If previous question has the same question number (e.g. Q.1(b) and Q.1(b)), link them as an internal choice pair
            choice_id = (
                f"{current_parent_num or 'Q'}_{current_sub_q or 'sub'}_choice"
                if is_choice
                else None
            )
            if questions and questions[-1]["question_number"] == current_q_num:
                is_choice = True
                choice_id = f"{current_parent_num or 'Q'}_{current_sub_q or 'sub'}_choice"
                questions[-1]["internal_choice"] = True
                questions[-1]["choice_group_id"] = choice_id

            q_type = "SUBQUESTION" if current_sub_q else "QUESTION"

            parse_conf = 0.96 if marks is not None else 0.72

            questions.append(
                {
                    "question_number": current_q_num,
                    "original_number": current_q_num,
                    "sub_question": current_sub_q,
                    "parent_number": current_parent_num,
                    "question_text": q_text,
                    "original_text": raw_joined,
                    "raw_text": raw_joined,
                    "normalized_text": q_text,
                    "marks": marks,
                    "co_code": co,
                    "bloom_level": bl,
                    "internal_choice": bool(is_choice),
                    "choice_group_id": choice_id,
                    "section_name": current_section,
                    "question_type": q_type,
                    "sequence_order": seq,
                    "parse_confidence": round(parse_conf, 2),
                    "marks_confidence": round(mk_conf, 2) if marks is not None else None,
                    "metadata_confidence": 0.95 if (co or bl) else (0.75 if marks is not None else 0.5),
                }
            )
            seq += 1
            current_q_num = None
            current_sub_q = None
            current_lines = []
            current_raw_lines = []
            is_choice = False

        for line in raw_lines:
            low = line.lower().strip()

            # Page break / separator
            if (
                "[next page]" in low
                or low.startswith("--- page")
                or low.startswith("=== page")
            ):
                flush()
                continue

            # Skip table headers
            if low in cls.TABLE_HEADERS:
                continue

            # General instructions
            if cls.is_instruction_text(line):
                flush()
                instructions.append(line)
                continue

            # Institutional headers / footers
            if cls.is_header_or_footer(line):
                continue

            # Section headers
            sec_m = re.match(
                r"^(?:SECTION|PART)\s*[\-–—]?\s*([A-Z0-9]+)|^Unit\s+No\.?\s*(\d+)",
                line,
                re.I,
            )
            if sec_m:
                flush()
                sec_name = sec_m.group(1) or f"Unit {sec_m.group(2)}"
                current_section = (
                    f"SECTION {sec_name.upper()}"
                    if not sec_name.upper().startswith("UNIT")
                    else sec_name.upper()
                )
                current_parent_num = None
                continue

            # Internal choice indicator
            if line.upper() in {"OR", "-- OR --", "[OR]", "OR:", "-OR-"}:
                flush()
                pending_is_choice = True
                continue

            # Inline subquestion: Q.1(a) / Q1(a) / 1(a)
            inline_m = re.match(
                r"^(?:Q(?:uestion)?\s*[\.\-]?\s*)?(\d+)\s*[\.\-]?\s*\(?([a-h])\)\s*(.*)$",
                line,
                re.I,
            )
            if inline_m:
                flush()
                p_idx = inline_m.group(1)
                s_char = inline_m.group(2).lower()
                rest = (inline_m.group(3) or "").strip()
                current_parent_num = f"Q.{p_idx}"
                current_sub_q = s_char
                current_q_num = f"Q.{p_idx}({s_char})"
                is_choice = pending_is_choice
                pending_is_choice = False
                current_raw_lines = [line]
                current_lines = [rest] if rest else []
                continue

            # Group Header: Q. 1 / Q1 / Question 1 (not followed by inline subquestion)
            g_m = re.match(
                r"^Q(?:uestion)?\s*[\.\-]?\s*(\d+)\s*[:.\-]?\s*(.*)$", line, re.I
            )
            if g_m and not re.match(r"^\(?([a-h])\)", g_m.group(2).strip(), re.I):
                flush()
                g_num = g_m.group(1)
                g_rest = g_m.group(2).strip()
                current_parent_num = f"Q.{g_num}"
                current_sub_q = None

                m_tot = re.search(r"\[\s*(\d+)\s*\]", g_rest)
                grp_marks = int(m_tot.group(1)) if m_tot else None
                rest_clean = re.sub(r"\[\s*\d+\s*\]", "", g_rest).strip(" .-:")

                is_group_header = (
                    not rest_clean
                    or re.match(r"^(?:solve|answer|attempt|write)\b", rest_clean, re.I)
                    or not any(
                        verb in rest_clean.lower()
                        for verb in [
                            "explain",
                            "define",
                            "derive",
                            "calculate",
                            "compare",
                            "apply",
                            "what",
                            "illustrate",
                        ]
                    )
                )

                if is_group_header:
                    full_title = f"{current_parent_num} {g_rest}".strip()
                    question_groups.append(
                        {
                            "group_number": current_parent_num,
                            "group_total_marks": grp_marks,
                            "question_number": current_parent_num,
                            "original_number": current_parent_num,
                            "sub_question": None,
                            "parent_number": None,
                            "question_text": full_title or current_parent_num,
                            "original_text": line,
                            "raw_text": line,
                            "normalized_text": full_title or current_parent_num,
                            "marks": grp_marks,
                            "co_code": None,
                            "bloom_level": None,
                            "internal_choice": False,
                            "choice_group_id": None,
                            "section_name": current_section,
                            "question_type": "QUESTION_GROUP",
                            "sequence_order": 0,
                            "parse_confidence": 0.98,
                            "marks_confidence": 0.95 if grp_marks is not None else None,
                            "metadata_confidence": 0.9,
                        }
                    )
                    current_q_num = None
                    current_lines = []
                    current_raw_lines = []
                    continue
                else:
                    # Standalone question e.g. "Q.1 Explain digital signature [10]"
                    current_q_num = current_parent_num
                    is_choice = pending_is_choice
                    pending_is_choice = False
                    current_raw_lines = [line]
                    current_lines = [g_rest]
                    continue

            # Subquestion: a) / (a) / b) under an active parent group
            sub_m = re.match(r"^\(?([a-h])\)\s*(.*)$", line, re.I)
            if sub_m and current_parent_num:
                flush()
                sub_char = sub_m.group(1).lower()
                rest = sub_m.group(2).strip()
                current_sub_q = sub_char
                current_q_num = f"{current_parent_num}({sub_char})"
                is_choice = pending_is_choice
                pending_is_choice = False
                current_raw_lines = [line]
                current_lines = [rest] if rest else []
                continue

            # Standalone numbered 1) All questions... before first parent -> instruction
            n_m = re.match(r"^(\d+)\s*[\.\)]\s*(.*)$", line)
            if n_m and not current_parent_num:
                rest = n_m.group(2).strip()
                if cls.is_instruction_text(rest) or not any(
                    verb in rest.lower()
                    for verb in [
                        "explain",
                        "define",
                        "calculate",
                        "solve",
                        "what",
                        "how",
                        "apply",
                        "derive",
                    ]
                ):
                    flush()
                    instructions.append(line)
                    continue

            # Total marks declared below question group e.g. "[16]"
            if question_groups and re.match(r"^\[\s*(\d+)\s*\]$", line) and not current_q_num:
                if question_groups[-1]["marks"] is None:
                    m_val = int(re.match(r"^\[\s*(\d+)\s*\]$", line).group(1))
                    question_groups[-1]["marks"] = m_val
                    question_groups[-1]["group_total_marks"] = m_val
                continue

            # Group title continuation line e.g. "Solve the following questions"
            if question_groups and not current_q_num and not current_parent_num:
                if re.match(r"^(?:solve|answer|attempt|write)\b", line, re.I):
                    question_groups[-1]["question_text"] = (
                        question_groups[-1]["question_text"] + " " + line
                    ).strip()
                    continue

            # Accumulate question line
            if current_q_num:
                current_lines.append(line)
                current_raw_lines.append(line)

        flush()

        # Combine question_groups and questions for all_items
        all_items = question_groups + questions

        def sort_key(x: Dict[str, Any]) -> Tuple[int, int, str, int]:
            m = re.search(r"(\d+)", x.get("question_number", ""))
            maj = int(m.group(1)) if m else 99
            rank = 0 if x.get("question_type") == "QUESTION_GROUP" else 1
            sub = x.get("sub_question") or ""
            return (maj, rank, sub, x.get("sequence_order", 0))

        all_items.sort(key=sort_key)
        for i, item in enumerate(all_items, 1):
            item["sequence_order"] = i

        analyzable = [
            q for q in all_items if q.get("question_type") in ("QUESTION", "SUBQUESTION")
        ]

        normalized_text = "\n".join(
            [
                f"[{q['question_number']}] (Marks: {q['marks'] if q['marks'] is not None else 'None'}, "
                f"CO: {q.get('co_code') or 'None'}, Bloom: {q.get('bloom_level') or 'None'}) "
                f"{q['question_text']}"
                for q in analyzable
            ]
        )

        return {
            "declared_total_marks": declared_total,
            "declared_duration_minutes": declared_duration,
            "subject_code_detected": detected_subject,
            "instructions": instructions,
            "question_groups": question_groups,
            "questions": analyzable,
            "all_items": all_items,
            "header_metadata": header_metadata,
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "parse_warnings": (
                ["No examination questions could be reliably extracted from this document."]
                if not analyzable
                else []
            ),
        }

    @classmethod
    def parse_paper(cls, raw_text: str) -> List[Dict[str, Any]]:
        detailed = cls.parse_paper_detailed(raw_text)
        return detailed["questions"]

    @classmethod
    def parse_extracted_text(cls, raw_text: str) -> List[Dict[str, Any]]:
        return cls.parse_paper(raw_text)

    @classmethod
    def parse_questions(cls, raw_text: str) -> List[Dict[str, Any]]:
        return cls.parse_paper(raw_text)

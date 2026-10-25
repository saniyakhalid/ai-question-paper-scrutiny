"""
Syllabus Import & Subject-Isolated Curriculum Management API
Allows faculty to preview and import searchable syllabus documents (PDF/DOCX/TXT),
extracts course outcomes, units, topics, and subject metadata, and isolates them per subject.
"""

import os
import re
import tempfile
import uuid
from mimetypes import guess_type
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING

from app.core.config import settings
from app.db.mongo import get_db, serialize_doc, serialize_docs, get_next_sequence
from app.core.dependencies import get_current_user, require_role, MongoUser
from app.services.extraction_service import DocumentExtractionService
from app.services.audit_service import AuditService

router = APIRouter(tags=["Syllabus Management"])

SYLLABUS_UPLOAD_DIR = os.path.join(settings.UPLOAD_DIR, "syllabus")
os.makedirs(SYLLABUS_UPLOAD_DIR, exist_ok=True)


def _public_syllabus_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """Return document metadata without exposing the server's local file path."""
    public_document = serialize_doc(document)
    public_document.pop("file_path", None)
    return public_document


def parse_syllabus_text(text: str) -> Dict[str, Any]:
    """
    Extract syllabus fields (metadata, course outcomes, units, topics)
    robustly from both Word (.docx) table layouts, plain text, and PDF OCR extracts.
    """
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    metadata: Dict[str, Any] = {}
    roman_map = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
        "XI": 11, "XII": 12, "V11": 7, "V1": 6, "1V": 4, "1X": 9, "V111": 8
    }

    filtered_lines = lines

    # 1. Subject Metadata Extraction
    metadata_patterns = {
        "code": r"^(?:subject|course|paper)\s*(?:code|no\.?|number)\s*[:|\-]\s*([A-Z0-9][A-Z0-9./_-]{2,})\b",
        "name": r"^(?:subject|course|paper)\s*(?:name|title)\s*[:|\-]\s*(.{3,100})$",
        "department": r"^(?:department|dept\.?|faculty)\s*[:|\-]\s*(.{2,100})$",
        "branch": r"^(?:branch|program(?:me)?|degree)\s*[:|\-]\s*(.{2,100})$",
        "academic_year": r"^(?:academic\s*year|a\.y\.)\s*[:|\-]\s*((?:20)?\d{2}\s*[-–/]\s*(?:20)?\d{2})\b",
    }

    for i, line in enumerate(filtered_lines):
        # Combined course code and title e.g. "Course Code and Course Title | 2CSPC401: Information & Network"
        comb_match = re.match(
            r"^(?:Course\s*Code\s*and\s*(?:Course\s*)?Title|Subject\s*Code\s*and\s*(?:Subject\s*)?Name)\s*[:|\-]\s*([A-Z0-9_-]+)\s*[:|\-]\s*(.+)$",
            line,
            re.I
        )
        if comb_match:
            if "code" not in metadata:
                metadata["code"] = comb_match.group(1).strip()
            if "name" not in metadata:
                cand_name = comb_match.group(2).strip(" -:|")
                # Lookahead for name continuation on next line (e.g. "Security")
                if i + 1 < len(filtered_lines):
                    next_l = filtered_lines[i + 1]
                    if len(next_l) < 40 and not any(k in next_l.lower() for k in [":", "|", "pre", "teach", "credit", "eval", "unit"]):
                        cand_name += f" {next_l.strip()}"
                metadata["name"] = cand_name

        syl_match = re.match(r"^Syllabus\s*[:|\-]\s*(.+)$", line, re.I)
        if syl_match and "name" not in metadata:
            cand = syl_match.group(1).strip(" -:|")
            if len(cand) > 3 and not cand.lower().startswith(("of ", "for ")):
                metadata["name"] = cand

        for key, pattern in metadata_patterns.items():
            match = re.match(pattern, line, re.I)
            if match and key not in metadata:
                metadata[key] = match.group(1).strip(" .;|")

        sem_inline = re.search(r"\b(?:semester|sem\.?|term)\s*[-:]?\s*([IVX0-9]+)\b", line, re.I)
        if sem_inline and "semester" not in metadata:
            sem_token = sem_inline.group(1).upper()
            sem_val = roman_map.get(sem_token)
            if sem_val is None:
                norm_token = re.sub(r"(?<=[IVX])1", "I", sem_token)
                norm_token = re.sub(r"1(?=[IVX])", "I", norm_token)
                sem_val = roman_map.get(norm_token, int(sem_token) if sem_token.isdigit() else None)
            if sem_val:
                metadata["semester"] = sem_val

        # Branch (prevent false match on English word 'be', allow OCR joined words like YearB.Tech)
        branch_inline = re.search(r"(?:^|\b|[A-Za-z])(B\.?Tech(?:\.?[A-Za-z ]*)?|M\.?Tech|B\.E\.|Diploma)\b", line, re.I)
        if branch_inline and "branch" not in metadata:
            clean_branch = re.sub(r"Sem.*$", "", branch_inline.group(1), flags=re.I).strip(" .")
            if clean_branch:
                metadata["branch"] = clean_branch

        # Evaluation Scheme Marks e.g. "Evaluation Scheme Theory: ISE/MSE/ESE | 40/30/30"
        if not any(w in line.lower() for w in ["teaching", "lecture", "tutorial"]):
            scheme_eval = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\s*/\s*(\d{2,3})\b", line)
            if scheme_eval and "total_marks" not in metadata and any(w in line.lower() for w in ["evaluation", "scheme", "ise", "mse", "ese", "theory", "marks"]):
                try:
                    s = sum(int(x) for x in scheme_eval.groups())
                    if s >= 20:
                        metadata["total_marks"] = s
                except Exception:
                    pass

        marks_match = re.match(
            r"^(?:total\s*(?:marks|marks?\s*of\s*examination)|maximum\s*marks|max\.?\s*marks|exam(?:ination)?\s*marks)\s*[:|\-]?\s*(\d{1,3})\b",
            line,
            re.I,
        )
        if marks_match and "total_marks" not in metadata:
            metadata["total_marks"] = int(marks_match.group(1))

        duration_match = re.match(
            r"^(?:exam(?:ination)?\s*duration|duration|time\s*allowed|time)\s*[:|\-]?\s*(\d{1,3})\s*(?:minutes?|mins?|min\.?)?\b",
            line,
            re.I,
        )
        if duration_match and "duration_minutes" not in metadata:
            metadata["duration_minutes"] = int(duration_match.group(1))
        hours_match = re.match(
            r"^(?:exam(?:ination)?\s*duration|duration|time\s*allowed)\s*[:|\-]?\s*(\d(?:\.\d)?)\s*(?:hours?|hrs?)\b",
            line,
            re.I,
        )
        if hours_match and "duration_minutes" not in metadata:
            metadata["duration_minutes"] = int(float(hours_match.group(1)) * 60)

        # Header match: "2CSPC401 Information & Network Security"
        header_match = re.match(r"^([A-Z0-9][A-Z0-9_-]*\d[A-Z0-9_-]*)\s+[-:|]?\s+([A-Z][A-Z0-9 &()/,-]{3,80})$", line)
        if header_match and "code" not in metadata and not re.match(r"^(?:UNIT|MODULE|CO\d)", line, re.I):
            metadata["code"] = header_match.group(1).strip()
            metadata.setdefault("name", header_match.group(2).strip(" -:|"))

        # Colon match e.g. 2CSPC401:Information&Network
        colon_m = re.match(r"^([A-Z0-9][A-Z0-9_-]*\d[A-Z0-9_-]*)\s*:\s*([A-Za-z0-9\s&/,-]{3,80})$", line)
        if colon_m and "code" not in metadata and not re.match(r"^(?:UNIT|MODULE|CO\d)", line, re.I):
            metadata["code"] = colon_m.group(1).strip()
            cname = colon_m.group(2).strip(" -:|")
            if i + 2 < len(filtered_lines):
                for step in [1, 2]:
                    next_l = filtered_lines[i + step]
                    if len(next_l) < 30 and not any(k in next_l.lower() for k in [":", "|", "pre", "teach", "credit", "eval", "unit", "course code"]):
                        cname += " " + next_l.strip()
                        break
            metadata["name"] = cname

    # Sensible defaults & department inference
    if not metadata.get("total_marks"):
        metadata["total_marks"] = 100
    if not metadata.get("duration_minutes"):
        metadata["duration_minutes"] = 180
    if not metadata.get("department"):
        combined_text = (metadata.get("name", "") + " " + metadata.get("code", "") + " " + metadata.get("branch", "")).lower()
        if any(k in combined_text for k in ["computer", "cse", "security", "cspc", "learning", "data"]):
            metadata["department"] = "Computer Science & Engineering"
        elif metadata.get("branch"):
            metadata["department"] = metadata.get("branch")

    # 2. Extract Course Outcomes
    outcomes: List[Dict[str, str]] = []
    in_outcome_section = False
    co_single_line_re = re.compile(
        r"^(?:(?:[A-Z0-9_-]+[\s_.-])?(?:CO\s*[-.]?\s*(\d+)|([A-Z0-9_-]{2,})[\s_.]([0-9]+))|Course\s+Outcome\s*[-.]?\s*(\d+)|CO(\d+))\s*[:.\-–|]\s*(.*)$",
        re.I
    )
    co_label_only_re = re.compile(
        r"^(?:(?:[A-Z0-9_-]+[\s_.-])?CO\s*[-.]?\s*(\d+)|([A-Z0-9_-]+)[\s_.-](\d{1,2})|CO(\d{1,2}))\s*$",
        re.I
    )
    non_outcome_section = re.compile(
        r"^(?:course\s+contents?|syllabus\s*contents?|unit\s*(?:no|name)|list\s+of\s+practical|text\s*books?|reference\s*books?)",
        re.I
    )

    known_code = metadata.get("code", "")
    pending_co_num: Optional[str] = None

    for line in filtered_lines:
        if re.search(r"\b(?:course\s+outcomes?|program(?:me)?\s+outcomes?)\b", line, re.I):
            in_outcome_section = True
            continue
        if non_outcome_section.match(line):
            in_outcome_section = False
            pending_co_num = None

        if pending_co_num is not None:
            desc = re.sub(r"\s*\|\s*\d+\s*(?:hrs?|hours?).*$", "", line, flags=re.I).strip(" .;:-–|")
            if len(desc) > 5 and not co_label_only_re.match(desc) and not non_outcome_section.match(desc):
                code = f"CO{pending_co_num}"
                if not any(o["co_code"].casefold() == code.casefold() for o in outcomes):
                    outcomes.append({"co_code": code, "description": desc})
                pending_co_num = None
                continue
            pending_co_num = None

        # Check single-line CO e.g. "2CSPC401 1 | Analyze the OSI..." or "CO1: ..."
        m = co_single_line_re.match(line)
        if m:
            num = m.group(1) or m.group(3) or m.group(4) or m.group(5)
            desc = m.group(6).strip(" .;:-–|")
            desc = re.sub(r"\s*\|\s*\d+\s*(?:hrs?|hours?).*$", "", desc, flags=re.I).strip(" .;:-–|")
            desc = re.sub(r"\s*\|\s*K[1-6].*$", "", desc, flags=re.I).strip(" .;:-–|")
            if num and len(desc) > 5:
                code = f"CO{num}"
                if not any(o["co_code"].casefold() == code.casefold() for o in outcomes):
                    outcomes.append({"co_code": code, "description": desc})
            continue

        if in_outcome_section:
            # Check numbered outcome: "1 | Analyze..." or "1. Analyze..." or "1) Analyze..."
            num_match = re.match(r"^(\d{1,2})\s*[:.\-–|)]\s*(.{8,})$", line)
            if num_match:
                num, desc = num_match.groups()
                desc = re.sub(r"\s*\|\s*\d+\s*(?:hrs?|hours?).*$", "", desc, flags=re.I).strip(" .;:-–|")
                code = f"CO{num}"
                if not any(o["co_code"].casefold() == code.casefold() for o in outcomes):
                    outcomes.append({"co_code": code, "description": desc})
                continue

            # Check label-only line e.g. "2CSPC401 1" or "2CSPC4011"
            if known_code and line.startswith(known_code):
                rest = line[len(known_code):].strip(" _-.")
                if rest.isdigit() and len(rest) <= 2:
                    pending_co_num = rest
                    continue

            # Fallback: check if line ends with a digit in outcome section
            if len(line) <= 15 and re.search(r"(\d{1,2})$", line):
                end_num = re.search(r"(\d{1,2})$", line).group(1)
                if int(end_num) in range(1, 13):
                    pending_co_num = end_num
                    continue

            label_match = co_label_only_re.match(line)
            if label_match:
                pending_co_num = label_match.group(1) or label_match.group(3) or label_match.group(4)
                continue

    # 3. Extract Units and Topics
    unit_blocks: List[Dict[str, Any]] = []
    current_block: Optional[Dict[str, Any]] = None
    in_contents = False
    units_section_completed = False

    unit_header_re = re.compile(
        r"^(?:unit|module|chapter)\s*[-:]?\s*(?:no\.?)?\s*([IVXLCDM]+|\d+)\s*[:.\-–|]?\s*(.*)$",
        re.I
    )
    unit_table_re = re.compile(
        r"^([1-9]|1[0-2]|[IVX]{1,4})\s*\|\s*([^|]+?)(?:\s*[:.\-–])?(?:\s*\|\s*.*)?$",
        re.I
    )
    end_contents_re = re.compile(
        r"^(?:list\s+of\s+practical|practical(?:s|\s+list)|text\s*books?|reference\s*books?|evaluation\s+scheme|assignments?|audit\s+course)",
        re.I
    )
    ocr_colon_title_re = re.compile(r"^([A-Z][A-Za-z0-9\s,&/\-–]+)\s*:\s*$", re.I)

    for line in filtered_lines:
        if re.search(r"\b(?:course\s*contents?|syllabus\s*contents?|unit\s*details?)\b", line, re.I):
            in_contents = True
            current_block = None
            continue

        if end_contents_re.match(line):
            in_contents = False
            current_block = None
            if unit_blocks:
                units_section_completed = True
            continue

        if units_section_completed:
            continue

        # Standard Unit header: "Unit 1: Title"
        u_match = unit_header_re.match(line)
        if u_match:
            u_token = u_match.group(1).upper()
            u_num = roman_map.get(u_token) or (int(u_token) if u_token.isdigit() else None)
            if u_num:
                title = u_match.group(2).strip(" .;:-–|")
                current_block = {"unit_number": u_num, "title": title, "raw_lines": []}
                unit_blocks.append(current_block)
                continue

        # Table-row unit: "1 | Introduction to Cryptography :"
        t_match = unit_table_re.match(line)
        if t_match:
            cand_title = t_match.group(2).strip(" .;:-–|")
            if not any(k in cand_title.lower() for k in ["unit name", "contact hour", "title of experiment", "author", "publisher", "sr.", "course title"]):
                u_token = t_match.group(1).upper()
                u_num = roman_map.get(u_token) or (int(u_token) if u_token.isdigit() else None)
                if u_num:
                    current_block = {"unit_number": u_num, "title": cand_title, "raw_lines": []}
                    unit_blocks.append(current_block)
                    continue

        # OCR colon title
        if in_contents:
            colon_m = ocr_colon_title_re.match(line)
            if colon_m and not any(k in line.lower() for k in ["scheme", "teaching", "credits", "lecture", "hrs", "hours"]):
                cand_title = colon_m.group(1).strip()
                if not any(k in cand_title.lower() for k in ["unit", "module", "text books", "reference", "course outcomes", "prerequisite"]):
                    u_num = len(unit_blocks) + 1
                    current_block = {"unit_number": u_num, "title": cand_title, "raw_lines": []}
                    unit_blocks.append(current_block)
                    continue

        if current_block:
            if any(k in line.lower() for k in ["contact hour", "unit name", "course contents", "no | unit"]):
                continue
            current_block["raw_lines"].append(line)

    units: List[Dict[str, Any]] = []
    seen_units = set()
    for blk in unit_blocks:
        u_num = blk["unit_number"]
        if u_num in seen_units:
            continue
        seen_units.add(u_num)

        title = blk["title"]
        topics: List[Dict[str, str]] = []

        cleaned_lines = []
        for l in blk["raw_lines"]:
            c = re.sub(r"\s*\|\s*\d+\s*(?:hrs?|hours?).*$", "", l, flags=re.I)
            c = re.sub(r"\b\d+\s*(?:hrs?|hours?)\.?$", "", c, flags=re.I)
            c = re.sub(r"[\uFFFD\u200B\u200C\u200D]", " ", c)
            c = re.sub(r"^[-*•▪\u2022\d]+[.)]?\s*", "", c).strip(" .;:-–|")
            if len(c) > 2 and not c.lower().startswith(("course outcome", "unit ", "module ")):
                cleaned_lines.append(c)

        joined_text = " ".join(cleaned_lines)
        parts = [p.strip() for p in re.split(r"[,;]\s*(?=[A-Z0-9])", joined_text) if len(p.strip()) > 2]
        if not parts and joined_text.strip():
            parts = [joined_text.strip()]

        for p in parts:
            clean_p = re.sub(r"\s+", " ", p).strip(" .;:-–|")
            if len(clean_p) > 2 and not any(t["topic_name"].lower() == clean_p.lower() for t in topics):
                topics.append({"topic_name": clean_p[:200]})

        if not title:
            title = f"Unit {u_num}"

        units.append({
            "unit_number": u_num,
            "title": title,
            "description": "\n".join(t["topic_name"] for t in topics),
            "topics": topics
        })

    return {
        "metadata": metadata,
        "course_outcomes": outcomes,
        "units": sorted(units, key=lambda item: item["unit_number"]),
        "warnings": ["No unit headings were recognized in this file."] if not units else [],
    }


async def _extract_syllabus_upload(file: UploadFile) -> tuple[str, str, str, Dict[str, Any]]:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="Supported syllabus formats are searchable PDF, DOCX, and TXT.")
    content = await file.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The selected syllabus file is empty.")
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Syllabus files must be {settings.MAX_UPLOAD_SIZE_MB} MB or smaller.")

    safe_filename = os.path.basename((file.filename or "syllabus").replace("\\", "/")) or "syllabus"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, dir=SYLLABUS_UPLOAD_DIR, delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(content)
        raw_text = DocumentExtractionService.extract_text(temp_path, ext.lstrip("."))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not read syllabus text: {exc}") from exc
    finally:
        if temp_path and os.path.isfile(temp_path):
            os.remove(temp_path)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="No readable text was found in the syllabus file.")
    return ext.lstrip("."), safe_filename, raw_text, parse_syllabus_text(raw_text)


@router.post("/subjects/syllabus/preview")
async def preview_subject_syllabus(
    file: UploadFile = File(...),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"])),
):
    """Extract subject metadata, units, topics, and outcomes without saving the file."""
    _ext, filename, raw_text, parsed = await _extract_syllabus_upload(file)
    return {
        "filename": filename,
        "metadata": parsed["metadata"],
        "units": parsed["units"],
        "course_outcomes": parsed["course_outcomes"],
        "units_extracted": len(parsed["units"]),
        "course_outcomes_extracted": len(parsed["course_outcomes"]),
        "text_characters": len(raw_text),
        "warnings": parsed["warnings"],
    }


@router.post("/subjects/{subject_id}/syllabus/upload")
async def upload_subject_syllabus(
    subject_id: int,
    file: UploadFile = File(...),
    academic_year: Optional[str] = Form(None),
    replace_existing: bool = Form(True),
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN"]))
):
    """
    Upload official syllabus file for a specific subject.
    Extracts text, parses units & topics, and populates MongoDB subject syllabus.
    Strictly isolated: Cannot bleed into other subjects.
    """
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    ext, safe_filename, raw_text, parsed = await _extract_syllabus_upload(file)

    subj_dir = os.path.join(SYLLABUS_UPLOAD_DIR, f"subject_{subject_id}")
    os.makedirs(subj_dir, exist_ok=True)
    saved_path = os.path.join(subj_dir, f"{uuid.uuid4().hex}_{safe_filename}")

    await file.seek(0)
    with open(saved_path, "wb") as buffer:
        buffer.write(await file.read())
    if not os.path.getsize(saved_path):
        os.remove(saved_path)
        raise HTTPException(status_code=400, detail="The selected syllabus file is empty.")

    resolved_year = (academic_year or parsed["metadata"].get("academic_year") or subject.get("academic_year") or "").strip() or None

    # Apply extracted subject metadata from the syllabus file (real values only).
    subject_updates: Dict[str, Any] = {}
    metadata = parsed.get("metadata") or {}
    for key in ("name", "department", "branch", "academic_year"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            subject_updates[key] = value.strip()
    if metadata.get("semester"):
        try:
            subject_updates["semester"] = int(metadata["semester"])
        except (TypeError, ValueError):
            pass
    if metadata.get("total_marks"):
        try:
            subject_updates["total_marks"] = int(metadata["total_marks"])
        except (TypeError, ValueError):
            pass
    if metadata.get("duration_minutes"):
        try:
            subject_updates["duration_minutes"] = int(metadata["duration_minutes"])
        except (TypeError, ValueError):
            pass
    if resolved_year:
        subject_updates["academic_year"] = resolved_year
    if subject_updates:
        db.subjects.update_one({"id": subject_id}, {"$set": subject_updates})
        pattern_updates = {}
        if "total_marks" in subject_updates:
            pattern_updates["total_marks"] = subject_updates["total_marks"]
        if "duration_minutes" in subject_updates:
            pattern_updates["duration_minutes"] = subject_updates["duration_minutes"]
            pattern_updates["exam_duration_mins"] = subject_updates["duration_minutes"]
        if pattern_updates:
            db.examination_patterns.update_one({"subject_id": subject_id}, {"$set": pattern_updates})

    # Save document record
    doc_id = get_next_sequence("syllabus_documents")
    doc_record = {
        "id": doc_id,
        "subject_id": subject_id,
        "filename": safe_filename,
        "file_path": saved_path,
        "file_type": ext,
        "academic_year": resolved_year,
        "uploaded_by_id": current_user.id,
        "uploaded_by_name": current_user.full_name,
        "unit_count": len(parsed["units"]),
        "co_count": len(parsed["course_outcomes"]),
        "raw_text_length": len(raw_text),
    }
    db.syllabus_documents.insert_one(doc_record)

    # Replace only sections that were recognized. An unfamiliar file layout must not
    # delete existing curriculum or trigger fabricated unit placeholders.
    if replace_existing and parsed["units"]:
        existing_unit_ids = [unit.get("id") for unit in db.syllabus_units.find({"subject_id": subject_id})]
        if existing_unit_ids:
            db.syllabus_topics.delete_many({"unit_id": {"$in": existing_unit_ids}})
        db.syllabus_units.delete_many({"subject_id": subject_id})
    if replace_existing and parsed["course_outcomes"]:
        db.course_outcomes.delete_many({"subject_id": subject_id})

    # Insert newly parsed units
    created_units = []
    for u in parsed["units"]:
        u_id = get_next_sequence("syllabus_units")
        u_record = {
            "id": u_id,
            "subject_id": subject_id,
            "unit_number": u["unit_number"],
            "title": u["title"],
            "description": u.get("description", ""),
            "topics": []
        }
        # Keep embedded topics complete so the subject workspace can render and edit them.
        for t in u.get("topics", []):
            t_id = get_next_sequence("syllabus_topics")
            topic_record = {
                "id": t_id,
                "unit_id": u_id,
                "topic_name": t.get("topic_name", ""),
                "description": "",
                "co_id": None
            }
            db.syllabus_topics.insert_one(topic_record)
            u_record["topics"].append(topic_record)
        db.syllabus_units.insert_one(u_record)
        created_units.append(u_record)

    # Insert newly parsed COs if available
    created_cos = []
    for c in parsed["course_outcomes"]:
        c_id = get_next_sequence("course_outcomes")
        c_record = {
            "id": c_id,
            "subject_id": subject_id,
            "co_code": c["co_code"],
            "description": c["description"]
        }
        db.course_outcomes.insert_one(c_record)
        created_cos.append(c_record)

    AuditService.log_action(
        db,
        action="SYLLABUS_UPLOAD",
        entity="SyllabusDocument",
        entity_id=doc_id,
        user_id=current_user.id,
        user_role=current_user.role,
        metadata={
            "subject_code": subject.get("code"),
            "subject_name": subject.get("name"),
            "units_extracted": len(created_units),
            "cos_extracted": len(created_cos)
        },
        details=f"Syllabus uploaded for {subject.get('code')} ({len(created_units)} units, {len(created_cos)} COs)"
    )

    return {
        "ok": True,
        "message": f"Syllabus successfully uploaded and processed for {subject.get('code')}.",
        "document": _public_syllabus_document(doc_record),
        "units_extracted": len(created_units),
        "course_outcomes_extracted": len(created_cos),
        "metadata_extracted": parsed["metadata"],
        "warnings": parsed["warnings"],
        "units": serialize_docs(created_units),
        "course_outcomes": serialize_docs(created_cos)
    }


@router.get("/subjects/{subject_id}/syllabus/status")
def get_subject_syllabus_status(
    subject_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    """Returns syllabus upload status and parsed curriculum breakdown for a subject."""
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    docs = list(db.syllabus_documents.find({"subject_id": subject_id}).sort("id", DESCENDING))
    units = list(db.syllabus_units.find({"subject_id": subject_id}).sort("unit_number", ASCENDING))
    cos = list(db.course_outcomes.find({"subject_id": subject_id}))

    return {
        "subject": {
            "id": subject.get("id"),
            "code": subject.get("code"),
            "name": subject.get("name"),
            "branch": subject.get("branch"),
            "semester": subject.get("semester"),
        },
        "has_uploaded_syllabus": len(docs) > 0,
        "documents": [_public_syllabus_document(doc) for doc in docs],
        "unit_count": len(units),
        "co_count": len(cos),
        "units": serialize_docs(units),
        "course_outcomes": serialize_docs(cos)
    }


@router.get("/subjects/{subject_id}/syllabus/documents/{doc_id}/download")
def download_syllabus_document(
    subject_id: int,
    doc_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """Allow signed-in faculty, moderators, and admins to view uploaded syllabi."""
    doc = db.syllabus_documents.find_one({"id": doc_id, "subject_id": subject_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Syllabus document not found")

    file_path = os.path.realpath(doc.get("file_path", ""))
    upload_root = os.path.realpath(SYLLABUS_UPLOAD_DIR)
    try:
        is_within_upload_dir = os.path.commonpath([upload_root, file_path]) == upload_root
    except ValueError:
        is_within_upload_dir = False
    if not is_within_upload_dir or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Syllabus file is unavailable")

    filename = doc.get("filename") or os.path.basename(file_path)
    return FileResponse(file_path, filename=filename, media_type=guess_type(filename)[0] or "application/octet-stream")


@router.delete("/subjects/{subject_id}/syllabus/documents/{doc_id}")
def delete_syllabus_document(
    subject_id: int,
    doc_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "MODERATOR", "ADMIN"]))
):
    """Deletes an uploaded syllabus document."""
    doc = db.syllabus_documents.find_one({"id": doc_id, "subject_id": subject_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Syllabus document not found")
    if current_user.role == "FACULTY" and doc.get("uploaded_by_id") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only remove syllabus documents that you uploaded")

    file_path = os.path.realpath(doc.get("file_path") or "")
    upload_root = os.path.realpath(SYLLABUS_UPLOAD_DIR)
    try:
        is_within_upload_dir = os.path.commonpath([upload_root, file_path]) == upload_root
    except ValueError:
        is_within_upload_dir = False
    if is_within_upload_dir and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    db.syllabus_documents.delete_one({"id": doc_id, "subject_id": subject_id})

    AuditService.log_action(
        db,
        action="SYLLABUS_DELETE",
        entity="SyllabusDocument",
        entity_id=doc_id,
        user_id=current_user.id,
        user_role=current_user.role,
        details=f"Deleted syllabus document #{doc_id} for subject #{subject_id}"
    )

    return {"ok": True, "message": "Syllabus document deleted successfully."}

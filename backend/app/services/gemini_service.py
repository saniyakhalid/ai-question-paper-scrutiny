import json
import logging
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.grammar_service import GrammarAnalysisService

logger = logging.getLogger(__name__)

class AIQuestionAnalysis(BaseModel):
    question_number: str
    bloom_level: Optional[str] = None
    co_code: Optional[str] = None
    unit_number: Optional[int] = None
    topic_name: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reasoning: str = ""
    grammar_status: str = "NOT_EVALUATED"
    quality_status: str = "NOT_EVALUATED"
    suggested_improvement: Optional[str] = None
    issues: Optional[List[Dict[str, Any]]] = None

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.ai_provider = (settings.AI_PROVIDER or "mock").lower()

    @classmethod
    def generate_json_completion(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """Legacy helper for backward-compatibility with older service calls."""
        service = GeminiService()
        return service._generate_structured_json(prompt, fallback_dict={}, max_retries=1)

    def _call_gemini_raw(self, prompt: str) -> str:
        """Invokes Google Gemini API safely and returns response text."""
        if self.ai_provider == "mock" or not self.api_key:
            raise ValueError("AI_PROVIDER is set to mock or GEMINI_API_KEY is missing.")

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.warning("Gemini API call failed; details omitted from logs.")
            raise RuntimeError("Gemini API request failed.") from e

    def _generate_structured_json(self, prompt: str, fallback_dict: dict, max_retries: int = 2) -> dict:
        if self.ai_provider == "mock" or not self.api_key:
            return fallback_dict

        for attempt in range(max_retries):
            try:
                raw_text = self._call_gemini_raw(prompt)
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]

                parsed = json.loads(cleaned.strip())
                return parsed
            except Exception as e:
                logger.warning(f"Gemini response attempt {attempt+1} was not valid JSON; details omitted.")

        return fallback_dict

    def analyze_paper_questions(
        self,
        subject_code: str,
        subject_name: str,
        course_outcomes: List[Dict[str, Any]],
        syllabus_units: List[Dict[str, Any]],
        questions: List[Dict[str, Any]],
        selected_units: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Main semantic analysis pipeline for all questions in an uploaded question paper.
        Source of Truth Priority:
          1. Deterministic parser values (marks, printed CO, printed Bloom)
          2. Gemini semantic analysis
          3. Subject syllabus configuration
        """
        # Exclude general instructions or non-questions (already filtered by parser, but guard defensively)
        valid_questions = [
            q for q in questions
            if q.get("question_type") in ["QUESTION", "SUBQUESTION", None]
            and not any(term in q.get("question_text", "").lower() for term in [
                "all questions are compulsory", "make suitable assumptions", "figures to the right indicate"
            ])
        ]

        if not valid_questions:
            return []

        # If Gemini is configured and enabled, attempt AI generation
        if self.ai_provider == "gemini" and self.api_key:
            try:
                ai_results = self._call_gemini_scrutiny(
                    subject_code, subject_name, course_outcomes, syllabus_units, valid_questions, selected_units
                )
                if ai_results:
                    return ai_results
            except Exception as e:
                logger.warning("Gemini scrutiny did not complete; falling back to offline heuristics.")

        # Fallback / Offline Semantic Pipeline (Deterministic Heuristic)
        return self._semantic_heuristic_analysis(
            subject_code, subject_name, course_outcomes, syllabus_units, valid_questions, selected_units
        )

    def _call_gemini_scrutiny(
        self,
        subject_code: str,
        subject_name: str,
        course_outcomes: List[Dict[str, Any]],
        syllabus_units: List[Dict[str, Any]],
        questions: List[Dict[str, Any]],
        selected_units: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Invokes Gemini using the strict academic scrutiny prompt."""
        cand_units = [u for u in syllabus_units if u.get("unit_number") in set(selected_units)] if selected_units else syllabus_units
        syl_lines = []
        for u in cand_units:
            syl_lines.append(f"Unit {u.get('unit_number')}: {u.get('title', '')}")
            for t in u.get('topics', []):
                t_name = t.get('topic_name') if isinstance(t, dict) else str(t)
                syl_lines.append(f"   - {t_name}")
        syl_text = "\n".join(syl_lines)

        questions_payload = []
        for q in questions:
            questions_payload.append({
                "question_number": q.get("question_number"),
                "question_text": q.get("question_text"),
                "marks": q.get("marks"),
                "co_code": q.get("co_code"),
                "bloom_level": q.get("bloom_level"),
                "section": q.get("section_name")
            })

        system_prompt = f"""You are an academic question-paper scrutiny engine for an autonomous engineering college.
You are NOT a generic chatbot.
You must analyze ONLY the supplied actual examination questions.

General instructions, headers, footers, exam metadata, section labels, marks legends, and explanatory notes are NOT questions.

Never invent:
- question text
- marks
- CO
- Bloom level
- unit
- topic

If a value is unavailable, return null.

The deterministic parser has already extracted:
question_number, question_text, marks, CO, Bloom, section, question_type.
Do not change deterministic values unless there is explicit contradictory evidence.

Subject: {subject_code} - {subject_name}
Configured Course Outcomes (COs):
{co_text or 'None configured'}

Configured Syllabus Units & Topics:
{syl_text or 'None configured'}

Active Examination Units (MANDATORY): {selected_units if selected_units else 'All Units'}
CRITICAL: You must ONLY map questions to the Active Examination Units listed above. Do NOT output any unit_number outside this set.

Supplied Examination Questions:
{json.dumps(questions_payload, indent=2)}

For each question return STRICT JSON array where each object has:
{{
  "question_number": "...",
  "bloom_level": "K1-K6 or null",
  "co_code": "CO1/CO2/... or null",
  "unit_number": integer or null,
  "topic_name": "..." or null,
  "confidence": 0.0-1.0 or null when unsupported,
  "reasoning": "...",
  "grammar_status": "PASS/WARNING/FAIL/NOT_EVALUATED",
  "quality_status": "PASS/WARNING/FAIL/NOT_EVALUATED",
  "suggested_improvement": "..." or null,
  "issues": [
    {{
      "issue_type": "Grammar/Spelling/Punctuation/Clarity/Ambiguity/Formatting",
      "problem": "Identified error or phrasing issue",
      "suggested_correction": "Correction text",
      "explanation": "Short actionable explanation"
    }}
  ]
}}

Return ONLY the raw JSON array. Do not include markdown code block formatting or conversational text."""

        raw_resp = self._call_gemini_raw(system_prompt)
        cleaned = raw_resp.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        parsed_json = json.loads(cleaned.strip())
        if not isinstance(parsed_json, list):
            parsed_json = [parsed_json]

        # Validate with Pydantic and merge with deterministic questions
        results_by_num = {}
        for item in parsed_json:
            try:
                val = AIQuestionAnalysis(**item)
                results_by_num[val.question_number] = val.model_dump()
            except Exception:
                logger.warning("A Gemini question result did not match the expected schema; it was left unavailable.")

        final_results = []
        for q in questions:
            q_num = q.get("question_number")
            ai_item = results_by_num.get(q_num, {})

            # Deterministic override: parser values take precedence; never invent missing values
            bloom = q.get("bloom_level") or ai_item.get("bloom_level")
            co = q.get("co_code") or ai_item.get("co_code")
            unit = ai_item.get("unit_number")
            topic = ai_item.get("topic_name")

            # Validate Bloom / CO formats from AI
            if bloom and not re.match(r"^K[1-6]$", str(bloom).upper()):
                bloom = q.get("bloom_level")
            elif bloom:
                bloom = str(bloom).upper()
            if co and not re.match(r"^CO\s*\d+$", str(co), re.I):
                co = q.get("co_code")
            elif co:
                co = re.sub(r"\s+", "", str(co).upper())

            conf = ai_item.get("confidence")
            try:
                conf = max(0.0, min(1.0, float(conf))) if conf is not None else None
            except (TypeError, ValueError):
                conf = None

            g_status = ai_item.get("grammar_status")
            q_status = ai_item.get("quality_status")
            s_improv = ai_item.get("suggested_improvement")
            g_reason = ai_item.get("reasoning")
            issues = ai_item.get("issues") or []

            if not g_status or g_status == "NOT_EVALUATED":
                g_eval = GrammarAnalysisService.evaluate_question(q.get("question_text", ""), marks=q.get("marks"))
                g_status = g_eval.get("grammar_status", "PASS")
                if not q_status or q_status == "NOT_EVALUATED":
                    q_status = g_eval.get("quality_status", "PASS")
                if not s_improv:
                    s_improv = g_eval.get("suggested_improvement")
                if not g_reason or g_reason == "No analysis explanation was returned for this question.":
                    g_reason = g_eval.get("reasoning", "")
                if not issues:
                    issues = g_eval.get("issues", [])

            final_results.append({
                "question_id": q.get("id"),
                "question_number": q_num,
                "bloom_level": bloom,
                "co_code": co,
                "unit_number": unit,
                "topic_name": topic,
                "confidence": conf,
                "reasoning": g_reason or "Question analysis completed.",
                "grammar_status": g_status,
                "quality_status": q_status or "PASS",
                "suggested_improvement": s_improv,
                "issues": issues,
                "analysis_mode": "gemini",
            })

        return final_results

    def _semantic_heuristic_analysis(
        self,
        subject_code: str,
        subject_name: str,
        course_outcomes: List[Dict[str, Any]],
        syllabus_units: List[Dict[str, Any]],
        questions: List[Dict[str, Any]],
        selected_units: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Deterministic, offline semantic evaluation engine.
        Evaluates Bloom's taxonomy verbs, syllabus unit keyword matches, and CO mappings.
        Respects explicitly parsed document values.
        """
        results = []
        selected_set = set(selected_units) if selected_units else None
        candidate_units = [u for u in syllabus_units if u.get("unit_number") in selected_set] if selected_set else syllabus_units

        # Filter candidate COs matching active unit scope
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

        for q in questions:
            q_text = q.get("question_text", "")
            q_text_lower = q_text.lower()
            q_num = q.get("question_number", "Q1")

            # 1. Bloom Level Determination
            # Source of truth: Document explicit Bloom -> Keyword heuristic
            bloom_level = q.get("bloom_level")
            bloom_confidence = None
            bloom_reason = ""

            if not bloom_level:
                if any(w in q_text_lower for w in ["design", "develop", "create", "construct", "formulate"]):
                    bloom_level, bloom_reason = "K6", "Classified as Create (K6) based on synthesis demand."
                elif any(w in q_text_lower for w in ["evaluate", "justify", "assess", "critique", "which is best"]):
                    bloom_level, bloom_reason = "K5", "Classified as Evaluate (K5) based on critical assessment requirements."
                elif any(w in q_text_lower for w in ["analyze", "differentiate", "compare", "contrast", "examine", "distinguish"]):
                    bloom_level, bloom_reason = "K4", "Classified as Analyze (K4) based on comparative and structural analysis."
                elif any(w in q_text_lower for w in ["apply", "solve", "calculate", "implement", "compute", "demonstrate", "cipher", "algorithm"]):
                    bloom_level, bloom_reason = "K3", "Classified as Apply (K3) based on procedural execution and computation."
                elif any(w in q_text_lower for w in ["explain", "describe", "discuss", "illustrate", "summarize", "why"]):
                    bloom_level, bloom_reason = "K2", "Classified as Understand (K2) based on conceptual explanation."
                else:
                    bloom_level = None
                    bloom_reason = "No supported Bloom action verb was detected; manual classification is required."
            else:
                bloom_reason = f"Explicitly indicated in examination paper as {bloom_level}."

            # 2. Unit & Topic Mapping — strictly restricted to active examination units
            detected_unit = None
            detected_topic = None

            sec_name = q.get("section_name") or ""
            sec_unit_match = re.search(r"Unit\s*(?:No\.?)?\s*0*(\d+)", sec_name, re.I)
            if not sec_unit_match:
                sec_unit_match = re.search(r"\bUnit\s*0*(\d+)\b", sec_name, re.I)

            forced_unit = None
            if sec_unit_match:
                u_cand = int(sec_unit_match.group(1))
                if any(u.get("unit_number") == u_cand for u in candidate_units):
                    forced_unit = u_cand

            if forced_unit is not None:
                detected_unit = forced_unit
                target_u = next((u for u in candidate_units if u.get("unit_number") == forced_unit), None)
                best_topic = None
                best_score = 0
                if target_u:
                    for t in target_u.get("topics", []):
                        t_name = t.get("topic_name") if isinstance(t, dict) else str(t)
                        t_lower = (t_name or "").lower()
                        score = sum(1 for word in re.findall(r"\w+", t_lower) if len(word) > 3 and word in q_text_lower)
                        if score > best_score:
                            best_score = score
                            best_topic = t_name
                    if not best_topic and target_u.get("topics"):
                        t0 = target_u.get("topics")[0]
                        best_topic = t0.get("topic_name") if isinstance(t0, dict) else str(t0)
                detected_topic = best_topic
            else:
                max_matches = 0
                for u in candidate_units:
                    u_num = u.get("unit_number")
                    u_title = u.get("title", "").lower()
                    u_topics = u.get("topics", [])

                    matches = 0
                    for word in re.findall(r"\w+", u_title):
                        if len(word) > 3 and word in q_text_lower:
                            matches += 2

                    best_topic_for_unit = None
                    for t in u_topics:
                        t_name = t.get("topic_name") if isinstance(t, dict) else str(t)
                        t_lower = (t_name or "").lower()
                        topic_hits = 0
                        for word in re.findall(r"\w+", t_lower):
                            if len(word) > 3 and word in q_text_lower:
                                topic_hits += 3
                        if topic_hits > 0 and (matches + topic_hits) >= max_matches:
                            best_topic_for_unit = t_name
                        matches += topic_hits

                    if matches > max_matches:
                        max_matches = matches
                        detected_unit = u_num
                        detected_topic = best_topic_for_unit

                if max_matches < 2:
                    if len(candidate_units) == 1:
                        detected_unit = candidate_units[0].get("unit_number")
                    else:
                        detected_unit = None
                        detected_topic = None

            # 3. Course Outcome (CO) Mapping — scoped to active units
            co_code = q.get("co_code")
            co_reason = ""
            if co_code and (not selected_set or any(c.get("co_code") == co_code for c in candidate_cos)):
                co_reason = f"Explicitly indicated in examination paper as {co_code}."
            elif candidate_cos:
                best_co = None
                best_score = 0
                for c in candidate_cos:
                    desc = (c.get("description") or "").lower()
                    score = sum(1 for w in re.findall(r"\w+", desc) if len(w) > 4 and w in q_text_lower)
                    if score > best_score:
                        best_score = score
                        best_co = c.get("co_code")
                if best_co and best_score >= 2:
                    co_code = best_co
                    co_reason = f"Mapped to {best_co} via syllabus CO keyword overlap."
                elif detected_unit:
                    unit_co = next((c.get("co_code") for c in candidate_cos if re.search(r"\d+", str(c.get("co_code", ""))) and int(re.search(r"\d+", str(c.get("co_code", ""))).group()) == detected_unit), None)
                    if unit_co:
                        co_code = unit_co
                        co_reason = f"Mapped to {unit_co} based on unit {detected_unit} alignment."
                    else:
                        co_code = candidate_cos[0].get("co_code") if candidate_cos else None
                        co_reason = f"Mapped to {co_code} from active examination scope." if co_code else "CO flagged for moderator review."
                else:
                    co_code = None
                    co_reason = "CO not confidently mapped; flagged for moderator review."
            else:
                co_code = None
                co_reason = "No course outcomes configured for this subject or active unit scope."

            # 4. Grammar & Clarity Analysis
            g_eval = GrammarAnalysisService.evaluate_question(q_text, marks=q.get("marks"))
            grammar_status = g_eval.get("grammar_status", "PASS")
            quality_status = g_eval.get("quality_status", "PASS")
            suggestion = g_eval.get("suggested_improvement")
            grammar_reason = g_eval.get("reasoning", "")

            combined_reason = f"{bloom_reason} {co_reason}".strip()
            if grammar_reason:
                combined_reason = f"{combined_reason} | Grammar: {grammar_reason}".strip()

            results.append({
                "question_id": q.get("id"),
                "question_number": q_num,
                "bloom_level": bloom_level,
                "co_code": co_code,
                "unit_number": detected_unit,
                "topic_name": detected_topic,
                "confidence": bloom_confidence,
                "reasoning": combined_reason,
                "grammar_status": grammar_status,
                "quality_status": quality_status,
                "suggested_improvement": suggestion,
                "issues": g_eval.get("issues", []),
                "analysis_mode": "offline_heuristic",
            })

        return results

    # --- Backward compatibility methods for individual services ---

    def analyze_bloom(self, subject_name: str, q_num: str, text: str, marks: int) -> dict:
        res = self._semantic_heuristic_analysis(
            "", subject_name, [], [], [{"question_number": q_num, "question_text": text, "marks": marks}]
        )
        item = res[0] if res else {}
        return {
            "bloom_level": item.get("bloom_level"),
            "confidence": item.get("confidence"),
            "reason": item.get("reasoning", "Bloom classification is unavailable.")
        }

    def map_co(self, subject_name: str, q_num: str, text: str, cos: list) -> dict:
        res = self._semantic_heuristic_analysis(
            "", subject_name, cos, [], [{"question_number": q_num, "question_text": text}]
        )
        item = res[0] if res else {}
        return {
            "co_code": item.get("co_code"),
            "confidence": item.get("confidence"),
            "reason": item.get("reasoning", "CO mapping evaluated.")
        }

    def map_syllabus(self, subject_name: str, q_num: str, text: str, units: list) -> dict:
        res = self._semantic_heuristic_analysis(
            "", subject_name, [], units, [{"question_number": q_num, "question_text": text}]
        )
        item = res[0] if res else {}
        return {
            "unit_number": item.get("unit_number"),
            "topic_name": item.get("topic_name"),
            "confidence": item.get("confidence"),
            "reason": item.get("reasoning", "Syllabus alignment evaluated.")
        }

    def check_grammar(self, q_num: str, text: str) -> dict:
        res = self._semantic_heuristic_analysis(
            "", "", [], [], [{"question_number": q_num, "question_text": text}]
        )
        item = res[0] if res else {}
        has_issue = item.get("grammar_status") != "PASS"
        return {
            "has_issue": has_issue,
            "issue_type": "Clarity Warning" if has_issue else "None",
            "explanation": item.get("suggested_improvement") or "Automated grammar evaluation is not configured.",
            "suggested_improvement": item.get("suggested_improvement"),
            "confidence": None
        }

    def evaluate_quality(self, subject_name: str, q_num: str, text: str, marks: int) -> dict:
        return {
            "quality_score": None,
            "confidence": None,
            "reason": "Question quality analysis is unavailable in offline heuristic mode.",
            "issues": [],
            "recommendation": None
        }

    def estimate_solving_time(self, q_num: str, text: str, marks: int, bloom_level: str) -> dict:
        if marks is None or bloom_level is None:
            return {
                "estimated_minutes": None,
                "confidence": None,
                "reason": "Marks or cognitive level is unavailable; solving time cannot be estimated."
            }
        level = str(bloom_level).upper()
        multipliers = {"K1": 1.0, "K2": 1.2, "K3": 1.5, "K4": 1.7, "K5": 1.9, "K6": 2.2}
        multiplier = multipliers.get(level)
        if multiplier is None:
            return {"estimated_minutes": None, "confidence": None, "reason": "The cognitive level is unsupported; solving time cannot be estimated."}
        est = round(marks * multiplier, 1)
        return {
            "estimated_minutes": max(est, 2.0),
            "confidence": None,
            "reason": f"Calculated based on {marks} marks and {bloom_level} cognitive complexity."
        }

    def generate_recommendations(self, findings_summary_text: str) -> dict:
        return {
            "recommendations": [],
            "status": "NOT_EVALUATED",
            "reason": "Recommendation generation is unavailable without evidence-backed findings.",
        }

gemini_service = GeminiService()


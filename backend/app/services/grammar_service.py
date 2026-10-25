import re
from typing import Dict, Any, List, Optional

class GrammarAnalysisService:
    """
    Academic question grammar and language clarity evaluation engine.
    Analyzes sentence structure, syntax, capitalization, punctuation,
    article agreement, repeated words, and double negatives.
    """

    ACTION_VERBS = {
        "explain", "describe", "define", "discuss", "compare", "differentiate",
        "state", "illustrate", "derive", "evaluate", "calculate", "find",
        "prove", "analyze", "design", "what", "why", "how", "which", "when",
        "where", "who", "write", "list", "give", "show", "determine", "classify",
        "distinguish", "construct", "estimate", "formulate", "sketch", "summarize",
        "demonstrate", "identify", "justify", "implement", "solve"
    }

    VOWEL_WORDS_NEEDING_AN = {
        "algorithm", "array", "entity", "outcome", "operation", "operating",
        "example", "expression", "architecture", "instruction", "integer",
        "automaton", "interface", "index", "instance", "iteration", "object",
        "attribute", "asymmetric", "encryption", "input", "output", "error"
    }

    CONSONANT_WORDS_NEEDING_A = {
        "system", "computer", "table", "tree", "binary", "model", "network",
        "matrix", "process", "thread", "database", "diagram", "program",
        "structure", "function", "variable", "class", "protocol", "cipher",
        "security", "packet", "layer", "router", "switch", "server", "client"
    }

    @classmethod
    def analyze_grammar(cls, question_text: str) -> List[Dict[str, Any]]:
        """Backward-compatible helper returning list of issues."""
        evaluation = cls.evaluate_question(question_text)
        return evaluation.get("issues", [])

    @classmethod
    def evaluate_question(cls, question_text: str, marks: Optional[int] = None) -> Dict[str, Any]:
        """
        Evaluates grammar, clarity, and question quality.
        Returns a dict with grammar_status ('PASS', 'WARNING', 'FAIL'),
        quality_status, issues list, suggested_improvement, and reasoning.
        """
        raw_text = (question_text or "").strip()
        if not raw_text:
            return {
                "grammar_status": "FAIL",
                "quality_status": "FAIL",
                "issues": [{"issue_type": "Empty Question", "explanation": "Question text is empty."}],
                "suggested_improvement": "Provide complete question text.",
                "reasoning": "Question text is empty."
            }

        issues: List[Dict[str, Any]] = []
        improved_text = raw_text

        # Strip leading numbering like '1.', 'a)', '(i)', 'Q.1', etc. for structural checks
        clean_prompt = re.sub(r"^(?:Q(?:uestion)?\.?\s*\d+[\w\.\)]*|\(?\d+[\.\)]|\(?[a-zA-Z][\.\)]|\(?[ivxIVX]+[\.\)])\s*", "", raw_text).strip()
        if not clean_prompt:
            clean_prompt = raw_text

        words = re.findall(r"\b[\w'-]+\b", clean_prompt)

        # 1. Brevity check
        if len(words) < 4:
            issues.append({
                "issue_type": "Excessive Brevity",
                "explanation": "Question is excessively short (< 4 words). Needs action verb and clear scope.",
                "severity": "WARNING"
            })
            first_word_lower = words[0].lower() if words else ""
            if first_word_lower not in cls.ACTION_VERBS:
                improved_text = f"Explain the concept of {clean_prompt} in detail."

        # 2. Capitalization check
        first_letter_match = re.search(r"[a-zA-Z]", clean_prompt)
        if first_letter_match and first_letter_match.group(0).islower():
            issues.append({
                "issue_type": "Capitalization",
                "explanation": "Question does not begin with an uppercase letter.",
                "severity": "WARNING"
            })
            idx = clean_prompt.find(first_letter_match.group(0))
            improved_text = improved_text[:idx] + improved_text[idx].upper() + improved_text[idx+1:]

        # 3. Punctuation check
        text_without_marks = re.sub(r"\s*(?:\[\s*\d+\s*(?:marks?|m)?\s*\]|\(\s*\d+\s*(?:marks?|m)?\s*\))\s*$", "", clean_prompt, flags=re.IGNORECASE).rstrip()
        clean_end = text_without_marks if text_without_marks else clean_prompt.rstrip()
        if clean_end and clean_end[-1] not in "?.:;!\"'":
            inquiry_words = {"what", "why", "how", "which", "where", "who", "when", "can", "is", "are"}
            first_word = words[0].lower() if words else ""
            if first_word in inquiry_words or "what is" in clean_prompt.lower() or "how to" in clean_prompt.lower():
                issues.append({
                    "issue_type": "Missing Terminal Punctuation",
                    "explanation": "Inquiry statement should terminate with a question mark (?).",
                    "severity": "WARNING"
                })
                improved_text = improved_text.rstrip() + "?"
            else:
                issues.append({
                    "issue_type": "Missing Terminal Punctuation",
                    "explanation": "Imperative question statement should terminate with a period (.).",
                    "severity": "WARNING"
                })
                improved_text = improved_text.rstrip() + "."

        # 4. Double Negatives
        q_lower = clean_prompt.lower()
        double_neg_patterns = [
            (r"\bdon'?t\s+not\b", "do not"),
            (r"\bcan'?t\s+not\b", "cannot"),
            (r"\bnever\s+no\b", "never any"),
            (r"\bhardly\s+no\b", "hardly any"),
            (r"\bnot\s+unnecessary\b", "necessary"),
        ]
        for pat, repl in double_neg_patterns:
            if re.search(pat, q_lower):
                issues.append({
                    "issue_type": "Double Negative",
                    "explanation": "Contains confusing double negative phrasing.",
                    "severity": "WARNING"
                })
                improved_text = re.sub(pat, repl, improved_text, flags=re.IGNORECASE)

        # 5. Duplicate consecutive words (e.g. "the the", "in in")
        dup_match = re.search(r"\b([a-zA-Z]{2,})\s+\1\b", clean_prompt, re.IGNORECASE)
        if dup_match:
            dup_word = dup_match.group(1)
            # Allow common idioms like "that that" or "had had" if unavoidable
            if dup_word.lower() not in {"that", "had"}:
                issues.append({
                    "issue_type": "Repeated Word",
                    "explanation": f"Contains duplicated consecutive word: '{dup_word} {dup_word}'.",
                    "severity": "WARNING"
                })
                improved_text = re.sub(r"\b(" + re.escape(dup_word) + r")\s+\1\b", r"\1", improved_text, flags=re.IGNORECASE)

        # 6. Article Agreement (a vs an)
        for w in cls.VOWEL_WORDS_NEEDING_AN:
            pat = r"\ba\s+(" + re.escape(w) + r")\b"
            if re.search(pat, q_lower):
                issues.append({
                    "issue_type": "Article Agreement",
                    "explanation": f"Use 'an' instead of 'a' before '{w}'.",
                    "severity": "WARNING"
                })
                improved_text = re.sub(r"\ba\s+(" + re.escape(w) + r")\b", r"an \1", improved_text, flags=re.IGNORECASE)

        for w in cls.CONSONANT_WORDS_NEEDING_A:
            pat = r"\ban\s+(" + re.escape(w) + r")\b"
            if re.search(pat, q_lower):
                issues.append({
                    "issue_type": "Article Agreement",
                    "explanation": f"Use 'a' instead of 'an' before '{w}'.",
                    "severity": "WARNING"
                })
                improved_text = re.sub(r"\ban\s+(" + re.escape(w) + r")\b", r"a \1", improved_text, flags=re.IGNORECASE)

        # 7. Common subject-verb slips in Indian academic exams
        verb_slips = [
            (r"\bdoes\s+not\s+has\b", "does not have"),
            (r"\bdo\s+not\s+has\b", "do not have"),
            (r"\bdid\s+not\s+went\b", "did not go"),
            (r"\bis\s+consist\s+of\b", "consists of"),
            (r"\bare\s+consist\s+of\b", "are composed of"),
        ]
        for pat, repl in verb_slips:
            if re.search(pat, q_lower):
                issues.append({
                    "issue_type": "Grammatical Agreement",
                    "explanation": f"Phrasing error: replace with '{repl}'.",
                    "severity": "WARNING"
                })
                improved_text = re.sub(pat, repl, improved_text, flags=re.IGNORECASE)

        # Determine overall statuses
        if not issues:
            grammar_status = "PASS"
            quality_status = "PASS"
            reasoning = "Question phrasing, sentence structure, and grammar are clear and syntactically correct."
            suggested_improvement = None
        elif len(issues) == 1:
            grammar_status = "WARNING"
            quality_status = "PASS" if issues[0]["issue_type"] in ("Missing Terminal Punctuation", "Capitalization") else "WARNING"
            reasoning = f"Minor language notice: {issues[0]['explanation']}"
            suggested_improvement = improved_text if improved_text != raw_text else None
        else:
            grammar_status = "WARNING" if all(i.get("severity") == "WARNING" for i in issues) else "FAIL"
            quality_status = "WARNING"
            reasoning = "; ".join(i["explanation"] for i in issues)
            suggested_improvement = improved_text if improved_text != raw_text else None

        return {
            "grammar_status": grammar_status,
            "quality_status": quality_status,
            "issues": issues,
            "suggested_improvement": suggested_improvement,
            "reasoning": reasoning
        }

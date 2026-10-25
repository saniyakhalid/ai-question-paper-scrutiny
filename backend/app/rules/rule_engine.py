import re
from typing import List, Dict, Any, Optional
from app.models.models import RuleStatus

class RuleEngine:
    def validate_paper(
        self,
        questions: List[Dict[str, Any]],
        subject_config: Dict[str, Any],
        bloom_findings: List[Dict[str, Any]],
        co_findings: List[Dict[str, Any]],
        syllabus_findings: List[Dict[str, Any]],
        estimated_solving_time_minutes: float,
        selected_units: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        rule_results = []
        
        # The institution's configured examination total is authoritative. A number
        # printed in the uploaded paper is evidence to check, not the target itself.
        target_total_marks = subject_config.get("total_marks")
        declared_total_marks = subject_config.get("declared_total_marks")
        if target_total_marks is None and declared_total_marks is not None:
            target_total_marks = declared_total_marks
        target_duration = subject_config.get("duration_minutes")
        min_co_pct = subject_config.get("min_co_coverage_pct")
        min_unit_pct = subject_config.get("min_unit_coverage_pct")
        all_cos = subject_config.get("course_outcomes", [])
        all_units = subject_config.get("syllabus_units", [])

        # Filter applicable units if selected_units specified
        if selected_units and len(selected_units) > 0:
            target_units = [u for u in all_units if u.get("unit_number") in selected_units]
            applicable_unit_numbers = set(selected_units)
        else:
            target_units = all_units
            applicable_unit_numbers = set(u.get("unit_number") for u in all_units)

        # 1. Total Marks Verification Rule
        # Exclude question groups (to avoid double counting parent group marks and child subquestion marks)
        # Exclude secondary alternatives in internal choices
        # For groups declaring a maximum limit (e.g. "any two [18]"), cap group contribution to group total
        seen_choices = set()
        group_marks_map: Dict[str, int] = {}
        group_items_map: Dict[str, List[Dict[str, Any]]] = {}
        standalone_questions: List[Dict[str, Any]] = []
        unmarked_count = 0

        # Find any group maximum limits
        for q in questions:
            if q.get("question_type") == "QUESTION_GROUP":
                q_num = q.get("question_number", "")
                if q.get("marks") is not None:
                    group_marks_map[q_num] = q.get("marks")
                continue

            q_marks = q.get("marks")
            if q_marks is None or q_marks <= 0:
                unmarked_count += 1
                continue

            # Handle internal choice
            choice_id = q.get("choice_group_id")
            if choice_id:
                if choice_id in seen_choices:
                    continue  # Skip alternative side of choice
                seen_choices.add(choice_id)
            elif q.get("internal_choice"):
                q_id_key = f"{q.get('parent_number')}_{q.get('sub_question') or q.get('question_number')}"
                if q_id_key in seen_choices:
                    continue
                seen_choices.add(q_id_key)

            parent_num = q.get("parent_number")
            if not parent_num:
                q_num_str = str(q.get("question_number", ""))
                m_p = re.match(r"^(Q(?:uestion)?\s*[\.\-]?\s*\d+)", q_num_str, re.I)
                if m_p:
                    raw_p = m_p.group(1)
                    for gm_key in group_marks_map:
                        if re.sub(r"[\s\.\-_]", "", gm_key).upper() == re.sub(r"[\s\.\-_]", "", raw_p).upper():
                            parent_num = gm_key
                            break

            if parent_num and parent_num in group_marks_map:
                if parent_num not in group_items_map:
                    group_items_map[parent_num] = []
                group_items_map[parent_num].append(q)
            else:
                standalone_questions.append(q)

        calculated_marks = 0
        # Add capped group marks
        for g_num, g_items in group_items_map.items():
            g_sum = sum(item.get("marks", 0) for item in g_items)
            g_cap = group_marks_map.get(g_num)
            if g_cap is not None and g_sum > g_cap:
                calculated_marks += g_cap
            else:
                calculated_marks += g_sum

        calculated_marks += sum(q.get("marks", 0) for q in standalone_questions)
        if target_total_marks is None:
            rule_results.append({
                "rule_name": "Total Marks Verification",
                "category": "MARKS",
                "expected": "Configured exam total marks",
                "actual": f"{calculated_marks} identifiable marks" + (f" ({unmarked_count} unallocated)" if unmarked_count else ""),
                "status": RuleStatus.NOT_EVALUATED.value,
                "message": "No examination total is configured or declared, so the marks total cannot be verified."
            })
        else:
            diff = calculated_marks - target_total_marks
            header_mismatch = declared_total_marks is not None and declared_total_marks != target_total_marks
            if calculated_marks == target_total_marks and unmarked_count == 0 and not header_mismatch:
                status_val = RuleStatus.PASS.value
            elif abs(diff) > 5 or header_mismatch:
                status_val = RuleStatus.FAIL.value
            else:
                status_val = RuleStatus.WARNING.value
            header_note = (
                f"; paper header declares {declared_total_marks} marks against configured {target_total_marks}"
                if header_mismatch else ""
            )
            rule_results.append({
                "rule_name": "Total Marks Verification",
                "category": "MARKS",
                "expected": f"{target_total_marks} Marks",
                "actual": f"{calculated_marks} identifiable marks" + (f" ({unmarked_count} unallocated)" if unmarked_count else "") + (f"; header declares {declared_total_marks}" if declared_total_marks is not None else ""),
                "status": status_val,
                "message": f"Configured total: {target_total_marks}; identifiable total: {calculated_marks}; difference: {diff:+d}" + (f"; {unmarked_count} question(s) have no marks" if unmarked_count else "") + header_note + f". Status: {status_val}"
            })

        # 1b. Section-wise Marks & Sub-Question Structure Check
        sections_map: Dict[str, int] = {}
        missing_marks_questions = []
        for q in questions:
            if q.get("question_type") == "QUESTION_GROUP":
                continue
            sec = q.get("section_name") or "GENERAL"
            qm = q.get("marks")
            if qm is not None and qm > 0:
                sections_map[sec] = sections_map.get(sec, 0) + qm
            else:
                missing_marks_questions.append(q.get("question_number") or "Unknown")

        if missing_marks_questions:
            sec_status = RuleStatus.WARNING.value
            sec_msg = f"Missing/unallocated marks detected in {len(missing_marks_questions)} question(s): {', '.join(missing_marks_questions[:6])}. Manual verification recommended."
        else:
            sec_status = RuleStatus.PASS.value
            sec_summary = ", ".join(f"{s}: {m}M" for s, m in sections_map.items()) if sections_map else "Unified layout"
            sec_msg = f"All individual questions have defined marks. Section totals: {sec_summary}."

        rule_results.append({
            "rule_name": "Section-wise Marks & Question Structure",
            "category": "MARKS",
            "expected": "Explicit marks for all questions and sub-questions",
            "actual": f"{len(missing_marks_questions)} unallocated; Sections: {len(sections_map)}",
            "status": sec_status,
            "message": sec_msg
        })

        # 2. Question Numbering Sequence Rule
        q_numbers = [q.get("question_number", "") for q in questions if q.get("question_type") != "QUESTION_GROUP"]
        # In case of internal choices, multiple questions may share the same question_number; filter choice alternatives
        unique_q_numbers = []
        for q in questions:
            if q.get("question_type") == "QUESTION_GROUP":
                continue
            if q.get("internal_choice") and q.get("question_number") in unique_q_numbers:
                continue
            unique_q_numbers.append(q.get("question_number", ""))

        has_duplicates = len(unique_q_numbers) != len(set(unique_q_numbers))
        if not has_duplicates and len(unique_q_numbers) > 0:
            rule_results.append({
                "rule_name": "Question Numbering Consistency",
                "category": "NUMBERING",
                "expected": "Unique sequential question numbers",
                "actual": f"{len(unique_q_numbers)} unique questions parsed",
                "status": RuleStatus.PASS.value,
                "message": "All questions have clear, unique identifiers."
            })
        else:
            rule_results.append({
                "rule_name": "Question Numbering Consistency",
                "category": "NUMBERING",
                "expected": "Unique sequential question numbers",
                "actual": "Duplicate or missing question numbers detected",
                "status": RuleStatus.WARNING.value,
                "message": "Duplicate or inconsistent question numbers detected in document layout."
            })

        # 3. Internal Choice Pattern Rule
        choice_count = sum(1 for q in questions if q.get("internal_choice", False))
        choice_required = subject_config.get("internal_choice_required")
        choice_status = (
            RuleStatus.NOT_EVALUATED.value if choice_required is None
            else RuleStatus.PASS.value if bool(choice_count) == bool(choice_required)
            else RuleStatus.WARNING.value
        )
        rule_results.append({
            "rule_name": "Internal Choice Validation",
            "category": "CHOICE",
            "expected": "Configured internal-choice requirement" if choice_required is not None else "Not configured",
            "actual": f"{choice_count} questions contain internal choices",
            "status": choice_status,
            "message": (
                f"{choice_count} internal-choice question(s) detected; configured requirement is {'required' if choice_required else 'not required'}."
                if choice_required is not None
                else "Internal-choice requirements are not configured for this examination; no compliance result was assigned."
            )
        })

        # 4. Course Outcome (CO) Coverage Rule
        mapped_cos = set(f.get("co_code") for f in co_findings if f.get("co_code") and f.get("co_code") != "UNMAPPED")
        
        # When selected_units is specified, expected COs must be restricted to those corresponding to selected_units
        if selected_units and len(selected_units) > 0:
            sel_unit_set = set(selected_units)
            applicable_cos = [
                c for c in all_cos
                if (re.search(r"\d+", str(c.get("co_code", ""))) and int(re.search(r"\d+", str(c.get("co_code", ""))).group()) in sel_unit_set)
                or (c.get("unit_number") in sel_unit_set)
            ]
            if not applicable_cos:
                applicable_cos = all_cos[:len(selected_units)]
        else:
            applicable_cos = all_cos

        total_co_count = len(applicable_cos)
        applicable_co_codes = set(c.get("co_code") for c in applicable_cos)
        mapped_applicable_cos = mapped_cos.intersection(applicable_co_codes) if applicable_co_codes else mapped_cos
        co_cov_pct = (len(mapped_applicable_cos) / total_co_count * 100.0) if total_co_count > 0 else None
        co_status = (
            RuleStatus.NOT_EVALUATED.value if total_co_count == 0 or min_co_pct is None
            else RuleStatus.PASS.value if co_cov_pct >= min_co_pct
            else RuleStatus.WARNING.value
        )
        scope_note = f" across selected units {sorted(list(selected_units))}" if selected_units else ""
        rule_results.append({
            "rule_name": "Course Outcome (CO) Coverage",
            "category": "COVERAGE",
            "expected": f">= {min_co_pct}% CO coverage ({total_co_count} COs total{scope_note})" if min_co_pct is not None else "Configured CO coverage requirement",
            "actual": f"{round(co_cov_pct, 1)}% ({len(mapped_applicable_cos)}/{total_co_count} COs covered)" if co_cov_pct is not None else "No course outcomes configured",
            "status": co_status,
            "message": (
                f"CO coverage ({round(co_cov_pct, 1)}%){scope_note} meets the configured threshold."
                if co_status == RuleStatus.PASS.value else
                f"CO coverage ({round(co_cov_pct, 1)}%){scope_note} is below the configured threshold ({min_co_pct}%)."
                if co_status == RuleStatus.WARNING.value else
                "CO coverage cannot be scored because course outcomes or an institutional coverage target are not configured."
            )
        })

        # 5. Syllabus Unit Coverage Rule (Dynamic against selected_units)
        mapped_units = set(f.get("unit_number") for f in syllabus_findings if f.get("unit_number", 0) in applicable_unit_numbers)
        total_unit_count = len(applicable_unit_numbers)
        unit_cov_pct = (len(mapped_units) / total_unit_count * 100.0) if total_unit_count > 0 else None
        unit_status = (
            RuleStatus.NOT_EVALUATED.value if total_unit_count == 0 or min_unit_pct is None
            else RuleStatus.PASS.value if unit_cov_pct >= min_unit_pct
            else RuleStatus.WARNING.value if unit_cov_pct >= (min_unit_pct * 0.5)
            else RuleStatus.FAIL.value
        )
        unit_msg = (
            f"Unit coverage ({round(unit_cov_pct, 1)}%) meets the configured threshold."
            if unit_status == RuleStatus.PASS.value
            else f"Unit coverage ({round(unit_cov_pct, 1)}%) is moderately below the configured threshold ({min_unit_pct}%)."
            if unit_status == RuleStatus.WARNING.value
            else f"Unit coverage ({round(unit_cov_pct, 1)}%) is below the configured threshold ({min_unit_pct}%)."
            if unit_status == RuleStatus.FAIL.value
            else "Unit coverage cannot be scored because syllabus units or an institutional coverage target are not configured."
        )
        rule_results.append({
            "rule_name": "Selected Unit Syllabus Coverage",
            "category": "COVERAGE",
            "expected": f">= {min_unit_pct}% coverage across selected units {sorted(list(applicable_unit_numbers))}" if min_unit_pct is not None else "Configured syllabus coverage requirement",
            "actual": f"{round(unit_cov_pct, 1)}% ({len(mapped_units)}/{total_unit_count} selected units covered)" if unit_cov_pct is not None else "No applicable syllabus units configured",
            "status": unit_status,
            "message": unit_msg
        })

        # 6. Unselected Unit Violation Rule
        unselected_violations = [
            f for f in syllabus_findings
            if f.get("unit_number") is not None
            and f.get("unit_number") not in applicable_unit_numbers
        ]
        if not applicable_unit_numbers:
            rule_results.append({
                "rule_name": "Exam Unit Selection Compliance",
                "category": "UNIT_COMPLIANCE",
                "expected": "Configured examination units",
                "actual": "No selected units or syllabus units configured",
                "status": RuleStatus.NOT_EVALUATED.value,
                "message": "Unit-selection compliance cannot be evaluated without a configured examination scope."
            })
        elif unselected_violations:
            violating_units = sorted(list(set(f.get("unit_number") for f in unselected_violations)))
            rule_results.append({
                "rule_name": "Exam Unit Selection Compliance",
                "category": "UNIT_COMPLIANCE",
                "expected": f"Questions restricted to selected units: {sorted(list(applicable_unit_numbers))}",
                "actual": f"{len(unselected_violations)} question(s) belong to unselected units {violating_units}",
                "status": RuleStatus.FAIL.value,
                "message": f"⚠ Question paper contains questions from unselected Unit(s) {violating_units} which are outside this exam's configured unit scope."
            })
        else:
            rule_results.append({
                "rule_name": "Exam Unit Selection Compliance",
                "category": "UNIT_COMPLIANCE",
                "expected": f"Questions restricted to selected units: {sorted(list(applicable_unit_numbers))}",
                "actual": f"All questions belong to selected units {sorted(list(applicable_unit_numbers))} (unmapped units ignored)",
                "status": RuleStatus.PASS.value,
                "message": "All mapped questions comply with configured examination unit boundary."
            })

        # 7. Bloom's Taxonomy Cognitive Level Distribution Rule
        bloom_counts = {}
        higher_order_levels = {
            "APPLY", "ANALYZE", "EVALUATE", "CREATE",
            "K3", "K4", "K5", "K6",
        }
        higher_order_count = 0
        for bf in bloom_findings:
            lvl = bf.get("bloom_level") or "UNMAPPED"
            bloom_counts[lvl] = bloom_counts.get(lvl, 0) + 1
            if str(lvl).upper() in higher_order_levels:
                higher_order_count += 1

        classified_bloom = [bf for bf in bloom_findings if bf.get("bloom_level")]
        total_q = len(classified_bloom)
        higher_order_pct = (higher_order_count / total_q) * 100.0 if total_q else None
        bloom_target = subject_config.get("min_higher_order_bloom_pct")
        bloom_status = (
            RuleStatus.NOT_EVALUATED.value if bloom_target is None or higher_order_pct is None
            else RuleStatus.PASS.value if higher_order_pct >= bloom_target
            else RuleStatus.WARNING.value
        )
        rule_results.append({
            "rule_name": "Bloom's Cognitive Distribution",
            "category": "COVERAGE",
            "expected": f">= {bloom_target}% Higher-Order questions" if bloom_target is not None else "Institution-configured Bloom distribution",
            "actual": f"{round(higher_order_pct, 1)}% Higher-Order questions ({higher_order_count}/{total_q} classified)" if higher_order_pct is not None else "No questions have a classified Bloom level",
            "status": bloom_status,
            "message": (
                "Bloom distribution meets the configured higher-order threshold."
                if bloom_status == RuleStatus.PASS.value else
                "Bloom distribution is below the configured higher-order threshold."
                if bloom_status == RuleStatus.WARNING.value else
                "Bloom distribution is informational only because an institutional target or classified evidence is unavailable."
            )
        })

        # 8. Estimated Solving Time Limit Rule
        if estimated_solving_time_minutes is None or target_duration is None:
            rule_results.append({
                "rule_name": "Solving Time Estimation Check",
                "category": "TIME",
                "expected": "Configured exam duration",
                "actual": "Unavailable",
                "status": RuleStatus.NOT_EVALUATED.value,
                "message": "Solving time cannot be compared because question marks/Bloom levels or the configured examination duration are unavailable."
            })
        elif estimated_solving_time_minutes <= (target_duration * 1.15):
            rule_results.append({
                "rule_name": "Solving Time Estimation Check",
                "category": "TIME",
                "expected": f"<= {target_duration} minutes",
                "actual": f"{round(estimated_solving_time_minutes, 1)} minutes",
                "status": RuleStatus.PASS.value,
                "message": f"Estimated solving time ({round(estimated_solving_time_minutes, 1)} min) is well within allotted examination duration ({target_duration} min)."
            })
        elif estimated_solving_time_minutes <= (target_duration * 1.35):
            diff = round(estimated_solving_time_minutes - target_duration, 1)
            rule_results.append({
                "rule_name": "Solving Time Estimation Check",
                "category": "TIME",
                "expected": f"<= {target_duration} minutes",
                "actual": f"{round(estimated_solving_time_minutes, 1)} minutes",
                "status": RuleStatus.WARNING.value,
                "message": f"Estimated solving time ({round(estimated_solving_time_minutes, 1)} min) slightly exceeds allotted duration ({target_duration} min) by {diff} minutes; advisory pacing note for examination committee."
            })
        else:
            diff = round(estimated_solving_time_minutes - target_duration, 1)
            rule_results.append({
                "rule_name": "Solving Time Estimation Check",
                "category": "TIME",
                "expected": f"<= {target_duration} minutes",
                "actual": f"{round(estimated_solving_time_minutes, 1)} minutes",
                "status": RuleStatus.FAIL.value,
                "message": f"Estimated solving time substantially exceeds allowed examination duration by {diff} minutes!"
            })

        return rule_results

    @staticmethod
    def validate_marks(questions, target_total_marks: int):
        calc = 0
        for q in questions:
            m = getattr(q, 'marks', None) if not isinstance(q, dict) else q.get('marks')
            calc += (m or 0)
        status = RuleStatus.PASS if calc == target_total_marks else RuleStatus.FAIL
        return {"status": status, "calculated": calc, "target": target_total_marks}

    @staticmethod
    def validate_numbering(questions):
        nums = []
        for q in questions:
            n = getattr(q, 'original_number', None) or getattr(q, 'question_number', None) if not isinstance(q, dict) else (q.get('original_number') or q.get('question_number'))
            if n:
                nums.append(str(n).strip())
        status = RuleStatus.PASS if (len(nums) == len(set(nums)) and len(nums) > 0) else RuleStatus.FAIL
        return {"status": status, "count": len(nums)}

rule_engine = RuleEngine()
RuleValidationEngine = RuleEngine

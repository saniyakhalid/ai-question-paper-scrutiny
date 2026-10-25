CO_PROMPT_TEMPLATE = """
You are assisting an examination moderator at an autonomous engineering college.
You are NOT the final decision maker.
Do not invent course outcomes. Use ONLY the supplied Course Outcomes.

Map the following question to the most appropriate Course Outcome (CO) from the available list:

Available Course Outcomes:
{co_list_text}

Question Details:
Subject: {subject_name}
Question Number: {question_number}
Question Text: "{question_text}"

Respond strictly in valid JSON format matching this schema:
{{
  "co_code": "CO1",
  "confidence": 0.90,
  "reason": "Clear technical alignment explanation.",
  "evidence": "Exact concepts or keywords linking question to CO description."
}}

If evidence is insufficient, set co_code to "UNMAPPED" and confidence to 0.0 with clear reasoning.
"""

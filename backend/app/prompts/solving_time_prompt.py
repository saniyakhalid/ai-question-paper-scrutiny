SOLVING_TIME_PROMPT_TEMPLATE = """
You are assisting an examination moderator as an AI Decision Support System.
Estimate the time (in minutes) required by an average student to solve this question under examination conditions.

Factors:
- Marks allocated: {marks}
- Cognitive level: {bloom_level}
- Mathematical/coding effort, diagram requirements, detailed derivation vs brief explanation

Question Details:
Question Number: {question_number}
Question Text: "{question_text}"
Marks: {marks}
Bloom Level: {bloom_level}

Respond strictly in valid JSON format matching this schema:
{{
  "estimated_minutes": 15.0,
  "confidence": 0.90,
  "reason": "Breakdown of time allocation (e.g. 5 min calculation, 10 min explanation)."
}}
"""

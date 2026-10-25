SYLLABUS_PROMPT_TEMPLATE = """
You are assisting an examination moderator at an autonomous engineering college.
You are NOT the final decision maker.
Use ONLY the provided syllabus structure. Do not invent units or topics.

Identify the primary Syllabus Unit and Topic for the question below:

Available Syllabus:
{syllabus_text}

Question Details:
Subject: {subject_name}
Question Number: {question_number}
Question Text: "{question_text}"

Respond strictly in valid JSON format matching this schema:
{{
  "unit_number": 1,
  "topic_name": "Name of matched topic",
  "confidence": 0.88,
  "reason": "Detailed subject topic rationale.",
  "evidence": "Keywords/phrases from question matching topic description."
}}

If uncertain, mark unit_number as 0 and topic_name as "Uncertain mapping".
"""

QUALITY_PROMPT_TEMPLATE = """
You are assisting an examination moderator as an AI Decision Support System.
You are NOT the final decision maker.
Label your evaluation clearly as an AI-Assisted Assessment.

Evaluate the overall pedagogical quality of the following examination question based on:
1. Clarity & Precision
2. Technical Specificity
3. Syllabus Relevance & Technical Depth
4. Answerability within allocated marks ({marks} marks)

Question Details:
Subject: {subject_name}
Question Number: {question_number}
Question Text: "{question_text}"
Marks: {marks}

Respond strictly in valid JSON format matching this schema:
{{
  "quality_score": 8.5,
  "confidence": 0.90,
  "reason": "Comprehensive pedagogical reasoning.",
  "issues": ["Minor ambiguity in parameter definitions"],
  "recommendation": "Specify the activation function parameters explicitly."
}}
"""

import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class SimilarityService:
    def __init__(self, threshold: float = 0.65):
        self.threshold = threshold

    def compute_embedding_vector(self, text: str) -> List[float]:
        """Generates text vector for vector store."""
        # Clean text token representation vector
        tokens = [w for w in text.lower().split() if len(w) > 2]
        # Return mock normalized vector
        vec = np.zeros(64)
        for idx, token in enumerate(tokens):
            h = hash(token) % 64
            vec[h] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def find_similar_questions(
        self,
        current_question_text: str,
        previous_questions: List[Dict[str, Any]],
        top_k: int = 3,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        if not previous_questions:
            return []

        previous_questions = [q for q in previous_questions if (q.get("question_text") or "").strip()]
        if not previous_questions or not (current_question_text or "").strip():
            return None
        all_texts = [q["question_text"] for q in previous_questions]
        corpus = [current_question_text] + all_texts
        active_threshold = self.threshold if threshold is None else threshold

        try:
            vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform(corpus)
            
            # Compute cosine similarity between current question (index 0) and all previous (1..)
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            results = []
            for idx, score in enumerate(similarities):
                score_float = float(score)
                if score_float >= active_threshold:
                    prev_q = previous_questions[idx]
                    results.append({
                        "matched_previous_question_id": prev_q["id"],
                        "matched_question_text": prev_q["question_text"],
                        "matched_paper_title": prev_q.get("paper_title", "Previous Question Paper"),
                        "similarity_score": round(score_float, 4),
                        "threshold": active_threshold,
                        "explanation": f"High TF-IDF text similarity ({round(score_float*100, 1)}%) with question from {prev_q.get('paper_title', 'historical question')}. This is a review flag, not a plagiarism finding."
                    })

            # Sort by highest score first
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            return results[:top_k]

        except Exception:
            logger.warning("Historical question similarity could not be computed; evidence is unavailable.")
            return None

similarity_service = SimilarityService()

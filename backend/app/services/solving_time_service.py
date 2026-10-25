from typing import Dict, Any, Optional

class SolvingTimeEstimationService:
    BLOOM_MULTIPLIERS = {
        "K1": 1.0,
        "K2": 1.2,
        "K3": 1.5,
        "K4": 1.7,
        "K5": 1.9,
        "K6": 2.2,
        "Remember": 1.0,
        "Understand": 1.2,
        "Apply": 1.5,
        "Analyze": 1.7,
        "Evaluate": 1.9,
        "Create": 2.2
    }

    @classmethod
    def estimate_question_time(cls, marks: int, bloom_level: str) -> Optional[int]:
        """
        Base formula: 1.5 minutes per mark, scaled by Bloom multiplier.
        """
        if marks is None or marks <= 0 or not bloom_level:
            return None
        multiplier = cls.BLOOM_MULTIPLIERS.get(str(bloom_level).upper()) or cls.BLOOM_MULTIPLIERS.get(str(bloom_level).title())
        if multiplier is None:
            return None
        base_mins = marks * 1.5
        estimated = int(round(base_mins * multiplier))
        return max(estimated, 2)

    @classmethod
    def validate_paper_solving_time(cls, total_estimated_mins: int, allowed_duration_mins: int) -> Dict[str, Any]:
        diff = total_estimated_mins - allowed_duration_mins
        if diff > 0:
            status = "FAIL"
            message = f"Estimated solving time ({total_estimated_mins} mins) exceeds examination duration ({allowed_duration_mins} mins) by {diff} minutes."
        elif abs(diff) <= 15:
            status = "PASS"
            message = f"Estimated solving time ({total_estimated_mins} mins) is well-balanced within examination duration ({allowed_duration_mins} mins)."
        else:
            status = "WARNING"
            message = f"Estimated solving time ({total_estimated_mins} mins) is significantly shorter than examination duration ({allowed_duration_mins} mins) by {abs(diff)} minutes."

        return {
            "estimated_mins": total_estimated_mins,
            "allowed_mins": allowed_duration_mins,
            "difference_mins": diff,
            "status": status,
            "message": message
        }

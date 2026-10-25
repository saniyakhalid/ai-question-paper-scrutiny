import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))

from app.rules.rule_engine import RuleValidationEngine
from app.models.domain_models import RuleStatus

class DummyQuestion:
    def __init__(self, original_number, marks, internal_choice=False, unit_id=1, co_id=1):
        self.original_number = original_number
        self.marks = marks
        self.internal_choice = internal_choice
        self.unit_id_ai = unit_id
        self.co_id_ai = co_id

def test_marks_rule():
    qs = [DummyQuestion("Q1", 50), DummyQuestion("Q2", 50)]
    res = RuleValidationEngine.validate_marks(qs, 100)
    assert res["status"] == RuleStatus.PASS

def test_marks_mismatch():
    qs = [DummyQuestion("Q1", 40), DummyQuestion("Q2", 50)]
    res = RuleValidationEngine.validate_marks(qs, 100)
    assert res["status"] == RuleStatus.FAIL

def test_duplicate_numbering():
    qs = [DummyQuestion("Q1", 10), DummyQuestion("Q1", 10)]
    res = RuleValidationEngine.validate_numbering(qs)
    assert res["status"] == RuleStatus.FAIL

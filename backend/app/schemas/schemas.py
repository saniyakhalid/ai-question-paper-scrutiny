from datetime import datetime
from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from app.models.models import UserRole, PaperStatus, RuleStatus

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = UserRole.FACULTY.value
    department: Optional[str] = None

class UserCreate(UserBase):
    role: UserRole = UserRole.FACULTY
    password: str = Field(min_length=8)

class UserResponse(UserBase):
    id: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

UserOut = UserResponse

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# Subject Document Schemas
class SubjectDocumentBase(BaseModel):
    doc_type: str = "PPT"  # SYLLABUS, CO_DOC, PPT, NOTES, EXAM_PATTERN, RULES, OTHER
    title: str
    academic_year: Optional[str] = None
    semester: Optional[int] = None
    unit_id: Optional[int] = None

class SubjectDocumentCreate(SubjectDocumentBase):
    subject_id: int

class SubjectDocumentResponse(SubjectDocumentBase):
    id: int
    subject_id: int
    unit_id: Optional[int] = None
    filename: str
    # Stored paths stay server-side; authorized users download through the API.
    file_path: Optional[str] = Field(default=None, exclude=True)
    uploaded_by_id: int
    uploaded_by_name: Optional[str] = None
    version: int = 1
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# Examination Schemas
class ExaminationBase(BaseModel):
    title: str
    exam_type: str = "Internal 1"  # Internal 1, Internal 2, End-Sem, Makeup
    academic_year: str
    semester: int
    total_marks: int
    duration_minutes: int
    selected_units: List[int] = []

class ExaminationCreate(ExaminationBase):
    subject_id: int

class ExaminationResponse(ExaminationBase):
    id: int
    subject_id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# Course Outcome Schemas
class CourseOutcomeBase(BaseModel):
    co_code: str
    description: str

class CourseOutcomeCreate(CourseOutcomeBase):
    subject_id: Optional[int] = None

class CourseOutcomeResponse(CourseOutcomeBase):
    id: int
    subject_id: int
    model_config = ConfigDict(from_attributes=True)

CourseOutcomeOut = CourseOutcomeResponse

class CourseOutcomeBatchCreate(BaseModel):
    cos: List[CourseOutcomeBase]

# Syllabus Topic & Unit Schemas
class SyllabusTopicBase(BaseModel):
    topic_name: str
    description: Optional[str] = None
    co_id: Optional[int] = None

class SyllabusTopicCreate(SyllabusTopicBase):
    pass

class SyllabusTopicResponse(SyllabusTopicBase):
    id: int
    unit_id: int
    model_config = ConfigDict(from_attributes=True)

TopicBase = SyllabusTopicBase
TopicCreate = SyllabusTopicCreate
TopicOut = SyllabusTopicResponse

class SyllabusUnitBase(BaseModel):
    unit_number: int
    title: str = "Unit Title"
    unit_title: Optional[str] = None
    description: Optional[str] = None

class SyllabusUnitCreate(SyllabusUnitBase):
    subject_id: Optional[int] = None
    topics: List[SyllabusTopicCreate] = []

class SyllabusUnitResponse(SyllabusUnitBase):
    id: int
    subject_id: int
    topics: List[SyllabusTopicResponse] = []
    documents: List[SubjectDocumentResponse] = []
    model_config = ConfigDict(from_attributes=True)

UnitBase = SyllabusUnitBase
UnitCreate = SyllabusUnitCreate
UnitOut = SyllabusUnitResponse

# Subject Schemas
class SubjectBase(BaseModel):
    code: str
    name: str
    department: str
    branch: str
    semester: int
    academic_year: Optional[str] = None
    total_marks: Optional[int] = None
    duration_minutes: Optional[int] = None
    exam_duration: Optional[int] = None

class SubjectCreate(SubjectBase):
    total_marks: int = Field(gt=0)
    duration_minutes: int = Field(gt=0)
    course_outcomes: List[CourseOutcomeBase] = Field(default_factory=list)
    syllabus_units: List[SyllabusUnitCreate] = Field(default_factory=list)

class SubjectUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1)
    name: Optional[str] = Field(default=None, min_length=1)
    department: Optional[str] = Field(default=None, min_length=1)
    branch: Optional[str] = Field(default=None, min_length=1)
    semester: Optional[int] = Field(default=None, ge=1, le=16)
    academic_year: Optional[str] = None
    total_marks: Optional[int] = Field(default=None, gt=0)
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    exam_duration: Optional[int] = Field(default=None, gt=0)

class SubjectResponse(SubjectBase):
    id: int
    created_at: Optional[datetime] = None
    course_outcomes: List[CourseOutcomeResponse] = []
    syllabus_units: List[SyllabusUnitResponse] = []
    documents: List[SubjectDocumentResponse] = []
    model_config = ConfigDict(from_attributes=True)

SubjectOut = SubjectResponse

# Examination Pattern Schema
class ExamPatternBase(BaseModel):
    total_marks: int = Field(default=100, gt=0)
    duration_minutes: int = Field(default=180, gt=0)
    exam_duration_mins: Optional[int] = Field(default=None, gt=0)
    choice_pattern: str = "Standard Choice"
    min_co_coverage_pct: Optional[float] = Field(default=None, ge=0, le=100)
    min_unit_coverage_pct: Optional[float] = Field(default=None, ge=0, le=100)
    # Legacy field names remain accepted for clients that predate the percentage suffix.
    min_co_coverage: Optional[float] = Field(default=None, ge=0, le=100)
    min_unit_coverage: Optional[float] = Field(default=None, ge=0, le=100)
    min_higher_order_bloom_pct: Optional[float] = Field(default=None, ge=0, le=100)
    internal_choice_required: Optional[bool] = None
    solve_time_limit_pct: Optional[float] = Field(default=None, ge=0, le=1000)
    similarity_threshold: Optional[float] = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def normalize_legacy_threshold_names(self):
        if self.min_co_coverage_pct is None and self.min_co_coverage is not None:
            self.min_co_coverage_pct = self.min_co_coverage
        elif self.min_co_coverage is None and self.min_co_coverage_pct is not None:
            self.min_co_coverage = self.min_co_coverage_pct
        if self.min_unit_coverage_pct is None and self.min_unit_coverage is not None:
            self.min_unit_coverage_pct = self.min_unit_coverage
        elif self.min_unit_coverage is None and self.min_unit_coverage_pct is not None:
            self.min_unit_coverage = self.min_unit_coverage_pct
        if self.exam_duration_mins is None:
            self.exam_duration_mins = self.duration_minutes
        return self

class ExamPatternCreate(ExamPatternBase):
    pass

class ExamPatternResponse(ExamPatternBase):
    id: int
    subject_id: int
    model_config = ConfigDict(from_attributes=True)

ExamPatternOut = ExamPatternResponse

# Question Paper & Question Schemas
class ExtractedQuestionResponse(BaseModel):
    id: int
    question_number: str = "Q1"
    original_number: Optional[str] = None
    sub_question: Optional[str] = None
    question_text: str
    original_text: str = ""
    marks: Optional[int] = None  # None when marks are missing/not detected
    internal_choice: bool = False
    section_name: Optional[str] = None
    sequence_order: int = 1
    detected_unit_number: Optional[int] = None
    is_unit_selected: bool = True
    unit_validation_status: str = "VALID"
    question_type: Optional[str] = "QUESTION"
    parent_question_id: Optional[int] = None
    choice_group_id: Optional[str] = None
    parse_confidence: Optional[float] = 1.0
    marks_confidence: Optional[float] = None
    metadata_confidence: Optional[float] = None
    co_code: Optional[str] = None
    bloom_level: Optional[str] = None
    topic_name: Optional[str] = None
    raw_text: Optional[str] = None
    normalized_text: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

QuestionOut = ExtractedQuestionResponse

class QuestionPaperResponse(BaseModel):
    id: int
    title: str
    file_path: str = ""
    filepath: Optional[str] = None
    file_type: str = "pdf"
    subject_id: int
    examination_id: Optional[int] = None
    uploaded_by_id: int
    academic_year: str
    exam_type: str
    selected_units_json: Optional[List[int]] = None
    status: str
    validation_status: Optional[str] = None
    validation_details: Optional[Dict[str, Any]] = None
    overall_score: Optional[float] = None
    version: int = 1
    raw_text: Optional[str] = None
    normalized_text: Optional[str] = None
    instructions_json: Optional[List[str]] = None
    uploaded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    questions: List[ExtractedQuestionResponse] = []
    subject: Optional[SubjectResponse] = None
    moderator_review: Optional[Dict[str, Any]] = None
    moderator_feedback: Optional[str] = None
    moderator_decision: Optional[str] = None
    moderator_required_action: Optional[str] = None
    moderator_name: Optional[str] = None
    moderated_at: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

PaperOut = QuestionPaperResponse

# Previous Question Paper Schemas
class PreviousQuestionResponse(BaseModel):
    id: int
    question_number: str = "Q1"
    question_text: str
    marks: Optional[int] = None
    bloom_level: Optional[str] = None
    co_code: Optional[str] = None
    unit_number: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class PreviousPaperResponse(BaseModel):
    id: int
    subject_id: int
    academic_year: str
    exam_type: str
    title: str
    uploaded_at: Optional[datetime] = None
    questions: List[PreviousQuestionResponse] = []
    model_config = ConfigDict(from_attributes=True)

# Rule Result Schema
class RuleResultResponse(BaseModel):
    id: Union[int, str]
    rule_name: str
    category: str
    expected_value: str = ""
    actual_value: str = ""
    expected: Optional[str] = None
    actual: Optional[str] = None
    status: str
    message: str
    model_config = ConfigDict(from_attributes=True)

RuleResultOut = RuleResultResponse

# Scrutiny Finding & Report Schemas
class ScrutinyFindingResponse(BaseModel):
    id: Union[int, str]
    question_id: Optional[int] = None
    finding_type: str = "BLOOM"
    category: Optional[str] = None
    ai_value: str = ""
    finding_text: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    evidence: Optional[str] = None
    suggested_improvement: Optional[str] = None
    recommendation: Optional[str] = None
    issues: Optional[List[Dict[str, Any]]] = None
    model_config = ConfigDict(from_attributes=True)

FindingOut = ScrutinyFindingResponse

class SimilarityResultResponse(BaseModel):
    id: Union[int, str]
    question_id: int
    question_number: Optional[str] = None
    matched_previous_question_id: Optional[int] = None
    similarity_score: float
    explanation: Optional[str] = None
    matched_question_text: Optional[str] = None
    matched_paper_title: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ScrutinyReportResponse(BaseModel):
    id: Union[int, str]
    paper_id: int
    version: int = 1
    overall_score: Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    analysis_mode: Optional[str] = None
    analysis_notice: Optional[str] = None
    evidence_coverage_pct: Optional[float] = None
    analysis_confidence: Optional[float] = None
    compliance_summary: Optional[str] = None
    compliance_status: Optional[str] = None
    solving_time_minutes: Optional[float] = None
    created_at: Optional[datetime] = None
    findings: List[ScrutinyFindingResponse] = []
    rule_results: List[RuleResultResponse] = []
    similarity_results: List[SimilarityResultResponse] = []
    model_config = ConfigDict(from_attributes=True)

ScrutinyReportOut = ScrutinyReportResponse

# Moderator Review & Correction Schemas
class ModeratorCorrectionCreate(BaseModel):
    question_id: int
    finding_type: str = "BLOOM"
    category: Optional[str] = None
    original_ai_value: str = ""
    corrected_value: str
    reason: Optional[str] = None

ModeratorCorrectionRequest = ModeratorCorrectionCreate

class ModeratorCorrectionResponse(ModeratorCorrectionCreate):
    id: int
    review_id: Optional[int] = None
    paper_id: Optional[int] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

ModeratorCorrectionOut = ModeratorCorrectionResponse

class ModeratorReviewCreate(BaseModel):
    decision: str = "APPROVED"
    new_status: Optional[str] = None
    remarks: str = Field(min_length=1, max_length=4000)
    required_action: Optional[str] = None
    corrections: List[ModeratorCorrectionCreate] = []

    @model_validator(mode="after")
    def require_non_blank_moderator_remarks(self):
        if not self.remarks.strip():
            raise ValueError("Moderator remarks are required for every decision.")
        return self

ModeratorDecisionRequest = ModeratorReviewCreate

class ModeratorReviewResponse(BaseModel):
    id: int
    paper_id: int
    report_id: Optional[int] = None
    moderator_id: int
    decision: str = "APPROVED"
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    corrections: List[ModeratorCorrectionResponse] = []
    model_config = ConfigDict(from_attributes=True)

# Audit Log Schema
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_role: Optional[str] = None
    action: str
    entity_type: str = "PAPER"
    entity: Optional[str] = None
    entity_id: Optional[int] = None
    details: Optional[str] = None
    timestamp: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

AuditLogOut = AuditLogResponse

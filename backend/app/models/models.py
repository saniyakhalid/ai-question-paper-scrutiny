import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship
from app.db.database import Base

class UserRole(str, enum.Enum):
    FACULTY = "FACULTY"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"

class PaperStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    EXTRACTED = "EXTRACTED"
    ANALYZED = "ANALYZED"
    PARSED = "PARSED"
    ANALYZING = "ANALYZING"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    NEEDS_MODIFICATION = "NEEDS_MODIFICATION"
    MODIFICATION_REQUIRED = "MODIFICATION_REQUIRED"
    REJECTED = "REJECTED"
    REVIEW_DECLINED = "REVIEW_DECLINED"
    DECLINED = "REVIEW_DECLINED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    FAILED = "FAILED"

class RuleStatus(str, enum.Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.FACULTY.value, nullable=False)
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    uploaded_papers = relationship("QuestionPaper", back_populates="uploaded_by")
    reviews = relationship("ModeratorReview", back_populates="moderator")
    audit_logs = relationship("AuditLog", back_populates="user")
    subject_documents = relationship("SubjectDocument", back_populates="uploaded_by")

class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    branch = Column(String(100), nullable=False)
    semester = Column(Integer, nullable=False)
    total_marks = Column(Integer, default=100)
    duration_minutes = Column(Integer, default=180)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    course_outcomes = relationship("CourseOutcome", back_populates="subject", cascade="all, delete-orphan")
    syllabus_units = relationship("SyllabusUnit", back_populates="subject", cascade="all, delete-orphan")
    exam_pattern = relationship("ExamPattern", back_populates="subject", uselist=False, cascade="all, delete-orphan")
    question_papers = relationship("QuestionPaper", back_populates="subject")
    previous_papers = relationship("PreviousPaper", back_populates="subject")
    documents = relationship("SubjectDocument", back_populates="subject", cascade="all, delete-orphan")
    examinations = relationship("Examination", back_populates="subject", cascade="all, delete-orphan")

    @property
    def exam_duration(self):
        return self.duration_minutes

    @exam_duration.setter
    def exam_duration(self, val):
        self.duration_minutes = val

class SubjectDocument(Base):
    __tablename__ = "subject_documents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("syllabus_units.id"), nullable=True)
    doc_type = Column(String(50), nullable=False, default="PPT")  # SYLLABUS, CO_DOC, PPT, NOTES, EXAM_PATTERN, RULES, OTHER
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    academic_year = Column(String(50), nullable=False, default="2025-2026")
    semester = Column(Integer, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    version = Column(Integer, default=1)
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subject = relationship("Subject", back_populates="documents")
    unit = relationship("SyllabusUnit", back_populates="documents")
    uploaded_by = relationship("User", back_populates="subject_documents")

class Examination(Base):
    __tablename__ = "examinations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    exam_type = Column(String(50), nullable=False)  # Internal 1, Internal 2, End-Sem, Makeup
    academic_year = Column(String(50), nullable=False)
    semester = Column(Integer, nullable=False)
    total_marks = Column(Integer, default=100)
    duration_minutes = Column(Integer, default=180)
    selected_units_json = Column(JSON, nullable=False)  # e.g., [1, 2]
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subject = relationship("Subject", back_populates="examinations")
    question_papers = relationship("QuestionPaper", back_populates="examination")

class CourseOutcome(Base):
    __tablename__ = "course_outcomes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    co_code = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)

    subject = relationship("Subject", back_populates="course_outcomes")
    topics = relationship("SyllabusTopic", back_populates="co")

class SyllabusUnit(Base):
    __tablename__ = "syllabus_units"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    unit_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False, default="Unit Title")
    description = Column(Text, nullable=True)

    subject = relationship("Subject", back_populates="syllabus_units")
    topics = relationship("SyllabusTopic", back_populates="unit", cascade="all, delete-orphan")
    documents = relationship("SubjectDocument", back_populates="unit", cascade="all, delete-orphan")

    @property
    def unit_title(self):
        return self.title

    @unit_title.setter
    def unit_title(self, val):
        self.title = val

class SyllabusTopic(Base):
    __tablename__ = "syllabus_topics"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("syllabus_units.id"), nullable=False)
    topic_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    co_id = Column(Integer, ForeignKey("course_outcomes.id"), nullable=True)

    unit = relationship("SyllabusUnit", back_populates="topics")
    co = relationship("CourseOutcome", back_populates="topics")

class ExamPattern(Base):
    __tablename__ = "examination_patterns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), unique=True, nullable=False)
    total_marks = Column(Integer, default=100)
    duration_minutes = Column(Integer, default=180)
    choice_pattern = Column(String(255), default="Standard Choice")
    min_co_coverage_pct = Column(Float, nullable=True, default=None)
    min_unit_coverage_pct = Column(Float, nullable=True, default=None)
    min_higher_order_bloom_pct = Column(Float, nullable=True, default=None)
    internal_choice_required = Column(Boolean, nullable=True, default=None)
    solve_time_limit_pct = Column(Float, nullable=True, default=None)
    similarity_threshold = Column(Float, nullable=True, default=None)

    subject = relationship("Subject", back_populates="exam_pattern")

    @property
    def exam_duration_mins(self):
        return self.duration_minutes

    @exam_duration_mins.setter
    def exam_duration_mins(self, val):
        self.duration_minutes = val

    @property
    def min_co_coverage(self):
        return self.min_co_coverage_pct

    @min_co_coverage.setter
    def min_co_coverage(self, val):
        self.min_co_coverage_pct = val

    @property
    def min_unit_coverage(self):
        return self.min_unit_coverage_pct

    @min_unit_coverage.setter
    def min_unit_coverage(self, val):
        self.min_unit_coverage_pct = val

ExaminationPattern = ExamPattern

class QuestionPaper(Base):
    __tablename__ = "question_papers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    examination_id = Column(Integer, ForeignKey("examinations.id"), nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(512), nullable=False, default="")
    file_type = Column(String(50), nullable=False, default="pdf")
    academic_year = Column(String(50), nullable=False)
    exam_type = Column(String(50), nullable=False)
    selected_units_json = Column(JSON, nullable=True)  # List of selected units e.g. [1, 2]
    status = Column(String(50), default=PaperStatus.SUBMITTED.value, nullable=False)
    overall_score = Column(Float, nullable=True)
    version = Column(Integer, default=1)
    raw_text = Column(Text, nullable=True)
    normalized_text = Column(Text, nullable=True)
    instructions_json = Column(JSON, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subject = relationship("Subject", back_populates="question_papers")
    examination = relationship("Examination", back_populates="question_papers")
    uploaded_by = relationship("User", back_populates="uploaded_papers")
    questions = relationship("ExtractedQuestion", back_populates="paper", cascade="all, delete-orphan", foreign_keys="[ExtractedQuestion.paper_id]")
    reports = relationship("ScrutinyReport", back_populates="paper", cascade="all, delete-orphan")
    reviews = relationship("ModeratorReview", back_populates="paper", cascade="all, delete-orphan")
    corrections = relationship("ModeratorCorrection", back_populates="paper", cascade="all, delete-orphan")

    @property
    def filepath(self):
        return self.file_path

    @filepath.setter
    def filepath(self, val):
        self.file_path = val

    @property
    def filename(self):
        return self.title

    @filename.setter
    def filename(self, val):
        self.title = val

    @property
    def uploaded_by_user(self):
        return self.uploaded_by

    @property
    def scrutiny_reports(self):
        return self.reports

class ExtractedQuestion(Base):
    __tablename__ = "extracted_questions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("question_papers.id"), nullable=False)
    question_number = Column(String(50), nullable=False, default="Q1")
    sub_question = Column(String(50), nullable=True)
    question_text = Column(Text, nullable=False)
    original_text = Column(Text, nullable=False, default="")
    marks = Column(Integer, nullable=True)  # Nullable: never invent fake default marks
    internal_choice = Column(Boolean, default=False)
    section_name = Column(String(50), nullable=True)
    sequence_order = Column(Integer, default=1)

    # Document Hierarchy & Classification
    question_type = Column(String(50), default="QUESTION", nullable=True)  # QUESTION, SUBQUESTION, QUESTION_GROUP
    parent_question_id = Column(Integer, ForeignKey("extracted_questions.id"), nullable=True)
    choice_group_id = Column(String(100), nullable=True)
    parse_confidence = Column(Float, default=1.0, nullable=True)
    marks_confidence = Column(Float, nullable=True)
    metadata_confidence = Column(Float, nullable=True)

    # Metadata explicitly printed or parsed
    co_code = Column(String(20), nullable=True)
    bloom_level = Column(String(50), nullable=True)
    detected_unit_number = Column(Integer, nullable=True)
    topic_name = Column(String(255), nullable=True)
    raw_text = Column(Text, nullable=True)
    normalized_text = Column(Text, nullable=True)

    # Unit & Syllabus mapping
    is_unit_selected = Column(Boolean, default=True)
    unit_validation_status = Column(String(50), default="VALID")  # VALID, UNSELECTED_UNIT, UNMAPPED

    paper = relationship("QuestionPaper", back_populates="questions", foreign_keys=[paper_id])
    subquestions = relationship("ExtractedQuestion", backref="parent_question", remote_side=[id])
    findings = relationship("ScrutinyFinding", back_populates="question", cascade="all, delete-orphan")

    @property
    def original_number(self):
        return self.question_number

    @original_number.setter
    def original_number(self, val):
        self.question_number = val

    @property
    def sub_number(self):
        return self.sub_question

    @sub_number.setter
    def sub_number(self, val):
        self.sub_question = val

    @property
    def section(self):
        return self.section_name

    @section.setter
    def section(self, val):
        self.section_name = val

Question = ExtractedQuestion

class PreviousPaper(Base):
    __tablename__ = "previous_papers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    academic_year = Column(String(50), nullable=False, default="2024-2025")
    exam_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subject = relationship("Subject", back_populates="previous_papers")
    questions = relationship("PreviousQuestion", back_populates="paper", cascade="all, delete-orphan")

    @property
    def year(self):
        return self.academic_year

    @year.setter
    def year(self, val):
        self.academic_year = val

    @property
    def filepath(self):
        return self.file_path

    @filepath.setter
    def filepath(self, val):
        self.file_path = val

    @property
    def filename(self):
        return self.title

    @filename.setter
    def filename(self, val):
        self.title = val

class PreviousQuestion(Base):
    __tablename__ = "previous_questions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("previous_papers.id"), nullable=False)
    question_number = Column(String(50), nullable=False, default="Q1")
    question_text = Column(Text, nullable=False)
    marks = Column(Integer, nullable=True)  # Never invent default marks
    bloom_level = Column(String(50), nullable=True)
    co_code = Column(String(20), nullable=True)
    unit_number = Column(Integer, nullable=True)

    paper = relationship("PreviousPaper", back_populates="questions")
    embedding = relationship("QuestionEmbedding", back_populates="previous_question", uselist=False, cascade="all, delete-orphan")

class QuestionEmbedding(Base):
    __tablename__ = "question_embeddings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    previous_question_id = Column(Integer, ForeignKey("previous_questions.id"), nullable=False)
    vector_json = Column(Text, nullable=False)

    previous_question = relationship("PreviousQuestion", back_populates="embedding")

class ScrutinyReport(Base):
    __tablename__ = "scrutiny_reports"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("question_papers.id"), nullable=False)
    version = Column(Integer, default=1)
    overall_score = Column(Float, nullable=False, default=0.0)
    compliance_summary = Column(Text, nullable=True)
    compliance_status = Column(String(50), nullable=True)
    summary_json = Column(JSON, nullable=True)
    solving_time_minutes = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    paper = relationship("QuestionPaper", back_populates="reports")
    findings = relationship("ScrutinyFinding", back_populates="report", cascade="all, delete-orphan")
    rule_results = relationship("RuleResult", back_populates="report", cascade="all, delete-orphan")
    similarity_results = relationship("SimilarityResult", back_populates="report", cascade="all, delete-orphan")
    reviews = relationship("ModeratorReview", back_populates="report")

class ScrutinyFinding(Base):
    __tablename__ = "scrutiny_findings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("scrutiny_reports.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("extracted_questions.id"), nullable=True)
    finding_type = Column(String(100), nullable=False)
    ai_value = Column(String(255), nullable=False, default="")
    confidence = Column(Float, default=0.0)
    reasoning = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    suggested_improvement = Column(Text, nullable=True)

    report = relationship("ScrutinyReport", back_populates="findings")
    question = relationship("ExtractedQuestion", back_populates="findings")

    @property
    def category(self):
        return self.finding_type

    @category.setter
    def category(self, val):
        self.finding_type = val

    @property
    def severity(self):
        return "WARNING" if self.confidence < 0.8 else "INFO"

    @property
    def finding_text(self):
        return f"{self.finding_type}: {self.ai_value}"

    @property
    def recommendation(self):
        return self.suggested_improvement

class RuleResult(Base):
    __tablename__ = "rule_results"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("scrutiny_reports.id"), nullable=False)
    rule_name = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    expected_value = Column(String(255), nullable=False)
    actual_value = Column(String(255), nullable=False)
    status = Column(String(50), default=RuleStatus.PASS.value)
    message = Column(Text, nullable=False)

    report = relationship("ScrutinyReport", back_populates="rule_results")

    @property
    def expected(self):
        return self.expected_value

    @expected.setter
    def expected(self, val):
        self.expected_value = val

    @property
    def actual(self):
        return self.actual_value

    @actual.setter
    def actual(self, val):
        self.actual_value = val

class SimilarityResult(Base):
    __tablename__ = "similarity_results"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("scrutiny_reports.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("extracted_questions.id"), nullable=False)
    matched_previous_question_id = Column(Integer, ForeignKey("previous_questions.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False, default=70.0)
    status = Column(String(50), nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    report = relationship("ScrutinyReport", back_populates="similarity_results")
    matched_question = relationship("PreviousQuestion")

    @property
    def previous_question_id(self):
        return self.matched_previous_question_id

    @previous_question_id.setter
    def previous_question_id(self, val):
        self.matched_previous_question_id = val

class ModeratorReview(Base):
    __tablename__ = "moderator_reviews"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("question_papers.id"), nullable=False)
    report_id = Column(Integer, ForeignKey("scrutiny_reports.id"), nullable=True)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(String(50), nullable=False)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    paper = relationship("QuestionPaper", back_populates="reviews")
    report = relationship("ScrutinyReport", back_populates="reviews")
    moderator = relationship("User", back_populates="reviews")
    corrections = relationship("ModeratorCorrection", back_populates="review", cascade="all, delete-orphan")

class ModeratorCorrection(Base):
    __tablename__ = "moderator_corrections"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("moderator_reviews.id"), nullable=True)
    paper_id = Column(Integer, ForeignKey("question_papers.id"), nullable=True)
    question_id = Column(Integer, ForeignKey("extracted_questions.id"), nullable=False)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    finding_type = Column(String(100), nullable=False, default="BLOOM")
    category = Column(String(100), nullable=True)
    original_ai_value = Column(Text, nullable=False)
    corrected_value = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    review = relationship("ModeratorReview", back_populates="corrections")
    paper = relationship("QuestionPaper", back_populates="corrections")
    question = relationship("ExtractedQuestion")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False, default="PAPER")
    entity = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="audit_logs")

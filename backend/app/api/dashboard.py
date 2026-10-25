from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from pymongo.database import Database
from pymongo import DESCENDING

from app.db.mongo import get_db, serialize_doc, serialize_docs
from app.core.dependencies import get_current_user, MongoUser

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/public-stats", response_model=Dict[str, Any])
def get_public_landing_stats(db: Database = Depends(get_db)):
    """Public statistical counters for the college landing page."""
    total_papers = db.question_papers.count_documents({})
    analyzed_papers = db.question_papers.count_documents({"overall_score": {"$ne": None}})
    subjects_count = db.subjects.count_documents({})

    reports = list(db.scrutiny_reports.find({"overall_score": {"$ne": None}}))
    avg_score = round(sum(r["overall_score"] for r in reports) / len(reports), 1) if reports else None

    pass_rules = db.rule_results.count_documents({"status": "PASS"})
    total_rules = db.rule_results.count_documents({})
    compliance_rate = round((pass_rules / total_rules) * 100, 1) if total_rules > 0 else None

    return {
        "total_papers_analyzed": analyzed_papers,
        "active_curriculum_subjects": subjects_count,
        "avg_scrutiny_score": avg_score,
        "rule_compliance_rate": compliance_rate,
        "institution_name": "Autonomous Engineering College & Examination Cell"
    }


@router.get("/stats", response_model=Dict[str, Any])
def get_dashboard_stats(
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    """Authenticated dashboard statistics with strict role filtering."""
    query = {}
    if current_user.role == "FACULTY":
        query["uploaded_by_id"] = current_user.id

    total_papers = db.question_papers.count_documents(query)
    
    pending_query = dict(query)
    pending_query["status"] = {"$in": ["PARSED", "ANALYZING", "PENDING_REVIEW", "SUBMITTED"]}
    pending_reviews = db.question_papers.count_documents(pending_query)

    appr_query = dict(query)
    appr_query["status"] = "APPROVED"
    approved_papers = db.question_papers.count_documents(appr_query)

    mod_query = dict(query)
    mod_query["status"] = "MODIFICATION_REQUIRED"
    needs_mod = db.question_papers.count_documents(mod_query)

    rej_query = dict(query)
    rej_query["status"] = "REJECTED"
    rejected = db.question_papers.count_documents(rej_query)

    dec_query = dict(query)
    dec_query["status"] = {"$in": ["REVIEW_DECLINED", "DECLINED"]}
    declined = db.question_papers.count_documents(dec_query)

    # Average score
    paper_ids = [p["id"] for p in db.question_papers.find(query, {"id": 1})]
    reports = list(db.scrutiny_reports.find({"paper_id": {"$in": paper_ids}, "overall_score": {"$ne": None}}))
    avg_score = round(sum(r["overall_score"] for r in reports) / len(reports), 1) if reports else None

    # Bloom distribution
    scoped_reports = list(db.scrutiny_reports.find({"paper_id": {"$in": paper_ids}}, {"id": 1}))
    scoped_report_ids = [r.get("id") for r in scoped_reports]
    bloom_findings = list(db.scrutiny_findings.find({
        "report_id": {"$in": scoped_report_ids}, "finding_type": "BLOOM"
    })) if scoped_report_ids else []
    bloom_dist = {"Remember (K1)": 0, "Understand (K2)": 0, "Apply (K3)": 0, "Analyze (K4)": 0, "Evaluate (K5)": 0, "Create (K6)": 0}
    for bf in bloom_findings:
        v = str(bf.get("ai_value", "")).upper()
        if "K1" in v or "REMEMBER" in v:
            bloom_dist["Remember (K1)"] += 1
        elif "K2" in v or "UNDERSTAND" in v:
            bloom_dist["Understand (K2)"] += 1
        elif "K3" in v or "APPLY" in v:
            bloom_dist["Apply (K3)"] += 1
        elif "K4" in v or "ANALYZE" in v:
            bloom_dist["Analyze (K4)"] += 1
        elif "K5" in v or "EVALUATE" in v:
            bloom_dist["Evaluate (K5)"] += 1
        elif "K6" in v or "CREATE" in v:
            bloom_dist["Create (K6)"] += 1
        # Unclassified questions remain unclassified; they are not counted as Understand.

    bloom_chart_data = [{"level": k, "count": v} for k, v in bloom_dist.items()]

    # Status distribution
    status_chart_data = [
        {"name": "Approved", "value": approved_papers, "color": "#10B981"},
        {"name": "Needs Modification", "value": needs_mod, "color": "#F59E0B"},
        {"name": "Rejected", "value": rejected, "color": "#EF4444"},
        {"name": "Review Declined", "value": declined, "color": "#94A3B8"},
        {"name": "Pending Review", "value": pending_reviews, "color": "#6366F1"}
    ]

    # Recent papers
    recent = list(db.question_papers.find(query).sort("id", DESCENDING).limit(8))
    recent_list = []
    for p in recent:
        subject = db.subjects.find_one({"id": p.get("subject_id")}) or {}
        uploader = db.users.find_one({"id": p.get("uploaded_by_id")}) or {}
        recent_list.append({
            "id": p.get("id"),
            "title": p.get("title"),
            "subject_code": subject.get("code", "N/A"),
            "subject_name": subject.get("name", "N/A"),
            "uploaded_by": uploader.get("full_name", "Faculty"),
            "status": p.get("status"),
            "overall_score": p.get("overall_score"),
            "uploaded_at": p.get("uploaded_at") or "",
            "moderator_decision": p.get("moderator_decision"),
            "moderator_feedback": p.get("moderator_feedback"),
            "moderator_name": p.get("moderator_name"),
            "moderated_at": p.get("moderated_at"),
        })

    return {
        "cards": {
            "total_papers": total_papers,
            "pending_reviews": pending_reviews,
            "approved": approved_papers,
            "needs_modification": needs_mod,
            "rejected": rejected,
            "declined": declined,
            "avg_scrutiny_score": avg_score
        },
        "bloom_distribution": bloom_chart_data,
        "status_distribution": status_chart_data,
        "recent_papers": recent_list
    }

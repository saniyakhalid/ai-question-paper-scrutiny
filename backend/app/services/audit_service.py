from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.db.mongo import get_next_sequence, serialize_doc

class AuditService:
    @staticmethod
    def log_action(
        db,
        action: str,
        entity: str,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        user_role: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        details: Optional[str] = None
    ) -> dict:
        entry_id = get_next_sequence("audit_logs")
        log_entry = {
            "id": entry_id,
            "action": action,
            "entity": entity,
            "entity_type": entity,
            "entity_id": entity_id,
            "user_id": user_id,
            "user_role": user_role,
            "details": details or f"{action} performed on {entity} #{entity_id}",
            "metadata_json": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        db.audit_logs.insert_one(log_entry)
        return serialize_doc(log_entry)

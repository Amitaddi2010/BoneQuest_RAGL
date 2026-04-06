# ============================================================
# BoneQuest v2 — Audit Logger
# ============================================================

import os
import json
from datetime import datetime
from typing import List, Optional
from models.schemas import QueryResponse, TraceStep


class AuditLogger:
    """
    Logs all AI query interactions for clinical compliance.
    
    In production, this would write to a database with:
    - Full reasoning traces
    - User role context
    - Response confidence scores
    - Exact page citations
    - Timestamp and session metadata
    """

    def __init__(self, log_dir: str = "data/audit_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def log_query(self, query_response: QueryResponse, original_query: str):
        """Log a complete query interaction."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query_id": query_response.id,
            "original_query": original_query,
            "role": query_response.role,
            "model": query_response.model,
            "confidence": query_response.confidence,
            "citations": query_response.citations,
            "reasoning_trace": [
                {"step": t.step, "action": t.action, "detail": t.detail}
                for t in query_response.reasoning_trace
            ],
            "answer_length": len(query_response.answer),
        }

        log_file = os.path.join(
            self.log_dir,
            f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_logs(self, date: Optional[str] = None) -> List[dict]:
        """Retrieve audit logs for a given date."""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        log_file = os.path.join(self.log_dir, f"audit_{date}.jsonl")
        
        if not os.path.exists(log_file):
            return []

        logs = []
        with open(log_file, "r") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        return logs

    def export_trace(self, query_id: str) -> Optional[dict]:
        """Export a specific query's reasoning trace for compliance."""
        # Scan all log files
        for filename in os.listdir(self.log_dir):
            if filename.endswith('.jsonl'):
                with open(os.path.join(self.log_dir, filename), "r") as f:
                    for line in f:
                        entry = json.loads(line)
                        if entry.get("query_id") == query_id:
                            return entry
        return None

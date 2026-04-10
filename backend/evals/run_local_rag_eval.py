import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.schemas import UserRole
from database import SessionLocal
from config import settings
from services.context_chat_engine import ContextChatEngine


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _contains_any(text: str, values: List[str]) -> bool:
    t = _normalize(text)
    return any(_normalize(v) in t for v in (values or []))


async def _run_one(engine: ContextChatEngine, case: Dict[str, Any]) -> Dict[str, Any]:
    final_payload: Dict[str, Any] = {}
    db = SessionLocal()
    async for ev in engine.generate_response_stream(
        db=db,
        query=case["query"],
        role=UserRole.consultant,
        document_id=case.get("document_id", "global"),
        history=[],
    ):
        if ev.get("type") == "final_payload":
            final_payload = ev.get("data", {}) or {}
    db.close()

    answer = final_payload.get("answer", "")
    citations = final_payload.get("citations", []) or []
    validation = final_payload.get("validation", {}) or {}
    retrieval = final_payload.get("retrieval", {}) or {}

    citation_blob = " ".join(
        [
            str(c.get("section", "")) + " " + str(c.get("snippet", "")) + " " + str(c.get("content", ""))
            for c in citations
        ]
    )
    retrieval_hit = _contains_any(citation_blob, case.get("expected_keywords_any", []))
    answer_hit = _contains_any(answer, case.get("expected_answer_contains_any", []))
    evidence_level = validation.get("evidence_level", "none")
    contradiction = bool(validation.get("contradiction", False))

    return {
        "id": case.get("id"),
        "query": case.get("query"),
        "is_mcq": bool(case.get("is_mcq", False)),
        "retrieval_used": bool(retrieval.get("used_rag", len(citations) > 0)),
        "retrieval_source": retrieval.get("source", "unknown"),
        "citations_count": len(citations),
        "retrieval_hit": retrieval_hit,
        "answer_hit": answer_hit,
        "evidence_level": evidence_level,
        "contradiction": contradiction,
        "confidence": float(final_payload.get("confidence", 0.0) or 0.0),
    }


async def run_eval(eval_set_path: str) -> Dict[str, Any]:
    engine = ContextChatEngine()
    cases = json.loads(Path(eval_set_path).read_text(encoding="utf-8"))
    results: List[Dict[str, Any]] = []
    for case in cases:
        results.append(await _run_one(engine, case))

    total = len(results)
    retrieval_hit_rate = (sum(1 for r in results if r["retrieval_hit"]) / total) if total else 0.0
    answer_hit_rate = (sum(1 for r in results if r["answer_hit"]) / total) if total else 0.0
    contradiction_rate = (sum(1 for r in results if r["contradiction"]) / total) if total else 0.0
    rag_usage_rate = (sum(1 for r in results if r["retrieval_used"]) / total) if total else 0.0

    return {
        "total_cases": total,
        "retrieval_hit_rate": round(retrieval_hit_rate, 3),
        "answer_hit_rate": round(answer_hit_rate, 3),
        "contradiction_rate": round(contradiction_rate, 3),
        "rag_usage_rate": round(rag_usage_rate, 3),
        "results": results,
    }


def _delta(a: float, b: float) -> float:
    return round(float(b) - float(a), 3)


async def run_eval_comparison(eval_set_path: str) -> Dict[str, Any]:
    original_flag = bool(getattr(settings, "ENABLE_HYBRID_RERANK", False))
    original_env = os.getenv("ENABLE_HYBRID_RERANK")
    try:
        settings.ENABLE_HYBRID_RERANK = False
        os.environ["ENABLE_HYBRID_RERANK"] = "false"
        baseline = await run_eval(eval_set_path)

        settings.ENABLE_HYBRID_RERANK = True
        os.environ["ENABLE_HYBRID_RERANK"] = "true"
        reranked = await run_eval(eval_set_path)
    finally:
        settings.ENABLE_HYBRID_RERANK = original_flag
        if original_env is None:
            os.environ.pop("ENABLE_HYBRID_RERANK", None)
        else:
            os.environ["ENABLE_HYBRID_RERANK"] = original_env

    summary = {
        "total_cases": baseline.get("total_cases", 0),
        "baseline": {
            "retrieval_hit_rate": baseline.get("retrieval_hit_rate", 0.0),
            "answer_hit_rate": baseline.get("answer_hit_rate", 0.0),
            "contradiction_rate": baseline.get("contradiction_rate", 0.0),
            "rag_usage_rate": baseline.get("rag_usage_rate", 0.0),
        },
        "reranked": {
            "retrieval_hit_rate": reranked.get("retrieval_hit_rate", 0.0),
            "answer_hit_rate": reranked.get("answer_hit_rate", 0.0),
            "contradiction_rate": reranked.get("contradiction_rate", 0.0),
            "rag_usage_rate": reranked.get("rag_usage_rate", 0.0),
        },
        "delta": {
            "retrieval_hit_rate": _delta(baseline.get("retrieval_hit_rate", 0.0), reranked.get("retrieval_hit_rate", 0.0)),
            "answer_hit_rate": _delta(baseline.get("answer_hit_rate", 0.0), reranked.get("answer_hit_rate", 0.0)),
            "contradiction_rate": _delta(baseline.get("contradiction_rate", 0.0), reranked.get("contradiction_rate", 0.0)),
            "rag_usage_rate": _delta(baseline.get("rag_usage_rate", 0.0), reranked.get("rag_usage_rate", 0.0)),
        },
        "baseline_results": baseline.get("results", []),
        "reranked_results": reranked.get("results", []),
    }
    return summary


if __name__ == "__main__":
    eval_file = str(Path(__file__).with_name("local_rag_eval_set.json"))
    payload = asyncio.run(run_eval_comparison(eval_file))
    print(json.dumps(payload, indent=2))

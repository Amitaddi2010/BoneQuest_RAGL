import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import QueryRequest, QueryResponse, TraceStep, UserRole
from services.pageindex_engine import PAGEINDEX_API_KEY
from pageindex.client import PageIndexClient

router = APIRouter()
pi_client = PageIndexClient(api_key=PAGEINDEX_API_KEY)

@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Submit a clinical query. (Non-streaming)"""
    try:
        messages = [
            {"role": "system", "content": f"You are a clinical assistant. Role: {request.role}"},
            {"role": "user", "content": request.query}
        ]
        response = pi_client.chat_completions(
            messages=messages,
            doc_id=request.document_id,
            stream=False,
            enable_citations=True
        )
        # Parse PageIndex response to our QueryResponse model
        answer = response["choices"][0]["message"]["content"]
        return QueryResponse(
            id="query-123",
            answer=answer,
            confidence=0.9,
            role=request.role
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/stream")
async def stream_query(request: QueryRequest):
    """Stream a clinical query response with real-time reasoning trace."""

    async def event_generator():
        try:
            messages = [
                {"role": "system", "content": f"You are an expert orthopaedic AI assistant. Answer the query for a {request.role.value}."},
                {"role": "user", "content": request.query}
            ]
            
            stream_iter = pi_client.chat_completions(
                messages=messages,
                doc_id=request.document_id,
                stream=True,
                stream_metadata=True,
                enable_citations=True
            )
            
            step_counter = 1
            for chunk in stream_iter:
                # If it's a citation or trace object
                if chunk.get("object") == "chat.completion.citations":
                    data = chunk.get("citations", [])
                    if data:
                        # Convert to trace steps for the UI
                        for idx, ref in enumerate(data):
                            trace_detail = ref.get("text", "Found section")
                            event = {
                                "type": "trace",
                                "step": step_counter,
                                "data": json.dumps({
                                    "action": f"Reference: {ref.get('title', 'Document Segment')}", 
                                    "detail": trace_detail[:100] + "..." if len(trace_detail) > 100 else trace_detail
                                })
                            }
                            yield f"data: {json.dumps(event)}\n\n"
                            step_counter += 1
                            await asyncio.sleep(0.1)
                else:
                    # Token chunk
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        event = {"type": "token", "data": content}
                        yield f"data: {json.dumps(event)}\n\n"
                        await asyncio.sleep(0.01)

            yield f"data: [DONE]\n\n"
            
        except Exception as e:
            error_event = {"type": "error", "data": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/query/{query_id}/trace")
async def get_query_trace(query_id: str):
    return {"query_id": query_id, "trace": []}

import sys
import os
import asyncio
import json

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.pageindex_engine import PageIndexEngine
from models.schemas import UserRole

async def test_global_rag():
    print("--- BoneQuest: Full Global RAG Pipeline Test ---")
    
    engine = PageIndexEngine()
    
    # We pass document_id=None to trigger automated librarian discovery
    query = "What is the hemiarthroplasty protocol for femoral neck fractures?"
    print(f"Query: {query}")
    
    try:
        # Capture events from the stream
        events = []
        async for event in engine.generate_response_stream(
            query=query,
            role=UserRole.resident,
            document_id=None # TRIGGER GLOBAL MODE
        ):
            events.append(event)
            if event["type"] == "trace":
                data = json.loads(event["data"])
                print(f"[Trace Step {event['step']}] {data['action']}: {data['detail']}")
            elif event["type"] == "citation":
                citations = json.loads(event["data"])
                print(f"[Citations] Found {len(citations)} sources.")
                for c in citations:
                    print(f"  - Ref: {c['guideline']} | {c['section']}")

        # Verify final payload
        final = next((e["data"] for e in events if e["type"] == "final_payload"), None)
        if final and final["citations"]:
            print("\n✅ SUCCESS: Global pipeline retrieved and cited from automatically discovered document.")
        else:
            print("\n❌ FAILURE: Global pipeline failed to retrieve evidence.")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_global_rag())

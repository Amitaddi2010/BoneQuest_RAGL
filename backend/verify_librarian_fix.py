
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent))

from services.pageindex_engine import PageIndexEngine
from models.schemas import UserRole

async def test_librarian_fallback():
    engine = PageIndexEngine()
    
    query = "rehab protocol for ACL"
    print(f"Testing Librarian Fallback for query: '{query}'")
    
    # We expect this to fallback to doc-1 since the DB is missing relevant ACL trees
    context, citations, meta = await engine._retrieve_hybrid_context(
        query=query,
        document_id=None, # Global Mode
        intent="clinical"
    )
    
    print(f"Strategy: {meta['strategy']}")
    print(f"Source: {meta['source']}")
    print(f"Citations Found: {len(citations)}")
    
    if len(citations) > 0 and meta['strategy'] == "librarian_institutional_fallback":
        print("✅ SUCCESS: Librarian correctly fell back to Institutional protocols.")
    else:
        print("❌ FAILURE: Librarian did not trigger institutional fallback.")

if __name__ == "__main__":
    asyncio.run(test_librarian_fallback())

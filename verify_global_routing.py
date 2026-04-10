import sys
import os
import asyncio
import json
from unittest.mock import MagicMock
from pathlib import Path

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from services.vectorless_retrieval import LibraryRouter

async def test_librarian_routing():
    print("--- BoneQuest: Global Librarian Routing Test ---")
    
    db = SessionLocal()
    
    # Mock Groq Client
    mock_groq = MagicMock()
    mock_response = MagicMock()
    # Simulate the LLM selecting document ID 1
    mock_response.choices[0].message.content = json.dumps({
        "thinking": "The user is asking about orthopaedic surgery techniques found in the main textbook.",
        "selected_ids": [1]
    })
    mock_groq.chat.completions.create.return_value = mock_response
    
    router = LibraryRouter(db, mock_groq)
    
    query = "How to treat a femoral neck fracture?"
    print(f"Query: {query}")
    
    try:
        selected = await router.select_relevant_documents(query)
        print("\n[Librarian Result]")
        for doc in selected:
            print(f"- Selected: {doc['name']} (ID: {doc['id']})")
            print(f"  Summary: {doc['root_summary'][:100]}...")
            
        if any(d['id'] == 1 for d in selected):
            print("\n✅ SUCCESS: Librarian correctly identified the textbook.")
        else:
            print("\n❌ FAILURE: Librarian did not select the expected document.")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_librarian_routing())

import sys
import os
import asyncio
import json
from pathlib import Path

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.vectorless_index import PDFHierarchyExtractor

async def main():
    print("--- BoneQuest Vectorless RAG: Extraction Test ---")
    
    # Path to the sample PDF we found in the uploads directory
    pdf_path = os.path.join('backend', 'data', 'uploads', '26156c24.pdf')
    
    if not os.path.exists(pdf_path):
        print(f"ERROR: Sample PDF not found at {pdf_path}")
        return

    extractor = PDFHierarchyExtractor()
    
    print(f"Processing: {pdf_path}")
    print("Extracting first 20 pages for testing...")
    
    # We'll run the extraction and then just show the hierarchy detected.
    try:
        # Note: To avoid long wait, we'll manually mock the 'pages' loop if we wanted, 
        # but let's see how fast it is.
        result = await extractor.extract_from_pdf(pdf_path)
        
        print("\n[SUCCESS] Extraction complete.")
        print(f"Total Pages processed: {result['total_pages']}")
        
        hierarchy = result['detected_hierarchy']
        print("\nDetected Hierarchy Summary:")
        print(f"- Chapters: {len(hierarchy.get('chapters', []))}")
        print(f"- Sections: {len(hierarchy.get('sections', []))}")
        print(f"- Subsections: {len(hierarchy.get('subsections', []))}")
        
        if hierarchy['chapters']:
            print("\nFirst 5 Chapters:")
            for c in hierarchy['chapters'][:5]:
                print(f"  * {c['title']} (Page {c['page']})")
                if c['sections']:
                    for s in c['sections'][:2]:
                        print(f"    - {s['title']} (Page {s['page']})")
        
    except Exception as e:
        print(f"ERROR during extraction: {e}")

if __name__ == "__main__":
    asyncio.run(main())

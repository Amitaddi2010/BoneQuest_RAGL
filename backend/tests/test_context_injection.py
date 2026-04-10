import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.db_models import Base, Document, DocumentChunk
from services.context_injection import ContextInjectionService


class ContextInjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()
        self.service = ContextInjectionService()

        doc1 = Document(doc_id="d1", internal_id="a1", name="Trauma Handbook", status="indexed", doc_type="guideline")
        doc2 = Document(doc_id="d2", internal_id="a2", name="Rehab Notes", status="indexed", doc_type="general")
        self.db.add_all([doc1, doc2])
        self.db.commit()
        self.db.refresh(doc1)
        self.db.refresh(doc2)

        chunks = [
            DocumentChunk(
                document_id=doc1.id,
                chunk_index=0,
                source_type="pdf",
                section="Fracture Management",
                page_label="p. 10",
                content="Tibial shaft fracture treatment in diabetic patients includes debridement and fixation.",
                token_count=40,
            ),
            DocumentChunk(
                document_id=doc1.id,
                chunk_index=1,
                source_type="pdf",
                section="Complications",
                page_label="p. 22",
                content="Diabetes increases infection risk after fracture surgery and requires tighter follow-up.",
                token_count=36,
            ),
            DocumentChunk(
                document_id=doc2.id,
                chunk_index=0,
                source_type="pdf",
                section="Rehabilitation",
                page_label="p. 4",
                content="Post-operative rehab timeline and functional milestones for lower limb injuries.",
                token_count=28,
            ),
        ]
        self.db.add_all(chunks)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_returns_ranked_context(self) -> None:
        pkg = self.service.build_context_package(
            db=self.db,
            query="diabetic tibial shaft fracture management",
            document_id="global",
            token_budget=300,
            max_chunks=4,
        )
        self.assertGreater(len(pkg["citations"]), 0)
        self.assertIn("Fracture Management", pkg["context"])
        self.assertEqual(pkg["retrieval"]["strategy"], "context_injection")

    def test_respects_token_budget(self) -> None:
        pkg = self.service.build_context_package(
            db=self.db,
            query="fracture diabetes",
            document_id="global",
            token_budget=50,
            max_chunks=5,
        )
        self.assertLessEqual(pkg["retrieval"]["tokens_used"], 50)
        self.assertLessEqual(len(pkg["citations"]), 2)


if __name__ == "__main__":
    unittest.main()

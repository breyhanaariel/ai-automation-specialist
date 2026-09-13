import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.schemas import RetrievedSource, SupportTicketIn, TicketClassification

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class KnowledgeDocument:
    source_id: str
    title: str
    content: str


class KnowledgeRetriever:
    def __init__(self, knowledge_path: Path | None = None) -> None:
        self.knowledge_path = knowledge_path or self._default_knowledge_path()
        self.documents = self._load_documents()

    @staticmethod
    def _default_knowledge_path() -> Path:
        return Path(__file__).resolve().parents[3] / "data" / "knowledge_base.json"

    def _load_documents(self) -> list[KnowledgeDocument]:
        payload = json.loads(self.knowledge_path.read_text(encoding="utf-8"))
        return [KnowledgeDocument(**item) for item in payload]

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(TOKEN_PATTERN.findall(text.lower()))

    def retrieve(
        self,
        ticket: SupportTicketIn,
        classification: TicketClassification,
        *,
        limit: int = 3,
    ) -> list[RetrievedSource]:
        query_tokens = self._tokens(
            " ".join(
                [
                    ticket.customer_message,
                    classification.category.value,
                    classification.intent_summary,
                ]
            )
        )

        scored: list[tuple[float, KnowledgeDocument]] = []
        for document in self.documents:
            document_tokens = self._tokens(f"{document.title} {document.content}")
            overlap = len(query_tokens & document_tokens)
            score = overlap / max(len(query_tokens), 1)
            if score > 0:
                scored.append((score, document))

        scored.sort(key=lambda item: (-item[0], item[1].source_id))
        return [
            RetrievedSource(
                source_id=document.source_id,
                title=document.title,
                excerpt=document.content,
                relevance_score=round(score, 4),
            )
            for score, document in scored[:limit]
        ]

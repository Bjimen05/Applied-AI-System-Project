"""Offline RAG layer for PawPal+: keyword/Jaccard retrieval over a small,
curated pet-care knowledge base. No external API — retrieval is entirely
local so this feature works without an LLM or network access.

Multi-source by default: the hand-written general-care KB below is merged
with a second, independently editable source (data/breed_facts.json) at
construction time, and callers can layer in a third source at runtime via
add_documents() — e.g. an owner's own notes about a specific pet.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re

_BREED_FACTS_PATH = Path(__file__).parent / "data" / "breed_facts.json"

_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "with",
    "is", "are", "this", "that", "be", "as", "at", "by", "it", "its",
}


_SUFFIXES = ("ing", "edly", "ed", "es", "s")


def _stem(word: str) -> str:
    """Light suffix-stripping so 'walks'/'walking' overlaps with 'walk',
    'minutes' with 'minute', etc. Not linguistically rigorous — just enough
    to keep exact-token Jaccard matching from missing obvious plurals."""
    for suffix in _SUFFIXES:
        if len(word) - len(suffix) >= 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return {_stem(w) for w in words if w not in _STOPWORDS}


@dataclass
class Document:
    doc_id: str
    species: str    # "dog", "cat", "rabbit", or "any"
    category: str   # "exercise", "feeding", "grooming", "litter", "enrichment", "medication", "vet", "general"
    text: str
    keywords: set[str] = field(default_factory=set)

    def tokens(self) -> set[str]:
        return _tokenize(self.text) | {_stem(k) for k in self.keywords}


KNOWLEDGE_BASE: list[Document] = [
    Document("dog-exercise-1", "dog", "exercise",
        "Dogs generally need 30 to 60 minutes of physical exercise daily; "
        "skipping walks can lead to destructive behavior and weight gain.",
        keywords={"walk", "walking", "exercise"}),
    Document("dog-feeding-1", "dog", "feeding",
        "Adult dogs are typically fed once or twice daily; sudden diet changes "
        "can cause stomach upset, so transition foods gradually over 5 to 7 days.",
        keywords={"feeding", "feed", "food", "diet", "kibble"}),
    Document("dog-grooming-1", "dog", "grooming",
        "Short-haired dogs should be brushed weekly and long-haired breeds several "
        "times a week to prevent matting and reduce shedding.",
        keywords={"grooming", "groom", "brush", "coat", "fur"}),
    Document("dog-medication-1", "dog", "medication",
        "Never give human medication like ibuprofen or acetaminophen to dogs; "
        "always follow the dose and schedule prescribed by a veterinarian.",
        keywords={"medication", "meds", "med", "dose", "dosage", "pill"}),
    Document("dog-vet-1", "dog", "vet",
        "Annual wellness exams help catch issues early; puppies and senior dogs "
        "may need checkups twice a year.",
        keywords={"vet", "checkup", "exam", "wellness"}),
    Document("cat-exercise-1", "cat", "exercise",
        "Indoor cats benefit from 15 to 20 minutes of interactive play daily to "
        "prevent obesity and boredom-related destructive behavior.",
        keywords={"play", "exercise", "enrichment"}),
    Document("cat-feeding-1", "cat", "feeding",
        "Cats are obligate carnivores and need a protein-rich diet; free-feeding "
        "dry food can lead to overeating in less active cats.",
        keywords={"feeding", "feed", "food", "diet"}),
    Document("cat-litter-1", "cat", "litter",
        "Litter boxes should be scooped at least once daily and fully changed "
        "weekly; cats may avoid a dirty box and eliminate elsewhere.",
        keywords={"litter", "box", "scoop"}),
    Document("cat-grooming-1", "cat", "grooming",
        "Long-haired cats need daily brushing to prevent mats and hairballs; "
        "short-haired cats can be brushed weekly.",
        keywords={"grooming", "groom", "brush", "coat", "ear", "ears"}),
    Document("cat-medication-1", "cat", "medication",
        "Administering pills or drops to cats is easier right after a meal; "
        "never crush medication without checking with a vet, since some pills "
        "are time-released.",
        keywords={"medication", "meds", "med", "pill", "drop", "drops"}),
    Document("cat-vet-1", "cat", "vet",
        "Cats hide illness well, so subtle changes in appetite or litter box "
        "habits often warrant a vet visit.",
        keywords={"vet", "checkup", "illness"}),
    Document("rabbit-feeding-1", "rabbit", "feeding",
        "Rabbits need unlimited access to hay, which should make up the majority "
        "of their diet, along with fresh greens and a small portion of pellets.",
        keywords={"feeding", "feed", "food", "diet", "hay"}),
    Document("rabbit-enrichment-1", "rabbit", "enrichment",
        "Rabbits are prey animals that need daily free-roam or exercise time and "
        "enrichment like tunnels and chew toys to stay mentally healthy.",
        keywords={"enrichment", "play", "exercise", "roam"}),
    Document("rabbit-grooming-1", "rabbit", "grooming",
        "Rabbits groom themselves but still need regular nail trims and brushing "
        "during shedding season to prevent ingested-fur blockages.",
        keywords={"grooming", "groom", "brush", "nail", "nails"}),
    Document("rabbit-vet-1", "rabbit", "vet",
        "Rabbits can hide pain well; a rabbit that stops eating for more than "
        "12 hours needs urgent veterinary attention.",
        keywords={"vet", "emergency", "pain"}),
    Document("general-medication-1", "any", "medication",
        "When giving any pet prescribed medication, follow the exact dosage and "
        "schedule from the vet, and watch for signs of an adverse reaction like "
        "vomiting or lethargy.",
        keywords={"medication", "meds", "med", "dose", "dosage", "prescribed", "pill"}),
    Document("general-emergency-1", "any", "vet",
        "Signs of a pet emergency include difficulty breathing, prolonged "
        "vomiting, seizures, or suspected poisoning — seek emergency veterinary "
        "care immediately rather than waiting for a routine appointment.",
        keywords={"emergency", "vet", "urgent"}),
    Document("general-enrichment-1", "any", "enrichment",
        "Mental enrichment such as puzzle toys, training, and novel scents is as "
        "important as physical exercise for reducing stress-related behavior in "
        "most pets.",
        keywords={"enrichment", "play", "toys", "training"}),
]

RISK_CATEGORIES = {"medication", "vet"}


def load_documents_from_json(path: str | Path) -> list[Document]:
    """Load a list of Documents from an external JSON file — a second,
    independently editable knowledge source. Expected shape per entry:
    {"doc_id": str, "species": str, "category": str, "text": str,
     "keywords": [str, ...]} ("keywords" is optional).
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Document(
            doc_id=entry["doc_id"],
            species=entry["species"],
            category=entry["category"],
            text=entry["text"],
            keywords=set(entry.get("keywords", [])),
        )
        for entry in raw
    ]


def _default_documents() -> list[Document]:
    """The built-in KB merged with the breed-facts source, if present."""
    docs = list(KNOWLEDGE_BASE)
    if _BREED_FACTS_PATH.exists():
        docs.extend(load_documents_from_json(_BREED_FACTS_PATH))
    return docs


@dataclass
class RetrievedPassage:
    document: Document
    score: float


class Retriever:
    """Jaccard-overlap retrieval over the pet-care knowledge base.

    With no documents given, merges two sources: the hand-written KB in
    this module and data/breed_facts.json. add_documents() layers in a
    third source at runtime (e.g. an owner's custom note about one pet).
    """

    def __init__(self, documents: list[Document] | None = None) -> None:
        self.documents = documents if documents is not None else _default_documents()

    def add_documents(self, documents: list[Document]) -> None:
        """Add custom documents at runtime without replacing existing sources."""
        self.documents = self.documents + list(documents)

    def retrieve(
        self, query: str, *, species: str | None = None, top_k: int = 3,
    ) -> list[RetrievedPassage]:
        """Return the top_k documents most relevant to `query`.

        species: if given, only documents tagged for that species or "any"
                 are considered.
        Score is Jaccard similarity between the query's tokens and each
        document's tokens — cheap, dependency-free, fully offline.
        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        candidates = self.documents
        if species:
            species = species.lower()
            candidates = [d for d in candidates if d.species in (species, "any")]

        scored: list[RetrievedPassage] = []
        for doc in candidates:
            doc_tokens = doc.tokens()
            overlap = query_tokens & doc_tokens
            if not overlap:
                continue
            union = query_tokens | doc_tokens
            score = len(overlap) / len(union)
            scored.append(RetrievedPassage(doc, score))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def retrieve_for_task(self, title: str, description: str, species: str, top_k: int = 1) -> list[RetrievedPassage]:
        return self.retrieve(f"{title} {description}", species=species, top_k=top_k)

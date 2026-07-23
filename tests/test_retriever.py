import json

from retriever import Document, Retriever, load_documents_from_json


def test_retrieve_returns_relevant_passage_for_species():
    retriever = Retriever()
    hits = retriever.retrieve("daily hay diet greens", species="rabbit", top_k=1)

    assert hits
    assert hits[0].document.species in ("rabbit", "any")
    assert "hay" in hits[0].document.text.lower()


def test_species_filter_excludes_other_species_docs():
    retriever = Retriever()
    hits = retriever.retrieve("litter box scooping", species="dog", top_k=5)

    assert all(h.document.species in ("dog", "any") for h in hits)


def test_empty_query_returns_no_hits():
    retriever = Retriever()
    assert retriever.retrieve("", species="cat") == []
    assert retriever.retrieve("   ", species="cat") == []


def test_top_k_limits_results():
    retriever = Retriever()
    hits = retriever.retrieve("vet medication dose exercise feeding grooming", top_k=2)

    assert len(hits) <= 2


def test_results_sorted_by_score_descending():
    retriever = Retriever()
    hits = retriever.retrieve("medication dosage vet prescribed schedule", top_k=5)

    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_for_task_combines_title_and_description():
    docs = [Document("custom-1", "any", "medication", "prescribed drops schedule vet visit")]
    retriever = Retriever(docs)

    hits = retriever.retrieve_for_task("Ear Drops", "prescribed schedule after vet visit", "dog", top_k=1)

    assert hits
    assert hits[0].document.doc_id == "custom-1"


def test_no_overlap_returns_no_hits():
    docs = [Document("custom-1", "any", "feeding", "hay greens pellets rabbit diet")]
    retriever = Retriever(docs)

    hits = retriever.retrieve("completely unrelated query zzz", top_k=3)

    assert hits == []


# ---------------------------------------------------------------------------
# Stretch: multi-source retrieval (default KB + breed_facts.json) and
# runtime-added custom documents (e.g. an owner's own notes).
# ---------------------------------------------------------------------------

def test_default_retriever_merges_breed_facts_source():
    retriever = Retriever()
    hits = retriever.retrieve("Golden Retriever high energy exercise needs", species="dog", top_k=1)

    assert hits
    assert hits[0].document.doc_id == "breed-golden-retriever-1"


def test_breed_specific_doc_outranks_generic_doc_for_breed_query():
    retriever = Retriever()
    hits = retriever.retrieve("Golden Retriever exercise needs more than a short walk", species="dog", top_k=2)

    assert len(hits) >= 2
    assert hits[0].document.doc_id == "breed-golden-retriever-1"
    assert hits[0].score > hits[1].score


def test_load_documents_from_json_parses_expected_shape(tmp_path):
    path = tmp_path / "custom_kb.json"
    path.write_text(json.dumps([
        {"doc_id": "x-1", "species": "dog", "category": "general",
         "text": "Test passage about walks", "keywords": ["walk"]},
    ]), encoding="utf-8")

    docs = load_documents_from_json(path)

    assert len(docs) == 1
    assert docs[0].doc_id == "x-1"
    assert docs[0].keywords == {"walk"}


def test_add_documents_makes_custom_note_retrievable():
    retriever = Retriever([])
    assert retriever.retrieve("Buddy allergic to chicken", top_k=1) == []

    retriever.add_documents([
        Document("custom-buddy-1", "dog", "general",
                 "Buddy is allergic to chicken, use turkey-based kibble instead"),
    ])

    hits = retriever.retrieve("Buddy allergic to chicken kibble", top_k=1)
    assert hits
    assert hits[0].document.doc_id == "custom-buddy-1"


def test_add_documents_does_not_remove_existing_sources():
    retriever = Retriever()
    before = len(retriever.documents)

    retriever.add_documents([Document("custom-1", "any", "general", "a brand new note")])

    assert len(retriever.documents) == before + 1

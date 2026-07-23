from retriever import Document, Retriever


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

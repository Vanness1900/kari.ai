from rag.retriever import retrieve_content


def build_context(query: str, k: int = 3) -> str:
    """Build formatted RAG context from retrieved semantic chunks."""

    # Retrieve semantically relevant chunks
    results = retrieve_content(
        query=query,
        k=k
    )

    # Store formatted context sections
    context_sections = []

    # Loop through retrieved results
    for document, relevance_score in results:

        # Extract metadata
        source = document.metadata.get("source")
        page = document.metadata.get("page")
        document_type = document.metadata.get("document_type")

        # Extract chunk content
        content = document.page_content

        # Improve multiline readability
        formatted_content = content.replace(
            "\n",
            "\n    "
        )

        # Build formatted retrieval section
        context_sections.append(
            f"""
Document Type: {document_type}
Source: {source}
Page: {page}

Content:
    {formatted_content}
"""
        )

    # Combine all retrieved sections into one context string
    return "\n\n".join(context_sections)
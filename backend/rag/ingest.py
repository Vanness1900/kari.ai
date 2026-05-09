from rag.parsers.parse_pdf import parse_pdf
from rag.chunker import chunk_text
from rag.embeddings import get_embeddings
from rag.chroma import create_vectorstore


def ingest_pdf(file_path: str, document_type: str):
    result = parse_pdf(file_path)
    course_name = result["course_name"]
    pages = result["pages"]
    embeddings = get_embeddings()
    all_chunks = []
    metadata_list = []
    chunk_id = 0

    for page_data in pages:
        page_number = page_data["page"]
        page_text = page_data["text"]
        chunks = chunk_text(page_text)

        for chunk in chunks:
            all_chunks.append(chunk)
            metadata_list.append({
                "course": course_name,
                "page": page_number,
                "chunk_id": chunk_id,
                "source": file_path,
                "document_type": document_type
            })

            chunk_id += 1

    create_vectorstore(
        all_chunks,
        embeddings,
        metadata_list
    )

    return {
        "status": "success",
        "course": course_name,
        "chunks": len(all_chunks),
    }
from langchain_community.vectorstores import Chroma

from rag.embeddings import get_embeddings
from settings import get_settings

settings = get_settings()

def retrieve_content(query: str, k: int = 3):
    embeddings = get_embeddings()

    vectorstore = Chroma(
        persist_directory=str(settings.chroma_db_path),
        embedding_function=embeddings,
    )

    results = vectorstore.similarity_search_with_score(
        query, 
        k = k
    )
    return results


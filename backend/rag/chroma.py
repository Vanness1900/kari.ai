from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma

from settings import get_settings

settings = get_settings()

CHROMA_CLIENT_SETTINGS = ChromaSettings(anonymized_telemetry=False)


def create_vectorstore(chunks, embeddings, metadata_list):
    vectorstore = Chroma.from_texts(
        texts=chunks,
        metadatas=metadata_list,
        embedding=embeddings,
        persist_directory=str(settings.chroma_db_path),
        client_settings=CHROMA_CLIENT_SETTINGS,
    )

    return vectorstore

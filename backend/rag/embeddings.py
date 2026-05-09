from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv(".env.local")

def get_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small"
    )
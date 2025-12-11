import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from app.core.config import settings

def get_chroma_client():
    """
    Connect to remote ChromaDB instance
    """
    return chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
        settings=ChromaSettings(allow_reset=True)
    )

def get_embedding_function():
    """
    Use OpenAI embedding function
    """
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.OPENAI_API_KEY,
        api_base=settings.OPENAI_BASE_URL,
        model_name=settings.EMBEDDING_MODEL
    )

def get_collection():
    client = get_chroma_client()
    ef = get_embedding_function()
    return client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=ef
    )

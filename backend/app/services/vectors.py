# Placeholder vector helpers for Qdrant
from qdrant_client import QdrantClient

def get_client(host: str, port: int):
    return QdrantClient(host=host, port=port)

def ensure_collection(client: QdrantClient, name: str):
    from qdrant_client.http.models import Distance, VectorParams
    try:
        client.get_collection(name)
    except Exception:
        client.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

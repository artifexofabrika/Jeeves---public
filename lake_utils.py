import chromadb
from chromadb.utils import embedding_functions

def query_lake(query, n=3):
    """Return top n document chunks from the knowledge lake."""
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)
    results = collection.query(query_texts=[query], n_results=n)
    return results.get("documents", [[]])[0]

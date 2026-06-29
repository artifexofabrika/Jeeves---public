import chromadb
from chromadb.utils import embedding_functions

def query_lake(query, n=3):
    """Return (list_of_documents, best_distance). best_distance is 1.0 if lake empty."""
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path="/mnt/lake/index")
    collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)
    results = collection.query(query_texts=[query], n_results=n)
    docs = results.get('documents', [[]])[0]
    distances = results.get('distances', [[1.0]])[0]
    best = distances[0] if distances else 1.0
    return docs, best

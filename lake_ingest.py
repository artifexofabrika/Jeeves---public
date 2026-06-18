import os, sys, time, re
import chromadb
from chromadb.utils import embedding_functions

RAW_DIR = "/mnt/lake/raw"
PROCESSED_DIR = "/mnt/lake/processed"
INDEX_DIR = "/mnt/lake/index"
CHUNK_WORDS = 500          # target words per chunk
MIN_FILE_SIZE_BYTES = 50 * 1024  # 50 KB – anything smaller is indexed whole

# Embedding engine
ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=INDEX_DIR)
collection = client.get_or_create_collection(name="memory_lake", embedding_function=ef)

def chunk_text(text, max_words=CHUNK_WORDS):
    """
    Split text into chunks of roughly max_words.
    Tries to break at paragraph boundaries first, then at sentences, then hard break.
    Returns a list of chunks.
    """
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    current_words = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_words = len(para.split())
        # If adding this paragraph exceeds the limit, store current chunk and start new
        if current_words + para_words > max_words and current_words > 0:
            chunks.append(current_chunk.strip())
            current_chunk = para
            current_words = para_words
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
            current_words += para_words

        # If current chunk itself is too big, break it further by sentences
        while current_words > max_words:
            sentences = re.split(r'(?<=[.!?]) +', current_chunk)
            new_chunk = ""
            new_words = 0
            for sent in sentences:
                sent_words = len(sent.split())
                if new_words + sent_words > max_words and new_words > 0:
                    chunks.append(new_chunk.strip())
                    new_chunk = sent
                    new_words = sent_words
                else:
                    new_chunk = (new_chunk + " " + sent).strip()
                    new_words += sent_words
            current_chunk = new_chunk
            current_words = new_words
            # Safety break if a single sentence is still over limit
            if len(sentences) == 1 and current_words > max_words:
                # Hard break by words
                words = current_chunk.split()
                while len(words) > max_words:
                    chunks.append(" ".join(words[:max_words]))
                    words = words[max_words:]
                current_chunk = " ".join(words)
                current_words = len(words)
                break

    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks

def process_file(filepath):
    filename = os.path.basename(filepath)
    # Only process .txt files
    if not filename.endswith('.txt'):
        return

    # Check file size
    size = os.path.getsize(filepath)
    if size > MIN_FILE_SIZE_BYTES:
        # Large file – read, chunk, index each chunk separately
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content.strip():
                return
            chunks = chunk_text(content)
            base_name = os.path.splitext(filename)[0]
            for i, chunk in enumerate(chunks):
                doc_id = f"{base_name}_chunk_{i:04d}"
                collection.add(
                    documents=[chunk],
                    ids=[doc_id]
                )
            print(f"Indexed {len(chunks)} chunks from {filename}")
            # Remove original large file from raw (it's been indexed)
            os.remove(filepath)
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    else:
        # Small file – index whole
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content.strip():
                return
            # Use filename (without extension) as ID
            doc_id = os.path.splitext(filename)[0]
            collection.add(
                documents=[content],
                ids=[doc_id]
            )
            # Move file to processed
            dest = os.path.join(PROCESSED_DIR, filename)
            os.rename(filepath, dest)
            print(f"Indexed: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    print("Lake ingestion running (with auto‑chunking). Drop .txt files into /mnt/lake/raw.")
if __name__ == "__main__":
    while True:
    if os.path.isdir(RAW_DIR):
        for filename in os.listdir(RAW_DIR):
            filepath = os.path.join(RAW_DIR, filename)
            if os.path.isfile(filepath):
                process_file(filepath)
    time.sleep(5)

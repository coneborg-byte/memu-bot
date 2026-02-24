import sys
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Import local DB manager
sys.path.append(os.path.dirname(__file__))
import db_manager

INDEX_PATH = "/root/.openclaw/library/knowledge/vector.index"
MODEL_NAME = 'all-MiniLM-L6-v2'


def search(query, top_k=3):
    if not os.path.exists(INDEX_PATH):
        return "Memory is empty. Please ingest some knowledge first."

    model = SentenceTransformer(MODEL_NAME)
    query_vector = model.encode([query])

    index = faiss.read_index(INDEX_PATH)
    _, indices = index.search(np.array(query_vector).astype('float32'), top_k)

    results = []
    for idx in indices[0]:
        # FAISS indices are 0-based
        # SQLite autoincrement IDs are 1-based (usually)
        # We assume they were added in the same order
        chunk_id = int(idx) + 1
        chunk_data = db_manager.get_chunk(chunk_id)

        if chunk_data:
            chunk_text, entry_id = chunk_data
            entry = db_manager.get_entry(entry_id)
            if entry:
                results.append({
                    "id": entry[0],
                    "type": entry[1],
                    "url": entry[2],
                    "title": entry[3],
                    "chunk": chunk_text,
                    "full_text_snippet": entry[4][:200] + "..."
                })

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search.py \"your query\"")
        sys.exit(1)

    search_query = sys.argv[1]
    print(f"🔍 Searching for: {search_query}")
    search_results = search(search_query)

    if isinstance(search_results, str):
        print(search_results)
    else:
        for r in search_results:
            print(f"\n--- Result [Entry ID: {r['id']}] ---")
            print(f"Title: {r['title']}")
            print(f"Source: {r['type']} ({r['url']})")
            print(f"Chunk: {r['chunk']}")
            print("-" * 20)

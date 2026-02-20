import sys
import os
import sqlite3
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Import local DB manager
sys.path.append(os.path.dirname(__file__))
import db_manager

DB_PATH = "library/knowledge/kb.db"
INDEX_PATH = "library/knowledge/vector.index"
MODEL_NAME = 'all-MiniLM-L6-v2'

def search(query, top_k=3):
    if not os.path.exists(INDEX_PATH):
        return "Memory is empty. Please ingest some knowledge first."
    
    model = SentenceTransformer(MODEL_NAME)
    query_vector = model.encode([query])
    
    index = faiss.read_index(INDEX_PATH)
    distances, indices = index.search(np.array(query_vector).astype('float32'), top_k)
    
    # Load mapping
    with open(INDEX_PATH + ".map", "r") as f:
        id_map = [line.strip() for line in f.readlines()]
    
    results = []
    for idx in indices[0]:
        if idx < len(id_map):
            entry_id = id_map[idx]
            entry = db_manager.get_entry(entry_id)
            if entry:
                results.append({
                    "id": entry[0],
                    "type": entry[1],
                    "url": entry[2],
                    "title": entry[3],
                    "text": entry[4][:500] + "..." # Snippet
                })
    
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search.py \"your query\"")
        sys.exit(1)
        
    query = sys.argv[1]
    print(f"🔍 Searching for: {query}")
    results = search(query)
    
    if isinstance(results, str):
        print(results)
    else:
        for r in results:
            print(f"\n--- Result [ID: {r['id']}] ---")
            print(f"Title: {r['title']}")
            print(f"Source: {r['type']} ({r['url']})")
            print(f"Snippet: {r['text']}")

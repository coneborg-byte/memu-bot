import argparse
import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Import local DB manager
sys.path.append(os.path.dirname(__file__))
import db_manager

INDEX_PATH = "library/knowledge/vector.index"
MODEL_NAME = 'all-MiniLM-L6-v2'

def get_youtube_id(url):
    if "youtu.be" in url:
        return url.split("/")[-1]
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return None

def fetch_youtube_transcript(url):
    video_id = get_youtube_id(url)
    if not video_id:
        return "Invalid YouTube URL"
    try:
        # Correct static call for the library
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript_list])
    except Exception as e:
        return f"Could not fetch transcript: {e}"

def fetch_web_article(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text()
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return "\n".join(chunk for chunk in chunks if chunk)
    except Exception as e:
        return f"Error fetching article: {e}"

def fetch_pdf_text(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def update_vector_index(entry_id, text):
    model = SentenceTransformer(MODEL_NAME)
    embedding = model.encode([text])
    
    dimension = embedding.shape[1]
    if os.path.exists(INDEX_PATH):
        index = faiss.read_index(INDEX_PATH)
    else:
        index = faiss.IndexFlatL2(dimension)
    
    # We store the entry_id as an ID in the index if using IndexIDMap, 
    # but for simplicity we'll just append and handle mapping via row order or a simple ID map
    # Simple Flat index doesn't store IDs by default
    index.add(np.array(embedding).astype('float32'))
    faiss.write_index(index, INDEX_PATH)
    
    # Store the mapping in a simple text file for now (id -> vector_idx)
    with open(INDEX_PATH + ".map", "a") as f:
        f.write(f"{entry_id}\n")

def main():
    parser = argparse.ArgumentParser(description="Morpheus Knowledge Ingestion")
    parser.add_argument("--url", help="URL to ingest (YouTube or Web)")
    parser.add_argument("--file", help="File to ingest (PDF)")
    parser.add_argument("--type", help="Source type (youtube, web, pdf, x)")
    parser.add_argument("--title", help="Override title")
    
    args = parser.parse_args()
    
    db_manager.init_db()
    
    raw_text = ""
    source_type = args.type or "unknown"
    source_url = args.url or args.file
    title = args.title or source_url
    
    if args.url:
        if "youtube.com" in args.url or "youtu.be" in args.url:
            raw_text = fetch_youtube_transcript(args.url)
            source_type = "youtube"
        else:
            raw_text = fetch_web_article(args.url)
            source_type = "web"
    elif args.file:
        if args.file.endswith(".pdf"):
            raw_text = fetch_pdf_text(args.file)
            source_type = "pdf"
        elif args.file.endswith(".txt"):
            try:
                with open(args.file, "r") as f:
                    raw_text = f.read()
                source_type = args.type or "text"
            except Exception as e:
                print(f"Error reading text file: {e}")
            
    if not raw_text or len(raw_text) < 50:
        print("❌ Failed to extract meaningful text.")
        return

    # 1. Store in SQLite
    entry_id = db_manager.add_entry(source_type, source_url, title, raw_text)
    
    # 2. Update Vector Index
    print(f"🧠 Embedding entry {entry_id}...")
    update_vector_index(entry_id, raw_text[:5000]) # Limit to first 5k chars for embedding for now
    
    print(f"✅ Successfully ingested: {title}")
    print(f"📊 Source: {source_type} | ID: {entry_id}")

if __name__ == "__main__":
    main()

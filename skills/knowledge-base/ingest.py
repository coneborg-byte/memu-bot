import argparse
import os
import sys
import numpy as np
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss

# Import local DB manager
sys.path.append(os.path.dirname(__file__))
import db_manager

INDEX_PATH = "/root/.openclaw/library/knowledge/vector.index"
MODEL_NAME = 'all-MiniLM-L6-v2'


def get_youtube_id(url):
    """Extract video ID from YouTube URL."""
    if "youtu.be" in url:
        return url.split("/")[-1]
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return None


def fetch_youtube_transcript(url):
    """Fetch transcript for a YouTube video."""
    video_id = get_youtube_id(url)
    if not video_id:
        return "Invalid YouTube URL"
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.fetch(video_id)
        return " ".join([t.text for t in transcript_list])
    except Exception as e:
        return f"Could not fetch transcript for {video_id}: {e}"


def fetch_web_article(url):
    """Scrape web article text safely."""
    try:
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
        headers = {'User-Agent': ua}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in
                  line.split("  "))
        return "\n".join(chunk for chunk in chunks if chunk)
    except Exception as e:
        return f"Error fetching article: {e}"


def fetch_pdf_text(file_path):
    """Extract text from PDF."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"


def chunk_text(text, chunk_size=1000, overlap=100):
    """Split text into manageable chunks for embeddings."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks


def update_vector_index(entry_id, raw_text):
    """Embed chunks and update FAISS index."""
    model = SentenceTransformer(MODEL_NAME)
    chunks = chunk_text(raw_text)

    if not chunks:
        return

    embeddings = model.encode(chunks)
    dimension = embeddings.shape[1]

    if os.path.exists(INDEX_PATH):
        index = faiss.read_index(INDEX_PATH)
    else:
        index = faiss.IndexFlatL2(dimension)

    # 1. Store chunks in DB first
    for chunk in chunks:
        db_manager.add_chunk(entry_id, chunk)

    # 2. Add to FAISS index
    index.add(np.array(embeddings).astype('float32'))
    faiss.write_index(index, INDEX_PATH)


def main():
    """Knowledge ingestion CLI."""
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

    entry_id = db_manager.add_entry(source_type, source_url, title, raw_text)

    print(f"🧠 Chunking and Embedding entry {entry_id}...")
    update_vector_index(entry_id, raw_text)

    print(f"✅ Successfully ingested: {title}")
    print(f"📊 Source: {source_type} | ID: {entry_id}")


if __name__ == "__main__":
    main()

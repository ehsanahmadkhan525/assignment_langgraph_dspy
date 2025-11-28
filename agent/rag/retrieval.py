import os
import glob
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class Retriever:
    def __init__(self, docs_dir: str):
        self.docs_dir = docs_dir
        self.chunks = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None
        self._load_and_chunk_docs()

    def _load_and_chunk_docs(self):
        """Loads markdown files and chunks them by headers or paragraphs."""
        md_files = glob.glob(os.path.join(self.docs_dir, "*.md"))
        
        for file_path in md_files:
            filename = os.path.basename(file_path).replace(".md", "")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple chunking by double newline (paragraphs)
            # A more robust approach would be to parse markdown headers
            raw_chunks = content.split('\n\n')
            
            for i, chunk in enumerate(raw_chunks):
                if chunk.strip():
                    self.chunks.append({
                        "id": f"{filename}::chunk{i}",
                        "content": chunk.strip(),
                        "source": filename
                    })
        
        if self.chunks:
            corpus = [chunk["content"] for chunk in self.chunks]
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """Retrieves top_k relevant chunks for the query."""
        if not self.chunks:
            return []
            
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top_k indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0: # Only return relevant results
                result = self.chunks[idx].copy()
                result["score"] = float(similarities[idx])
                results.append(result)
                
        return results

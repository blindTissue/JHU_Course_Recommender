"""
Embedding-based retrieval for course recommendations using OpenAI text-embedding-3-small.
"""
import json
import os
import numpy as np
from typing import List, Dict, Optional
from openai import OpenAI
import pickle


class EmbeddingRetriever:
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        """
        Initialize embedding-based retriever.

        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model: OpenAI embedding model to use
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.courses = []
        self.embeddings = None
        self.embedding_dim = 1536  # text-embedding-3-small dimension

    def _get_course_text(self, course: Dict) -> str:
        """
        Extract text to embed from course dictionary.

        Args:
            course: Course dictionary

        Returns:
            Text representation for embedding
        """
        parts = []

        # Title
        title = course.get('Title', '')
        parts.append(f"Title: {title}")

        # Course number and department
        offering = course.get('OfferingName', '')
        dept = course.get('Department', '')
        parts.append(f"Course: {offering} - {dept}")

        # Description (main content)
        description = course.get('Description', '')
        if description:
            parts.append(f"Description: {description}")

        # Areas
        areas = course.get('Areas', '')
        if areas and areas != 'None':
            parts.append(f"Areas: {areas}")

        # Level
        level = course.get('Level', '')
        if level:
            parts.append(f"Level: {level}")

        # Instructors
        instructors = course.get('InstructorsFullName', '')
        if instructors:
            parts.append(f"Instructors: {instructors}")

        # Prerequisites
        prereqs = course.get('Prerequisites', [])
        if isinstance(prereqs, list) and prereqs:
            prereq_texts = []
            for prereq in prereqs:
                if isinstance(prereq, dict):
                    prereq_desc = prereq.get('Description', '')
                    if prereq_desc:
                        prereq_texts.append(prereq_desc)
            if prereq_texts:
                parts.append(f"Prerequisites: {' '.join(prereq_texts)}")

        return '\n'.join(parts)

    def build_index(self, courses: List[Dict], cache_file: Optional[str] = None):
        """
        Build embedding index from course data.

        Args:
            courses: List of course dictionaries
            cache_file: Optional file to cache embeddings (saves API costs)
        """
        self.courses = courses

        # Try to load from cache
        if cache_file and os.path.exists(cache_file):
            print(f"Loading embeddings from cache: {cache_file}")
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
                self.embeddings = cache_data['embeddings']
                print(f"Loaded {len(self.embeddings)} cached embeddings")
                return

        # Generate embeddings
        print(f"Generating embeddings for {len(courses)} courses...")
        texts = [self._get_course_text(course) for course in courses]

        # Batch process for efficiency (OpenAI allows up to 2048 texts per request)
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"  Processing batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")

            response = self.client.embeddings.create(
                model=self.model,
                input=batch
            )

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        self.embeddings = np.array(all_embeddings)
        print(f"Generated {len(self.embeddings)} embeddings")

        # Cache embeddings
        if cache_file:
            print(f"Caching embeddings to: {cache_file}")
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'embeddings': self.embeddings,
                    'model': self.model
                }, f)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a query.

        Args:
            query: Query text

        Returns:
            Query embedding vector
        """
        response = self.client.embeddings.create(
            model=self.model,
            input=[query]
        )
        return np.array(response.data[0].embedding)

    def cosine_similarity(self, query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarity between query and documents.

        Args:
            query_embedding: Query embedding vector
            doc_embeddings: Document embedding matrix

        Returns:
            Similarity scores
        """
        # Normalize
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)

        # Cosine similarity
        similarities = np.dot(doc_norms, query_norm)
        return similarities

    def search(self, query: str, top_k: int = 10,
               previous_courses: List[str] = None,
               filters: Dict = None) -> List[Dict]:
        """
        Search for courses using semantic similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            previous_courses: List of previously taken course offerings (for query expansion)
            filters: Optional filters (e.g., {'Department': 'EN Computer Science'})

        Returns:
            List of top-k courses with similarity scores
        """
        # Expand query with previous course context
        full_query = query
        if previous_courses:
            prev_course_texts = []
            for course_offering in previous_courses:
                for course in self.courses:
                    if course.get('OfferingName') == course_offering:
                        prev_course_texts.append(course.get('Title', ''))
                        prev_course_texts.append(course.get('Description', '')[:200])
                        break
            if prev_course_texts:
                full_query = f"{query}\n\nStudent background: {' '.join(prev_course_texts)}"

        # Generate query embedding
        query_embedding = self.embed_query(full_query)

        # Calculate similarities
        similarities = self.cosine_similarity(query_embedding, self.embeddings)

        # Apply filters and get top-k
        results = []
        for idx, score in enumerate(similarities):
            course = self.courses[idx].copy()

            # Apply filters
            if filters:
                skip = False
                for key, value in filters.items():
                    if course.get(key) != value:
                        skip = True
                        break
                if skip:
                    continue

            course['similarity_score'] = float(score)
            results.append(course)

        # Sort by similarity and return top-k
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:top_k]


def main():
    """Example usage."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python embedding_retrieval.py <course_data.json> [query]")
        sys.exit(1)

    # Load course data
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        courses = json.load(f)

    # Initialize retriever
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment")
        sys.exit(1)

    retriever = EmbeddingRetriever(api_key=api_key)

    # Build index (with caching)
    cache_file = 'course_data/embeddings_cache.pkl'
    retriever.build_index(courses, cache_file=cache_file)

    # Search
    query = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else "machine learning artificial intelligence"
    print(f"\nSearching for: {query}")

    results = retriever.search(query, top_k=10)

    print(f"\nTop {len(results)} results:")
    for i, course in enumerate(results, 1):
        print(f"\n{i}. {course.get('Title', 'N/A')} ({course.get('OfferingName', 'N/A')})")
        print(f"   Department: {course.get('Department', 'N/A')}")
        print(f"   Instructor: {course.get('InstructorsFullName', 'N/A')}")
        print(f"   Similarity Score: {course['similarity_score']:.4f}")
        desc = course.get('Description', '')[:150]
        if desc:
            print(f"   Description: {desc}...")


if __name__ == "__main__":
    main()

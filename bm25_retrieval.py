"""
BM25-based keyword retrieval for course recommendations.
"""
import json
import math
from collections import Counter, defaultdict
from typing import List, Dict, Set
import re


class BM25Retriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 retriever.

        Args:
            k1: Term frequency saturation parameter (default 1.5)
            b: Length normalization parameter (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.courses = []
        self.doc_freqs = defaultdict(int)
        self.idf = {}
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.vocab = set()

    def tokenize(self, text: str) -> List[str]:
        """Tokenize and normalize text."""
        if not text:
            return []
        # Convert to lowercase and split on non-alphanumeric characters
        tokens = re.findall(r'\w+', text.lower())
        return tokens

    def build_index(self, courses: List[Dict]):
        """
        Build BM25 index from course data.

        Args:
            courses: List of course dictionaries
        """
        self.courses = courses
        N = len(courses)

        # Build vocabulary and document frequencies
        for course in courses:
            # Combine relevant fields for indexing
            text = self._get_searchable_text(course)
            tokens = self.tokenize(text)
            unique_tokens = set(tokens)

            self.vocab.update(unique_tokens)
            self.doc_lengths.append(len(tokens))

            for token in unique_tokens:
                self.doc_freqs[token] += 1

        # Calculate average document length
        self.avg_doc_length = sum(self.doc_lengths) / N if N > 0 else 0

        # Calculate IDF for each term
        for term in self.vocab:
            df = self.doc_freqs[term]
            # IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)
            self.idf[term] = math.log((N - df + 0.5) / (df + 0.5) + 1)

    def _get_searchable_text(self, course: Dict) -> str:
        """
        Extract searchable text from course dictionary.

        Args:
            course: Course dictionary

        Returns:
            Combined text for indexing
        """
        fields = []

        # Add title (weighted more by repeating)
        title = course.get('Title', '')
        fields.extend([title] * 3)  # Triple weight for title

        # Add description (main searchable content)
        description = course.get('Description', '')
        fields.append(description)

        # Add department and course number
        dept = course.get('Department', '')
        course_num = course.get('OfferingName', '')
        fields.append(f"{dept} {course_num}")

        # Add instructors
        instructors = course.get('InstructorsFullName', '')
        fields.append(instructors)

        # Add areas/topics
        areas = course.get('Areas', '')
        if areas and areas != 'None':
            fields.append(str(areas))

        # Add prerequisites description
        prereqs = course.get('Prerequisites', [])
        if isinstance(prereqs, list):
            for prereq in prereqs:
                if isinstance(prereq, dict):
                    prereq_desc = prereq.get('Description', '')
                    if prereq_desc:
                        fields.append(prereq_desc)

        return ' '.join(str(f) for f in fields if f)

    def score(self, query_tokens: List[str], doc_idx: int) -> float:
        """
        Calculate BM25 score for a document given query tokens.

        Args:
            query_tokens: List of query tokens
            doc_idx: Document index

        Returns:
            BM25 score
        """
        score = 0.0
        doc_text = self._get_searchable_text(self.courses[doc_idx])
        doc_tokens = self.tokenize(doc_text)
        doc_length = self.doc_lengths[doc_idx]
        term_freqs = Counter(doc_tokens)

        for term in query_tokens:
            if term not in self.vocab:
                continue

            tf = term_freqs.get(term, 0)
            idf = self.idf.get(term, 0)

            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))

            score += idf * (numerator / denominator)

        return score

    def search(self, query: str, top_k: int = 10,
               previous_courses: List[str] = None,
               filters: Dict = None) -> List[Dict]:
        """
        Search for courses matching the query.

        Args:
            query: Search query
            top_k: Number of results to return
            previous_courses: List of previously taken course offerings (e.g., ["EN.601.220"])
            filters: Optional filters (e.g., {'Department': 'EN Computer Science', 'Level': 'Upper Level Undergraduate'})

        Returns:
            List of top-k courses with scores
        """
        query_tokens = self.tokenize(query)

        # Optionally boost related courses based on previous courses
        if previous_courses:
            for course_offering in previous_courses:
                # Find courses with similar offerings
                for course in self.courses:
                    if course.get('OfferingName') == course_offering:
                        prev_text = self._get_searchable_text(course)
                        prev_tokens = self.tokenize(prev_text)
                        # Add department and area terms with lower weight
                        query_tokens.extend([t for t in prev_tokens if len(t) > 3][:5])
                        break

        # Score all documents
        scores = []
        for idx in range(len(self.courses)):
            course = self.courses[idx]

            # Apply filters
            if filters:
                skip = False
                for key, value in filters.items():
                    if course.get(key) != value:
                        skip = True
                        break
                if skip:
                    continue

            score = self.score(query_tokens, idx)
            if score > 0:
                scores.append((score, idx))

        # Sort by score and return top-k
        scores.sort(reverse=True)
        results = []

        for score, idx in scores[:top_k]:
            course = self.courses[idx].copy()
            course['bm25_score'] = score
            results.append(course)

        return results


def main():
    """Example usage."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python bm25_retrieval.py <course_data.json> [query]")
        sys.exit(1)

    # Load course data
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        courses = json.load(f)

    # Build index
    print(f"Building BM25 index for {len(courses)} courses...")
    retriever = BM25Retriever()
    retriever.build_index(courses)
    print("Index built!")

    # Search
    query = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else "machine learning artificial intelligence"
    print(f"\nSearching for: {query}")

    results = retriever.search(query, top_k=10)

    print(f"\nTop {len(results)} results:")
    for i, course in enumerate(results, 1):
        print(f"\n{i}. {course.get('Title', 'N/A')} ({course.get('OfferingName', 'N/A')})")
        print(f"   Department: {course.get('Department', 'N/A')}")
        print(f"   Instructor: {course.get('InstructorsFullName', 'N/A')}")
        print(f"   BM25 Score: {course['bm25_score']:.4f}")
        desc = course.get('Description', '')[:150]
        if desc:
            print(f"   Description: {desc}...")


if __name__ == "__main__":
    main()

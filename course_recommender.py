"""
Hybrid course recommender combining BM25 and embedding-based retrieval.
"""
import json
import os
from typing import List, Dict, Optional
from bm25_retrieval import BM25Retriever
from embedding_retrieval import EmbeddingRetriever


class CourseRecommender:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize hybrid course recommender.

        Args:
            api_key: OpenAI API key for embeddings
        """
        self.bm25_retriever = BM25Retriever()
        self.embedding_retriever = EmbeddingRetriever(api_key=api_key)
        self.courses = []

    def build_index(self, courses: List[Dict], embedding_cache_file: Optional[str] = None):
        """
        Build indices for both retrieval methods.

        Args:
            courses: List of course dictionaries
            embedding_cache_file: Optional file to cache embeddings
        """
        self.courses = courses

        print("Building BM25 index...")
        self.bm25_retriever.build_index(courses)

        print("\nBuilding embedding index...")
        self.embedding_retriever.build_index(courses, cache_file=embedding_cache_file)

        print("\nIndices built successfully!")

    def recommend(self,
                  user_interests: str,
                  previous_courses: Optional[List[str]] = None,
                  top_k: int = 10,
                  bm25_weight: float = 0.3,
                  embedding_weight: float = 0.7,
                  filters: Optional[Dict] = None) -> List[Dict]:
        """
        Recommend courses using hybrid retrieval.

        Args:
            user_interests: User's interests/query as natural language
            previous_courses: List of previously taken course offerings (e.g., ["EN.601.220"])
            top_k: Number of recommendations to return
            bm25_weight: Weight for BM25 scores (default 0.3)
            embedding_weight: Weight for embedding scores (default 0.7)
            filters: Optional filters (e.g., {'Level': 'Upper Level Undergraduate'})

        Returns:
            List of recommended courses with combined scores
        """
        # Get results from both methods (retrieve more for better reranking)
        retrieve_k = min(top_k * 3, 50)

        bm25_results = self.bm25_retriever.search(
            user_interests,
            top_k=retrieve_k,
            previous_courses=previous_courses,
            filters=filters
        )

        embedding_results = self.embedding_retriever.search(
            user_interests,
            top_k=retrieve_k,
            previous_courses=previous_courses,
            filters=filters
        )

        # Normalize scores and combine
        combined_scores = {}

        # Normalize BM25 scores (min-max normalization)
        if bm25_results:
            bm25_scores = [r['bm25_score'] for r in bm25_results]
            max_bm25 = max(bm25_scores) if bm25_scores else 1.0
            min_bm25 = min(bm25_scores) if bm25_scores else 0.0
            bm25_range = max_bm25 - min_bm25 if max_bm25 > min_bm25 else 1.0

            for result in bm25_results:
                course_key = (result['OfferingName'], result['SectionName'])
                normalized_score = (result['bm25_score'] - min_bm25) / bm25_range
                combined_scores[course_key] = {
                    'course': result,
                    'bm25_norm': normalized_score,
                    'embedding_norm': 0.0
                }

        # Add embedding scores (already normalized 0-1)
        for result in embedding_results:
            course_key = (result['OfferingName'], result['SectionName'])
            if course_key in combined_scores:
                combined_scores[course_key]['embedding_norm'] = result['similarity_score']
            else:
                combined_scores[course_key] = {
                    'course': result,
                    'bm25_norm': 0.0,
                    'embedding_norm': result['similarity_score']
                }

        # Calculate final scores
        recommendations = []
        for course_key, scores in combined_scores.items():
            course = scores['course'].copy()
            final_score = (bm25_weight * scores['bm25_norm'] +
                          embedding_weight * scores['embedding_norm'])

            course['combined_score'] = final_score
            course['bm25_score_norm'] = scores['bm25_norm']
            course['embedding_score_norm'] = scores['embedding_norm']
            recommendations.append(course)

        # Sort by combined score and return top-k
        recommendations.sort(key=lambda x: x['combined_score'], reverse=True)
        return recommendations[:top_k]


def main():
    """Example usage."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python course_recommender.py <course_data.json> [user_interests]")
        print("\nExample:")
        print("  python course_recommender.py course_data/courses.json \"machine learning\"")
        sys.exit(1)

    # Load course data
    print("Loading course data...")
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        courses = json.load(f)
    print(f"Loaded {len(courses)} courses")

    # Initialize recommender
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment")
        sys.exit(1)

    recommender = CourseRecommender(api_key=api_key)

    # Build indices
    cache_file = 'course_data/embeddings_cache.pkl'
    recommender.build_index(courses, embedding_cache_file=cache_file)

    # Get user interests
    user_interests = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else \
        "machine learning and artificial intelligence for computer vision"

    print(f"\n{'='*60}")
    print(f"User Interests: {user_interests}")
    print(f"{'='*60}")

    # Example: recommend with previous courses
    previous_courses = None  # e.g., ["EN.500.112", "EN.601.220"]

    results = recommender.recommend(
        user_interests=user_interests,
        previous_courses=previous_courses,
        top_k=10,
        bm25_weight=0.3,
        embedding_weight=0.7
    )

    print(f"\nTop {len(results)} Recommendations:\n")
    for i, course in enumerate(results, 1):
        print(f"{i}. {course.get('Title', 'N/A')} ({course.get('OfferingName', 'N/A')})")
        print(f"   Department: {course.get('Department', 'N/A')}")
        print(f"   Instructor: {course.get('InstructorsFullName', 'N/A')}")
        print(f"   Level: {course.get('Level', 'N/A')}")
        print(f"   Credits: {course.get('Credits', 'N/A')}")
        print(f"   Combined Score: {course['combined_score']:.4f} "
              f"(BM25: {course['bm25_score_norm']:.3f}, Embedding: {course['embedding_score_norm']:.3f})")

        desc = course.get('Description', '')[:200]
        if desc:
            print(f"   Description: {desc}...")

        # Show prerequisites if available
        prereqs = course.get('Prerequisites', [])
        if prereqs and isinstance(prereqs, list):
            for prereq in prereqs[:1]:  # Show first prerequisite
                if isinstance(prereq, dict):
                    prereq_desc = prereq.get('Description', '')
                    if prereq_desc:
                        print(f"   Prerequisites: {prereq_desc[:150]}...")

        print()


if __name__ == "__main__":
    main()

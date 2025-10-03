"""
Flask web application for JHU Course Recommender.
"""
from flask import Flask, render_template, request, jsonify
import json
import os
from dotenv import load_dotenv
from course_recommender import CourseRecommender

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize recommender (load once at startup)
print("Loading course data...")
with open('course_data/courses_20251003_142222.json', 'r', encoding='utf-8') as f:
    courses = json.load(f)

print("Initializing recommender...")
api_key = os.getenv('OPENAI_API_KEY')
recommender = CourseRecommender(api_key=api_key)
recommender.build_index(courses, embedding_cache_file='course_data/embeddings_cache.pkl')
print("Recommender ready!")

# Get unique values for filters
departments = sorted(list(set(c.get('Department', '') for c in courses if c.get('Department'))))
levels = sorted(list(set(c.get('Level', '') for c in courses if c.get('Level'))))
schools = sorted(list(set(c.get('SchoolName', '') for c in courses if c.get('SchoolName'))))


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html',
                         departments=departments,
                         levels=levels,
                         schools=schools)


@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Get course recommendations based on user input.

    Expected JSON payload:
    {
        "query": "user interests",
        "previous_courses": ["EN.601.220", ...],
        "filters": {
            "Department": "EN Computer Science",
            "Level": "Graduate"
        },
        "top_k": 10
    }
    """
    try:
        data = request.get_json()

        query = data.get('query', '')
        if not query:
            return jsonify({'error': 'Query is required'}), 400

        previous_courses = data.get('previous_courses', [])
        filters = data.get('filters', {})
        top_k = data.get('top_k', 10)

        # Remove empty filter values
        filters = {k: v for k, v in filters.items() if v}

        # Get recommendations
        results = recommender.recommend(
            user_interests=query,
            previous_courses=previous_courses if previous_courses else None,
            top_k=top_k,
            filters=filters if filters else None
        )

        # Format results for frontend
        formatted_results = []
        for course in results:
            formatted_results.append({
                'title': course.get('Title', 'N/A'),
                'offering_name': course.get('OfferingName', 'N/A'),
                'section': course.get('SectionName', 'N/A'),
                'department': course.get('Department', 'N/A'),
                'school': course.get('SchoolName', 'N/A'),
                'instructor': course.get('InstructorsFullName', 'N/A'),
                'level': course.get('Level', 'N/A'),
                'credits': course.get('Credits', 'N/A'),
                'description': course.get('Description', 'No description available'),
                'prerequisites': [p.get('Description', '') for p in course.get('Prerequisites', []) if isinstance(p, dict)],
                'status': course.get('Status', 'N/A'),
                'seats': course.get('SeatsAvailable', 'N/A'),
                'meetings': course.get('Meetings', 'N/A'),
                'areas': course.get('Areas', 'N/A'),
                'combined_score': course.get('combined_score', 0),
                'bm25_score': course.get('bm25_score_norm', 0),
                'embedding_score': course.get('embedding_score_norm', 0)
            })

        return jsonify({
            'success': True,
            'results': formatted_results,
            'count': len(formatted_results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)

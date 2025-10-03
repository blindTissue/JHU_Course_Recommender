"""
Flask web application for JHU Course Recommender.
"""
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import json
import os
from dotenv import load_dotenv
from course_recommender import CourseRecommender
from anthropic import Anthropic

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

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


@app.route('/chat', methods=['POST'])
def chat():
    """
    Get AI-powered insights about recommended courses.

    Expected JSON payload:
    {
        "user_query": "I want to learn machine learning",
        "courses": [...],  // Array of course objects
        "message": "Tell me more about these courses"  // Optional
    }
    """
    try:
        data = request.get_json()

        user_query = data.get('user_query', '')
        courses = data.get('courses', [])
        user_message = data.get('message', '')

        if not courses:
            return jsonify({'error': 'No courses provided'}), 400

        # Build context from courses
        course_context = []
        for i, course in enumerate(courses[:10], 1):  # Limit to top 10 for context length
            course_info = f"""
Course {i}: {course.get('title')} ({course.get('offering_name')})
- Department: {course.get('department')}
- Level: {course.get('level')}
- Instructor: {course.get('instructor')}
- Credits: {course.get('credits')}
- Description: {course.get('description', '')[:300]}...
- Prerequisites: {course.get('prerequisites', ['None'])[0] if course.get('prerequisites') else 'None'}
- Match Score: {course.get('combined_score', 0):.3f}
"""
            course_context.append(course_info.strip())

        # Construct prompt for Claude
        system_prompt = """You are a helpful academic advisor for Johns Hopkins University.
Your role is to help students understand course recommendations and make informed decisions about their academic path.
Provide personalized, insightful summaries that highlight:
1. Key themes across recommended courses
2. How courses align with the student's interests
3. Suggested learning paths or course sequences
4. Important prerequisites or preparation needed
5. Career or academic opportunities these courses might open

Be conversational, encouraging, and specific. Reference actual course details."""

        user_prompt = f"""The student is interested in: "{user_query}"

Here are the top recommended courses based on their interests:

{chr(10).join(course_context)}

{f'Student question: {user_message}' if user_message else 'Please provide a helpful summary and overview of these course recommendations, explaining why they match the student interests and suggesting which courses to prioritize.'}"""

        # Stream response from Claude API
        def generate():
            try:
                with anthropic_client.messages.stream(
                    model="claude-sonnet-4-5",
                    max_tokens=1024,
                    temperature=0.7,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                ) as stream:
                    for text in stream.text_stream:
                        yield f"data: {json.dumps({'text': text})}\n\n"

                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)

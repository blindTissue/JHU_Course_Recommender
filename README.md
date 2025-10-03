# JHU Course Recommender 🎓

An intelligent course recommendation system for Johns Hopkins University students, powered by hybrid AI search and interactive chat. Combines BM25 keyword matching with OpenAI semantic embeddings, plus Claude AI for personalized academic advice.

![Python](https://img.shields.io/badge/python-3.13+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.1.2-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-text--embedding--3--small-orange.svg)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude-purple.svg)


## Demo

![Demo][demo.gif]

## Features

- 🔍 **Hybrid Search**: Combines BM25 keyword matching (30%) and OpenAI embeddings (70%) for optimal results
- 💬 **AI Course Advisor**: Chat with Claude AI for personalized insights and course recommendations
- 📚 **10,329 Fall 2025 Courses**: Complete course catalog with descriptions and prerequisites
- 🎯 **Smart Filtering**: Filter by school, department, and level
- 🧠 **Semantic Understanding**: Natural language queries like "I want to learn web development and databases"
- ⚡ **Fast Performance**: Cached embeddings for instant results
- 🎨 **Modern Web UI**: Clean, responsive interface with real-time search and streaming AI responses

## Demo

Try searching for:
- "machine learning and neural networks"
- "web development, databases, and building scalable applications"
- "data science and statistical analysis"

Then ask Claude questions like:
- "Which course should I take first?"
- "How do these courses prepare me for a data science career?"
- "What prerequisites do I need for these courses?"

## Architecture

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│   Flask Web UI          │
│   (app.py)              │
└────┬──────────────┬─────┘
     │              │
     ▼              ▼
┌─────────────────────────┐    ┌──────────────────┐
│  Course Recommender     │    │  Claude AI Chat  │
│  (Hybrid Retrieval)     │    │  (Anthropic)     │
└────┬──────────────┬─────┘    └──────────────────┘
     │              │
     ▼              ▼
┌─────────┐   ┌──────────────┐
│  BM25   │   │    OpenAI    │
│  (30%)  │   │  Embeddings  │
└────┬────┘   └──────┬───────┘
     │               │
     └───────┬───────┘
             ▼
      ┌──────────────┐
      │   Combine    │
      │ 0.3×BM25 +   │
      │ 0.7×Embed    │
      └──────┬───────┘
             ▼
      ┌──────────────┐
      │Ranked Results│
      └──────────────┘
```

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Anthropic API key ([Get one here](https://console.anthropic.com/settings/keys))
- JHU SIS API key (optional, for fetching fresh data)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/blindTissue/JHU_Course_Recommender.git
   cd JHU_Course_Recommender
   ```

2. **Install dependencies with uv**
   ```bash
   uv sync
   ```

   Or with pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Create a `.env` file in the project root:
   ```bash
   # Required: OpenAI API key for embeddings
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx

   # Required: Anthropic API key for Claude AI chat
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx

   # Optional: JHU SIS API key for fetching fresh course data
   JHU_SIS_API_KEY=your_jhu_sis_api_key_here
   ```

   **How to get API keys:**

   - **OpenAI API Key**:
     1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
     2. Sign up or log in
     3. Click "Create new secret key"
     4. Copy the key (starts with `sk-proj-` or `sk-`)
     5. Add billing information (embeddings cost ~$0.50 for initial setup)

   - **Anthropic API Key**:
     1. Visit [Anthropic Console](https://console.anthropic.com/settings/keys)
     2. Sign up or log in
     3. Click "Create Key"
     4. Copy the key (starts with `sk-ant-`)
     5. Add billing information (Claude chat is ~$0.003 per request)

   > **🔒 Security Note**: The `.env` file is already in `.gitignore` to protect your API keys from being committed to git. Never share or commit your API keys!

4. **Run the web application**
   ```bash
   uv run python app.py
   ```

   The app will be available at `http://127.0.0.1:5000`

## Usage

### Web Interface (Recommended)

1. **Open your browser** and navigate to `http://127.0.0.1:5000`

2. **Enter your interests** in natural language:
   - "I want to learn about artificial intelligence and machine learning"
   - "web development, databases, and APIs"
   - "data visualization and statistical computing"

3. **Apply filters** (optional):
   - Filter by school, department, or level
   - Choose number of results (5-20)

4. **Get recommendations** with detailed scores:
   - Combined relevance score
   - BM25 keyword matching score
   - Semantic embedding similarity score

5. **Chat with AI advisor**:
   - Click "Get AI Summary" for an overview
   - Ask specific questions about courses, prerequisites, or learning paths
   - Get personalized advice from Claude AI

### Command Line (Advanced)

You can also use the underlying retrieval systems directly:

**Hybrid Recommender** (recommended):
```bash
uv run python course_recommender.py course_data/courses_20251003_142222.json "machine learning and AI"
```

**BM25 Only** (keyword search):
```bash
uv run python bm25_retrieval.py course_data/courses_20251003_142222.json "machine learning"
```

**Embeddings Only** (semantic search):
```bash
uv run python embedding_retrieval.py course_data/courses_20251003_142222.json "deep learning"
```

## Data Collection

To fetch fresh course data from JHU SIS API:

```bash
uv run python fetch_courses.py
```

This will:
- Fetch all Fall 2025 courses with descriptions
- Cache the data in `course_data/`
- Generate embeddings (one-time cost: ~$0.50)

## Project Structure

```
JHU_Course_Recommender/
├── app.py                      # Flask web application (main entry point)
├── course_recommender.py       # Hybrid recommender (BM25 + embeddings)
├── bm25_retrieval.py          # BM25 keyword search module
├── embedding_retrieval.py     # OpenAI embedding search module
├── fetch_courses.py           # JHU SIS API data fetcher
├── course_data/               # Course data & embeddings (Git LFS)
│   ├── courses_*.json         # Course catalog snapshots
│   └── embeddings_cache.pkl   # Cached OpenAI embeddings
├── templates/
│   └── index.html             # Web UI template
├── static/
│   ├── css/style.css          # Styling
│   └── js/app.js              # Frontend logic & chat interface
└── .env                       # API keys (not in git)
```

## API Endpoints

### POST `/recommend`

Get course recommendations based on user interests.

**Request Body**:
```json
{
  "query": "machine learning and AI",
  "previous_courses": ["EN.601.220"],  // Optional
  "filters": {                          // Optional
    "Department": "EN Computer Science",
    "Level": "Graduate",
    "SchoolName": "Whiting School of Engineering"
  },
  "top_k": 10
}
```

**Response**:
```json
{
  "success": true,
  "results": [
    {
      "title": "Deep Neural Networks",
      "offering_name": "EN.605.742",
      "department": "PE Computer Science",
      "description": "...",
      "combined_score": 0.6221,
      "bm25_score": 1.0000,
      "embedding_score": 0.4601,
      "instructor": "Dr. Smith",
      "credits": 3,
      "seats": 25,
      ...
    }
  ],
  "count": 10
}
```

### POST `/chat`

Get AI-powered insights about recommended courses (streaming response).

**Request Body**:
```json
{
  "user_query": "I want to learn machine learning",
  "courses": [...],  // Array of course objects from /recommend
  "message": "Which course should I take first?"  // Optional
}
```

**Response**: Server-Sent Events (SSE) stream
```
data: {"text": "Based on your interest in machine learning..."}
data: {"text": " I'd recommend starting with..."}
data: {"done": true}
```

## Methodology

### Hybrid Retrieval System

The recommender combines two complementary search methods:

#### BM25 Retrieval (30% weight)
- Traditional keyword-based search algorithm
- Parameters: k1=1.5, b=0.75 (tuned for academic content)
- Indexes multiple fields:
  - Course title (3x weight boost)
  - Description
  - Department
  - Instructors
  - Academic areas
  - Prerequisites
- Best for: Specific course codes, instructor names, technical terms

#### OpenAI Embedding Retrieval (70% weight)
- Model: `text-embedding-3-small` (1536 dimensions)
- Cosine similarity for semantic matching
- Captures semantic meaning and context
- Embeddings cached locally to minimize API costs
- Best for: Natural language queries, conceptual searches, learning goals

#### Hybrid Scoring Formula
```
final_score = 0.3 × BM25_normalized + 0.7 × embedding_similarity
```

Both scores are normalized to [0, 1] range before combining.

### AI Course Advisor

- Uses **Claude 4.5 Sonnet** (Anthropic)
- Provides personalized insights based on:
  - Student's stated interests
  - Recommended courses and their details
  - Course prerequisites and sequences
  - Career and academic pathways
- Streaming responses for real-time interaction
- Context-aware: maintains conversation about current search results

## Performance

- **Index Build Time**: ~2 minutes (first time with embeddings)
- **Query Time**: <1 second (with cached embeddings)
- **Dataset Size**: 10,329 courses (Fall 2025)
- **Embedding Cache**: ~121MB (Git LFS tracked)
- **AI Chat Latency**: ~1-3 seconds (streaming response)

## Cost Estimates

- **Initial Setup**: ~$0.50 (one-time embedding generation for all courses)
- **Per Search**: $0.0001 (query embedding only)
- **Per AI Chat**: ~$0.003-0.01 (varies with conversation length)
- **Total for 100 searches + 20 chats**: ~$0.08

## Technologies

- **Backend**: Flask 3.1.2, Python 3.13
- **Search**:
  - BM25 (custom implementation with TF-IDF)
  - OpenAI `text-embedding-3-small`
- **AI Chat**: Anthropic Claude 4.5 Sonnet (streaming API)
- **Frontend**: Vanilla JavaScript, CSS3, Server-Sent Events (SSE)
- **Data Source**: JHU SIS API (Student Information System)
- **Package Management**: uv (fast Python package manager)

## Future Enhancements

- [ ] User authentication and saved preferences
- [ ] Course schedule builder with conflict detection
- [ ] Visual prerequisite tree/pathway explorer
- [ ] Professor ratings integration (RateMyProfessors)
- [ ] Historical enrollment data and trends
- [ ] Mobile app (React Native)
- [ ] A/B testing different weight combinations (30/70 vs 40/60)
- [ ] Export recommendations to PDF/calendar
- [ ] Degree requirements tracker and progress visualization
- [ ] Multi-term planning (Fall + Spring + Summer)
- [ ] Course comparison feature (side-by-side)
- [ ] Email notifications for seat availability

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this project for educational purposes.

## Acknowledgments

- Johns Hopkins University for the SIS API
- OpenAI for the embedding models
- Anthropic for Claude AI
- The JHU student community

---

**Built with ❤️ for JHU students**

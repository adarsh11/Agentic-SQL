# 🚀 Agentic SQL Backend

This folder contains the FastAPI backend for the Multi-Agent NLP-to-SQL system.

## 🛠 Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Server**:
   ```bash
   python main.py
   ```
    The API will be available at `http://localhost:8000`.

3. **Configure Environment**:
   Copy `.env.example` to `.env` and add your API keys.

## 📌 API Endpoints

### `POST /generate-sql`
Converts natural language queries to SQL.

**Request Body**:
```json
{
  "query": "Who are the top 5 customers by spending?",
  "verbose": true
}
```

**Response**:
```json
{
  "success": true,
  "sql": "SELECT ...",
  "category": "Customer & Sales",
  "tool_order": ["Customer & Sales", ...],
  "evaluation": { ... },
  "planner_reasoning": "...",
  "attempts": 1
}
```

## 📂 Structure
- `main.py`: FastAPI application and endpoints.
- `sql_agent.py`: Multi-agent orchestration logic.
- `llm_client.py`: Singleton LLM client with Groq/Mistral support.
- `.env`: Environment variables (API Keys).

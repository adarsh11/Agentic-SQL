from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from sql_agent import run_nlp_to_sql, CATEGORY_MAP

app = FastAPI(
    title="Agentic SQL API",
    description="Natural Language to SQL Multi-Agent System API",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    verbose: Optional[bool] = True

class QueryResponse(BaseModel):
    success: bool
    sql: Optional[str] = None
    category: Optional[str] = None
    tool_order: Optional[List[str]] = None
    evaluation: Optional[Dict] = None
    planner_reasoning: Optional[str] = None
    attempts: Optional[int] = None
    error: Optional[str] = None
    sql_history: Optional[List[str]] = None  # All SQL attempts including unoptimized
    tool_calls_made: Optional[Dict] = None  # Tool calls per agent

@app.get("/")
async def root():
    return {"status": "online", "message": "Agentic SQL API is running"}

@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    from datetime import datetime
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "service": "agentic-sql-backend"
    }

@app.get("/schema")
async def get_schema():
    """Return database schema information organized by category."""
    try:
        from sql_agent import CATEGORY_MAP
        
        if not CATEGORY_MAP:
            raise ValueError("CATEGORY_MAP is empty or not loaded correctly.")
            
        schema_data = {
            "categories": []
        }
        
        # CATEGORY_MAP is a dict with int keys: {0: {...}, 1: {...}, 2: {...}}
        for key in sorted(CATEGORY_MAP.keys()):
            category_info = CATEGORY_MAP[key]
            category_data = {
                "name": category_info.get("name", "Unknown Category"),
                "tables": category_info.get("tables", [])
            }
            schema_data["categories"].append(category_data)
        
        return schema_data
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"SCHEMA ERROR: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Schema error: {str(e)}")

@app.post("/generate-sql", response_model=QueryResponse)
async def generate_sql(request: QueryRequest):
    """
    Convert Natural Language query to SQL using the Multi-Agent System.
    """
    try:
        result = run_nlp_to_sql(request.query, verbose=request.verbose)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(path_name: str):
    """
    Catch-all route for debugging and handling undefined endpoints.
    """
    return {
        "error": "Endpoint not found",
        "requested_path": path_name,
        "available_endpoints": ["/", "/health", "/generate-sql"]
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

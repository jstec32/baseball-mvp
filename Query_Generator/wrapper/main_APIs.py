from fastapi import FastAPI, Query
from pydantic import BaseModel
from pathlib import Path
from Query_Generator.wrapper.llm_sql import ChatSession
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or use ["http://localhost:8081"] for tighter control
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
session = ChatSession(str(Path(__file__).parent / "sql_generation.txt"))

class QueryRequest(BaseModel):
    question: str
    output_format: str = "json"

@app.post("/query")
def ask_sql(request: QueryRequest):
    return session.query(request.question, request.output_format)

@app.get("/")
def root():
    return {"status": "Server running"}

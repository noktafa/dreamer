from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel

from config import settings
from es_client import get_recent_summary, search_logs
from logging_config import get_logger, setup_logging
from prompt_builder import build_analysis_prompt
from query_parser import parse_question

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="Banking POC LLM RAG Service", version="1.0.0")
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


class AskRequest(BaseModel):
    question: str


@app.post("/api/ask")
async def ask(request: AskRequest):
    question = request.question
    logger.info("Received analysis question", extra={"question": question})

    parsed_query = parse_question(question, openai_client)
    search_results = search_logs(parsed_query)
    messages = build_analysis_prompt(question, search_results)

    try:
        response = openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=2000,
        )
        answer = response.choices[0].message.content

        logger.info(
            "Analysis complete",
            extra={
                "question": question,
                "logs_analyzed": search_results["total"],
                "tokens_used": response.usage.total_tokens if response.usage else 0,
            },
        )

        return {
            "question": question,
            "answer": answer,
            "logs_analyzed": search_results["total"],
            "time_range": parsed_query.get("time_range", "last 1 hour"),
            "model": settings.OPENAI_MODEL,
        }

    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="LLM analysis failed")


@app.get("/api/summary")
async def summary():
    summary_data = get_recent_summary(15)

    prompt = (
        f"Summarize this system health data in 2-3 sentences:\n"
        f"Total logs in last 15 min: {summary_data['total_logs']}\n"
        f"Warnings: {summary_data['warnings_count']}\n"
        f"Error details: {summary_data['errors_by_component']}"
    )

    try:
        response = openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a concise infrastructure health reporter."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        return {
            "summary": response.choices[0].message.content,
            "period": "last 15 minutes",
            "total_logs": summary_data["total_logs"],
            "error_count": summary_data.get("errors_by_component", {}).get("doc_count", 0),
        }
    except Exception as e:
        logger.error(f"Summary generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Summary generation failed")


@app.get("/api/health")
async def health():
    from elasticsearch import Elasticsearch

    es_status = "connected"
    try:
        es = Elasticsearch(f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}")
        es.info()
    except Exception:
        es_status = "disconnected"

    status = "healthy" if es_status == "connected" else "degraded"
    return {"status": status, "elasticsearch": es_status}

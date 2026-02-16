import json
from logging_config import get_logger

logger = get_logger(__name__)

PARSER_SYSTEM_PROMPT = """You are a log query parser. Given a user's question about system health or issues, extract structured search parameters.

Return JSON with these fields:
- "time_range": natural language time range (e.g. "last 2 hours", "last 30 minutes")
- "severity": list of log levels to filter by (e.g. ["ERROR", "WARNING"]). Use empty list for all levels.
- "components": list of components to search (options: "app", "rabbitmq", "nginx_lb", "nginx_app", "queue_consumer", "postgresql", "os_syslog"). Use empty list for all.
- "correlation_id": specific correlation ID if mentioned, otherwise null
- "keywords": list of relevant keywords to search for in log messages

Always return valid JSON."""

DEFAULTS = {
    "time_range": "last 1 hour",
    "severity": [],
    "components": [],
    "correlation_id": None,
    "keywords": [],
}


def parse_question(question: str, openai_client) -> dict:
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": PARSER_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=500,
        )

        parsed = json.loads(response.choices[0].message.content)
        logger.info("Parsed question", extra={"parsed_query": parsed})
        return parsed

    except Exception as e:
        logger.warning(f"Failed to parse question, using defaults: {e}")
        return DEFAULTS.copy()

import re
from datetime import datetime, timedelta, timezone

from elasticsearch import Elasticsearch

from config import settings
from logging_config import get_logger

logger = get_logger(__name__)

es = Elasticsearch(f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}")


def _parse_time_range(time_range: str) -> str:
    match = re.search(r"(\d+)\s*(hour|minute|min|day)", time_range.lower())
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("hour"):
            return f"now-{value}h"
        elif unit.startswith("min"):
            return f"now-{value}m"
        elif unit.startswith("day"):
            return f"now-{value}d"
    return "now-1h"


def search_logs(parsed_query: dict) -> dict:
    try:
        must_filters = []
        should_clauses = []

        time_range = parsed_query.get("time_range", "last 1 hour")
        must_filters.append({"range": {"@timestamp": {"gte": _parse_time_range(time_range)}}})

        severity = parsed_query.get("severity", [])
        if severity:
            must_filters.append({"terms": {"log_data.level": severity}})

        components = parsed_query.get("components", [])
        if components:
            must_filters.append({"terms": {"component": components}})

        cid = parsed_query.get("correlation_id")
        if cid:
            must_filters.append({"term": {"correlation_id": cid}})

        keywords = parsed_query.get("keywords", [])
        for kw in keywords:
            should_clauses.append({"match": {"message": kw}})

        query_body = {
            "query": {
                "bool": {
                    "filter": must_filters,
                }
            },
            "sort": [{"@timestamp": {"order": "desc"}}],
            "size": settings.MAX_LOG_ENTRIES,
            "aggs": {
                "errors_by_component": {
                    "filter": {"term": {"log_data.level": "ERROR"}},
                    "aggs": {
                        "components": {"terms": {"field": "component", "size": 20}},
                    },
                },
                "logs_over_time": {
                    "date_histogram": {"field": "@timestamp", "fixed_interval": "1m"},
                },
            },
        }

        if should_clauses:
            query_body["query"]["bool"]["should"] = should_clauses
            query_body["query"]["bool"]["minimum_should_match"] = 1

        result = es.search(index=settings.ELASTICSEARCH_INDEX, body=query_body)

        hits = [hit["_source"] for hit in result["hits"]["hits"]]
        total = result["hits"]["total"]["value"]
        aggregations = result.get("aggregations", {})

        logger.info("Elasticsearch query completed", extra={"total_hits": total})
        return {"hits": hits, "aggregations": aggregations, "total": total}

    except Exception as e:
        logger.error(f"Elasticsearch query failed: {e}", exc_info=True)
        return {"hits": [], "aggregations": {}, "total": 0}


def get_recent_summary(minutes: int = 15) -> dict:
    try:
        result = es.search(
            index=settings.ELASTICSEARCH_INDEX,
            body={
                "query": {"range": {"@timestamp": {"gte": f"now-{minutes}m"}}},
                "size": 0,
                "aggs": {
                    "total_logs": {"value_count": {"field": "@timestamp"}},
                    "errors_by_component": {
                        "filter": {"term": {"log_data.level": "ERROR"}},
                        "aggs": {
                            "components": {"terms": {"field": "component", "size": 20}},
                        },
                    },
                    "warnings_count": {
                        "filter": {"term": {"log_data.level": "WARNING"}},
                    },
                },
            },
        )
        return {
            "total_logs": result["aggregations"]["total_logs"]["value"],
            "errors_by_component": result["aggregations"]["errors_by_component"],
            "warnings_count": result["aggregations"]["warnings_count"]["doc_count"],
        }
    except Exception as e:
        logger.error(f"Failed to get summary: {e}", exc_info=True)
        return {"total_logs": 0, "errors_by_component": {}, "warnings_count": 0}

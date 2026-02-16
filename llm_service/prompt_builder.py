SYSTEM_PROMPT = """You are a senior Site Reliability Engineer analyzing logs from a banking system infrastructure.

Architecture:
- Nginx Load Balancer (round-robin) → 2x App Servers (FastAPI behind Nginx)
- App Servers publish to RabbitMQ (orders_exchange → orders_queue)
- Queue Consumer reads from RabbitMQ and writes to PostgreSQL
- All components ship structured JSON logs via Filebeat → ELK

Components and their log identifiers:
- nginx_lb: Nginx load balancer access/error logs
- nginx_app: Nginx reverse proxy on app servers
- app: FastAPI application logs
- rabbitmq: RabbitMQ broker logs
- queue_consumer: Python message consumer logs
- postgresql: Database query and error logs
- os_syslog: Operating system logs

When analyzing issues:
1. Identify root cause by tracing correlation IDs across components
2. Determine which component is the source of the problem
3. Assess blast radius (which other components are affected)
4. Suggest concrete remediation steps
5. Rate severity: CRITICAL / HIGH / MEDIUM / LOW

Always reference specific log entries, timestamps, and correlation IDs in your analysis."""

MAX_LOG_LINES = 120  # ~6000 tokens at ~50 tokens per line


def _format_log_entry(hit: dict) -> str:
    ts = hit.get("@timestamp", hit.get("timestamp", "?"))
    component = hit.get("component", hit.get("fields", {}).get("component", "?"))
    server = hit.get("source_server", hit.get("fields", {}).get("server", "?"))
    log_data = hit.get("log_data", {})
    level = log_data.get("level", "?")
    cid = hit.get("correlation_id", log_data.get("correlation_id", "-"))
    message = log_data.get("message", hit.get("message", ""))
    return f"{ts} | {component} | {server} | {level} | {cid} | {message}"


def _format_aggregations(aggregations: dict) -> str:
    lines = []
    errors = aggregations.get("errors_by_component", {})
    if isinstance(errors, dict):
        buckets = errors.get("components", {}).get("buckets", [])
        if buckets:
            lines.append("Errors by component:")
            for b in buckets:
                lines.append(f"  - {b['key']}: {b['doc_count']} errors")

    timeline = aggregations.get("logs_over_time", {})
    if isinstance(timeline, dict):
        buckets = timeline.get("buckets", [])
        if buckets:
            non_zero = [b for b in buckets if b["doc_count"] > 0]
            if non_zero:
                lines.append(f"Log volume: {len(non_zero)} active time buckets")
    return "\n".join(lines) if lines else "No aggregation data available."


def build_analysis_prompt(question: str, search_results: dict) -> list[dict]:
    hits = search_results.get("hits", [])
    total = search_results.get("total", 0)
    aggregations = search_results.get("aggregations", {})

    log_lines = [_format_log_entry(h) for h in hits[:MAX_LOG_LINES]]
    formatted_logs = "\n".join(log_lines)
    error_summary = _format_aggregations(aggregations)

    user_message = f"""## Question
{question}

## Log Data ({total} entries found)
{formatted_logs}

## Error Summary
{error_summary}

Please analyze the above logs and answer the question."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

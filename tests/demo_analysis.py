import asyncio
import time

import httpx

from config import LLM_URL


questions = [
    "What errors occurred in the last 30 minutes?",
    "Which component is generating the most errors?",
    "Are there any slow responses? What might be causing them?",
    "Give me a system health summary",
    "Are there any messages in the dead letter queue? Why did they fail?",
]


async def main():
    print("Starting LLM Analysis Demo...")
    print(f"LLM Service: {LLM_URL}\n")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Health check
        try:
            resp = await client.get(f"{LLM_URL}/api/health")
            health = resp.json()
            print(f"LLM Service Health: {health['status']}")
            print(f"Elasticsearch: {health['elasticsearch']}\n")
        except Exception as e:
            print(f"Health check failed: {e}")
            return

        # Ask questions
        for question in questions:
            print(f"\n{'='*60}")
            print(f"Q: {question}")
            print(f"{'='*60}")

            try:
                resp = await client.post(f"{LLM_URL}/api/ask", json={"question": question})
                data = resp.json()
                print(f"A: {data['answer']}")
                print(f"(Analyzed {data['logs_analyzed']} log entries)")
            except Exception as e:
                print(f"Error: {e}")

            time.sleep(2)

        # Summary
        print(f"\n{'='*60}")
        print("SYSTEM SUMMARY")
        print(f"{'='*60}")

        try:
            resp = await client.get(f"{LLM_URL}/api/summary")
            data = resp.json()
            print(f"Period: {data['period']}")
            print(f"Total logs: {data['total_logs']}")
            print(f"Errors: {data['error_count']}")
            print(f"\n{data['summary']}")
        except Exception as e:
            print(f"Summary failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())

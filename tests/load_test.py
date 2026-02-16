import argparse
import asyncio
import random
import time

import httpx

from config import LB_URL


async def send_order(client: httpx.AsyncClient, url: str, i: int, semaphore: asyncio.Semaphore):
    async with semaphore:
        payload = {
            "customer_id": f"C{i:03d}",
            "amount": round(random.uniform(10, 5000), 2),
            "currency": "TRY",
        }
        start = time.perf_counter()
        try:
            resp = await client.post(f"{url}/api/orders", json=payload)
            duration = (time.perf_counter() - start) * 1000
            return {
                "status": resp.status_code,
                "duration_ms": duration,
                "correlation_id": resp.json().get("correlation_id") if resp.status_code == 202 else None,
            }
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return {"status": 0, "duration_ms": duration, "error": str(e), "correlation_id": None}


async def check_order(client: httpx.AsyncClient, url: str, cid: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        try:
            resp = await client.get(f"{url}/api/orders/{cid}")
            return resp.status_code
        except Exception:
            return 0


async def main():
    parser = argparse.ArgumentParser(description="Load test for Banking POC")
    parser.add_argument("--url", default=LB_URL, help="Load balancer URL")
    parser.add_argument("--count", type=int, default=100, help="Number of orders to send")
    parser.add_argument("--workers", type=int, default=10, help="Concurrent workers")
    args = parser.parse_args()

    print(f"Starting load test: {args.count} orders to {args.url}")
    semaphore = asyncio.Semaphore(args.workers)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Phase 1: Send orders
        tasks = [send_order(client, args.url, i, semaphore) for i in range(args.count)]
        results = await asyncio.gather(*tasks)

        successful = [r for r in results if r["status"] == 202]
        failed = [r for r in results if r["status"] != 202]
        durations = [r["duration_ms"] for r in results]
        durations.sort()

        print(f"\n{'='*50}")
        print(f"LOAD TEST RESULTS")
        print(f"{'='*50}")
        print(f"Total requests:  {len(results)}")
        print(f"Successful (202): {len(successful)}")
        print(f"Failed:           {len(failed)}")
        print(f"Avg response:     {sum(durations)/len(durations):.1f}ms")
        print(f"Min response:     {durations[0]:.1f}ms")
        print(f"Max response:     {durations[-1]:.1f}ms")
        if len(durations) > 1:
            p95_idx = int(len(durations) * 0.95)
            p99_idx = int(len(durations) * 0.99)
            print(f"P95 response:     {durations[p95_idx]:.1f}ms")
            print(f"P99 response:     {durations[p99_idx]:.1f}ms")

        # Phase 2: Verify processing
        correlation_ids = [r["correlation_id"] for r in successful if r["correlation_id"]]
        if correlation_ids:
            print(f"\nWaiting 5 seconds for processing...")
            await asyncio.sleep(5)

            check_tasks = [check_order(client, args.url, cid, semaphore) for cid in correlation_ids]
            check_results = await asyncio.gather(*check_tasks)

            processed = sum(1 for s in check_results if s == 200)
            not_found = sum(1 for s in check_results if s == 404)
            errors = sum(1 for s in check_results if s not in (200, 404))

            print(f"\n{'='*50}")
            print(f"PROCESSING RESULTS")
            print(f"{'='*50}")
            print(f"Checked:    {len(correlation_ids)}")
            print(f"Processed:  {processed}")
            print(f"Not found:  {not_found}")
            print(f"Errors:     {errors}")


if __name__ == "__main__":
    asyncio.run(main())

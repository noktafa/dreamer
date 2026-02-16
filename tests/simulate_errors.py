import asyncio
import httpx

from config import LB_URL


async def main():
    print("Simulating errors...")
    print(f"Target: {LB_URL}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Simulate errors
        print("--- Sending error simulations ---")
        for i in range(10):
            try:
                resp = await client.post(f"{LB_URL}/api/simulate/error")
                data = resp.json()
                print(f"  [{i+1}/10] Error type: {data.get('error_type', '?')} - {data.get('detail', '')[:60]}")
            except Exception as e:
                print(f"  [{i+1}/10] Request failed: {e}")

        # Simulate slow responses
        print("\n--- Sending slow simulations ---")
        for i in range(5):
            try:
                resp = await client.post(f"{LB_URL}/api/simulate/slow")
                data = resp.json()
                print(f"  [{i+1}/5] Delay: {data.get('delay_seconds', '?')}s")
            except Exception as e:
                print(f"  [{i+1}/5] Request failed: {e}")

        print("\nWaiting 30 seconds for log propagation...")
        await asyncio.sleep(30)
        print("Error simulation complete. Logs should now be in Elasticsearch.")


if __name__ == "__main__":
    asyncio.run(main())

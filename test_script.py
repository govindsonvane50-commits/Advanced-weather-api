import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        r = await client.post("http://127.0.0.1:8000/register", json={"username": "testuser2", "password": "password123"})
        print("Register:", r.status_code, r.text)

asyncio.run(test())


import asyncio

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Hermes Agent Runner")

class RunRequest(BaseModel):
    task_id: str
    prompt: str
    agent_id: str

@app.post("/run")
async def run_agent(req: RunRequest):
    # Stub logic representing Hermes running
    out = f"[{req.agent_id}] (Real HTTP) processed task {req.task_id} with prompt: {req.prompt[:50]}..."

    # Simulate processing time
    await asyncio.sleep(1)

    return {
        "task_id": req.task_id,
        "ok": True,
        "output": out,
        "tokens_in": len(req.prompt) // 4,
        "tokens_out": len(out) // 4
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)

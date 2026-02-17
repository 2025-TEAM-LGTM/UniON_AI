from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Req(BaseModel):
    post_id: int

@app.post("/ping")
def ping(req: Req):
    # 통신 확인용: 받은 값 그대로 + 간단 메시지
    return {
        "ok": True,
        "received_post_id": req.post_id,
        "message": "hello from fastapi"
    }
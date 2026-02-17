from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from match.kiwi_algo import main_process

app = FastAPI()

# 통신 확인용: 받은 값 그대로 + 간단 메시지
class MatchReq(BaseModel):
    post_id: int

class MatchResult(BaseModel):
    user_id : int
    main_strength : str

class MatchResponse(BaseModel):
    results: List[MatchResult]

@app.post("/ping")
def ping(req: MatchReq):
    return {
        "ok": True,
        "received_post_id": req.post_id,
        "message": "hello from fastapi"
    }

# spring이 보낸 post_id를 받아 매칭 로직을 실행, 정제된 결과를 Json으로 return
@app.post("/match_result", response_model = MatchResponse)
def match_result(req : MatchReq):
    post_id = req.post_id

    top_users = main_process(post_id)
    results = [
        {"user_id": r["user_id"], "main_strength": r.get("main_strength", "UNKNOWN")}
        for r in top_users
    ]
    return MatchResponse(results = results)




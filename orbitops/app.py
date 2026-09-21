from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app=FastAPI(title="OrbitOps",version="1.0.0")
ROOT=Path(__file__).parent
app.mount("/static",StaticFiles(directory=ROOT/"static"),name="static")
class Mission(BaseModel):
    company:str
    objective:str
    approve_external_action:bool=False
@app.get("/health")
def health(): return {"status":"ok","app":"OrbitOps"}
@app.post("/api/run")
def run(m:Mission):
    steps=[
      {"agent":"Coordinator","action":"plan","status":"completed"},
      {"agent":"Research","action":"prepare synthetic company context","status":"completed"},
      {"agent":"Document","action":"draft onboarding brief","status":"completed"},
      {"agent":"Integration","action":"prepare CRM update","status":"completed"},
      {"agent":"Communication","action":"draft customer message","status":"completed"},
    ]
    external="executed" if m.approve_external_action else "awaiting_human_approval"
    return {"mission":m.model_dump(),"shared_state":{"company":m.company,"objective":m.objective},
            "steps":steps,"external_action":external,"policy_violation":False}
@app.get("/")
def home(): return FileResponse(ROOT/"static"/"index.html")

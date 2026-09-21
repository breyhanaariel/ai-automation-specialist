from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app=FastAPI(title="LedgerLoom",version="1.0.0")
ROOT=Path(__file__).parent
app.mount("/static",StaticFiles(directory=ROOT/"static"),name="static")
class Document(BaseModel):
    vendor:str
    invoice_id:str
    amount:float
    po_amount:float
    confidence:float=0.95
@app.get("/health")
def health(): return {"status":"ok","app":"LedgerLoom"}
@app.post("/api/process")
def process(d:Document):
    issues=[]
    if abs(d.amount-d.po_amount)>0.01: issues.append("amount_mismatch")
    if d.confidence<0.85: issues.append("low_confidence")
    status="awaiting_review" if issues else "ready_for_approval"
    return {"document":d.model_dump(),"status":status,"issues":issues,"auto_approved":False,
            "extraction":{"invoice_id":d.invoice_id,"vendor":d.vendor,"amount":d.amount,"confidence":d.confidence}}
@app.get("/")
def home(): return FileResponse(ROOT/"static"/"index.html")

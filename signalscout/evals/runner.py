from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from app.persistence import Store
from app.schemas import LeadSubmission
from app.workflow import process_lead

def run(path: Path) -> dict:
    rows=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    with TemporaryDirectory() as d:
        store=Store(str(Path(d)/"eval.db"))
        processed=[]
        for row in rows:
            labels=row.pop("labels")
            result=process_lead(LeadSubmission.model_validate(row),store)
            processed.append((labels,result))
    violations=sum(1 for labels,r in processed if labels["spam"] and r["routing"]["route"]!="disqualify")
    unauthorized=sum(1 for _,r in processed if r["outbound_sent"])
    return {"label":"Benchmark result from a labeled synthetic dataset","leads":len(processed),
            "spam_policy_violations":violations,"unauthorized_outbound_sends":unauthorized}

if __name__=="__main__":
    print(json.dumps(run(Path(__file__).parents[1]/"data"/"leads.jsonl"),indent=2))

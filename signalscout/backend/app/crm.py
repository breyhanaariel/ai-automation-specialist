from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CRMResult:
    provider: str
    record_id: str
    task_created: bool

class DemoCRM:
    name="demo"
    def sync(self,lead_id:str)->CRMResult:
        return CRMResult(provider=self.name,record_id=f"demo-{lead_id}",task_created=True)

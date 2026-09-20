from __future__ import annotations
import json, sqlite3
from datetime import UTC, datetime
from threading import Lock
from typing import Any

class Store:
    def __init__(self, url: str = "sqlite:///./signalscout.db") -> None:
        self.url=url; self.lock=Lock(); self.postgres=url.startswith(("postgres://","postgresql://"))
        self._init()

    def _sqlite(self):
        path=self.url.removeprefix("sqlite:///")
        c=sqlite3.connect(path,check_same_thread=False); c.row_factory=sqlite3.Row; return c

    def _pg(self):
        import psycopg
        return psycopg.connect(self.url)

    def _init(self):
        sql="""CREATE TABLE IF NOT EXISTS leads(
        lead_id TEXT PRIMARY KEY,email TEXT NOT NULL,company TEXT NOT NULL,status TEXT NOT NULL,
        payload TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
        CREATE TABLE IF NOT EXISTS audit_events(
        id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,lead_id TEXT NOT NULL,event TEXT NOT NULL,
        detail TEXT NOT NULL,created_at TEXT NOT NULL);"""
        if self.postgres:
            with self._pg() as c:
                with c.cursor() as cur: cur.execute(sql)
        else:
            sql=sql.replace("INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY","INTEGER PRIMARY KEY AUTOINCREMENT")
            with self._sqlite() as c: c.executescript(sql)

    def find_duplicate(self,email:str,company:str,exclude_id:str|None=None)->bool:
        q="SELECT lead_id FROM leads WHERE (lower(email)=lower(%s) OR lower(company)=lower(%s)) AND lead_id != COALESCE(%s,'') LIMIT 1" if self.postgres else "SELECT lead_id FROM leads WHERE (lower(email)=lower(?) OR lower(company)=lower(?)) AND lead_id != COALESCE(?,'') LIMIT 1"
        conn=self._pg() if self.postgres else self._sqlite()
        with conn as c:
            cur=c.cursor(); cur.execute(q,(email,company,exclude_id)); return cur.fetchone() is not None

    def save(self,lead_id:str,email:str,company:str,status:str,payload:dict[str,Any])->None:
        now=datetime.now(UTC).isoformat(); ph="%s" if self.postgres else "?"
        q=f"""INSERT INTO leads(lead_id,email,company,status,payload,created_at,updated_at)
        VALUES({','.join([ph]*7)}) ON CONFLICT(lead_id) DO UPDATE SET
        email=excluded.email,company=excluded.company,status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at"""
        aq=f"INSERT INTO audit_events(lead_id,event,detail,created_at) VALUES({','.join([ph]*4)})"
        conn=self._pg() if self.postgres else self._sqlite()
        with self.lock,conn as c:
            cur=c.cursor(); cur.execute(q,(lead_id,email,company,status,json.dumps(payload),now,now)); cur.execute(aq,(lead_id,"workflow_saved",status,now))

    def list(self)->list[dict[str,Any]]:
        conn=self._pg() if self.postgres else self._sqlite()
        with conn as c:
            cur=c.cursor(); cur.execute("SELECT lead_id,email,company,status,payload,created_at,updated_at FROM leads ORDER BY updated_at DESC")
            cols=[x.name if hasattr(x,"name") else x[0] for x in cur.description]
            return [dict(zip(cols,row,strict=True)) for row in cur.fetchall()]

    def update_status(self,lead_id:str,status:str)->bool:
        ph="%s" if self.postgres else "?"
        q=f"UPDATE leads SET status={ph},updated_at={ph} WHERE lead_id={ph}"
        now=datetime.now(UTC).isoformat(); conn=self._pg() if self.postgres else self._sqlite()
        with conn as c:
            cur=c.cursor(); cur.execute(q,(status,now,lead_id)); changed=cur.rowcount>0
            if changed:
                aq=f"INSERT INTO audit_events(lead_id,event,detail,created_at) VALUES({','.join([ph]*4)})"
                cur.execute(aq,(lead_id,"human_review_decided",status,now))
            return changed

    def metrics(self)->dict[str,int]:
        conn=self._pg() if self.postgres else self._sqlite()
        with conn as c:
            cur=c.cursor(); cur.execute("SELECT status,count(*) FROM leads GROUP BY status"); rows=cur.fetchall()
            cur.execute("SELECT count(*) FROM leads"); total=cur.fetchone()[0]
        return {"total":total,**{r[0]:r[1] for r in rows}}

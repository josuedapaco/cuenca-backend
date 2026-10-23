import hmac
import json
import os
import re
import sqlite3
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, StrictInt, StrictStr, field_validator

ROOT = Path(__file__).parent
MENU = json.loads((ROOT / "menu.json").read_text())
NY = ZoneInfo("America/New_York")

@contextmanager
def database():
    path = Path(os.getenv("DATABASE_PATH", "./data/cuenca.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()

def initialize():
    with database() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS catering_requests (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL,
            email TEXT NOT NULL, event_date TEXT NOT NULL, guests INTEGER NOT NULL,
            dishes TEXT NOT NULL, notes TEXT NOT NULL, language TEXT NOT NULL,
            created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new'
        )""")

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title="Cuenca Coffee Shop API", version="1.0.0", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("PUBLIC_ORIGINS", "https://cuencany.com,https://www.cuencany.com").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"])
attempts = defaultdict(deque)

@app.middleware("http")
async def policy(request: Request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        if origin and origin not in origins:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail":"Origin not allowed"},status_code=403)
        if len(await request.body()) > 16384:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail":"Request too large"},status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/api/health")
def health():
    with database() as db: db.execute("SELECT 1")
    return {"status":"ok","service":"cuenca-api"}

@app.get("/api/menu")
def menu():
    return MENU

@app.get("/api/restaurant")
def restaurant():
    return {"name":"Cuenca Coffee Shop","domain":"cuencany.com","address":"9529 Jamaica Ave., Woodhaven, NY 11421",
            "phones":["+17188474697","+17188474642"],"hours":None,"cuisines":["Ecuadorian","Colombian"]}

class CateringRequest(BaseModel):
    name: StrictStr = Field(min_length=2,max_length=100)
    phone: StrictStr = Field(min_length=7,max_length=30)
    email: StrictStr = Field(default="",max_length=160)
    event_date: date
    guests: StrictInt = Field(ge=1,le=10000)
    dishes: StrictStr = Field(min_length=2,max_length=1000)
    notes: StrictStr = Field(default="",max_length=2000)
    language: StrictStr = Field(default="es",pattern="^(es|en)$")
    consent: bool

    @field_validator("name","phone","dishes")
    @classmethod
    def trim_required(cls,value):
        value=value.strip()
        if len(value)<2: raise ValueError("Required")
        return value

    @field_validator("phone")
    @classmethod
    def phone_valid(cls,value):
        if len(re.sub(r"\D","",value))<7: raise ValueError("Invalid phone")
        return value

    @field_validator("email")
    @classmethod
    def email_valid(cls,value):
        value=value.strip()
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",value): raise ValueError("Invalid email")
        return value

    @field_validator("event_date")
    @classmethod
    def event_future(cls,value):
        if value<datetime.now(NY).date(): raise ValueError("Date is in the past")
        return value

@app.post("/api/catering",status_code=201)
def catering(data:CateringRequest,request:Request):
    if not data.consent: raise HTTPException(400,"Contact consent is required")
    key=request.client.host if request.client else "unknown"
    now=time.monotonic()
    queue=attempts[key]
    while queue and now-queue[0]>3600:queue.popleft()
    if len(queue)>=5: raise HTTPException(429,"Please call us to discuss more requests.")
    ident=str(uuid.uuid4())
    with database() as db:
        db.execute("INSERT INTO catering_requests (id,name,phone,email,event_date,guests,dishes,notes,language,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (ident,data.name,data.phone,data.email,str(data.event_date),data.guests,data.dishes,data.notes.strip(),data.language,datetime.now(NY).isoformat()))
    queue.append(now)
    return {"id":ident,"status":"received","phone":"+17188474697"}

def admin(request:Request):
    configured=os.getenv("ADMIN_API_KEY","")
    provided=request.headers.get("authorization","").removeprefix("Bearer ")
    if not configured or not hmac.compare_digest(configured,provided):raise HTTPException(401,"Unauthorized")

@app.get("/api/admin/catering",dependencies=[Depends(admin)])
def catering_list():
    with database() as db:
        return {"requests":[dict(row) for row in db.execute("SELECT * FROM catering_requests ORDER BY created_at DESC LIMIT 500")]}

# The key is read only by the backend, never returned to the browser.
from .assistant import router as assistant_router
app.include_router(assistant_router)

"""Growth Ledger API. Run with: uvicorn --factory app.main:create_app"""
import json
import sqlite3
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, HTTPException, Path, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from starlette.middleware.sessions import SessionMiddleware

from app import db
from app.auth import authenticate, current_user
from app.config import Settings, load_settings
from app.models import MODELS, WRITE_ROLE, LoginIn

DOC_ID = r"^[A-Za-z0-9_\-.~:@+]{1,200}$"

# The frontend file is written for claude.ai, which wraps it in this skeleton when
# publishing; the server does the same so the one file works in both places.
PAGE_HEAD = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    "<style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);"
    "padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;padding:0;"
    "font:14px -apple-system,BlinkMacSystemFont,sans-serif}img{max-width:100%}"
    "[hidden]{display:none!important}</style></head><body>"
)
PAGE_TAIL = "</body></html>"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    db.init(settings.database_path)

    app = FastAPI(title="Growth Ledger", docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json")
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="gl_session",
        max_age=30 * 24 * 3600,
        same_site="lax",
        https_only=settings.cookie_secure,
    )

    def get_conn():
        conn = db.connect(settings.database_path)
        try:
            yield conn
        finally:
            conn.close()

    Conn = Annotated[sqlite3.Connection, Depends(get_conn)]
    User = Annotated[dict, Depends(current_user)]
    DocId = Annotated[str, Path(pattern=DOC_ID)]

    def table_for(collection: str) -> db.Table:
        if collection not in db.TABLES:
            raise HTTPException(404, "Unknown collection")
        return db.TABLES[collection]

    def check_write(collection: str, user: dict) -> None:
        if WRITE_ROLE[collection] == "admin" and user["role"] != "admin":
            raise HTTPException(403, "Admin access required")

    def validate(collection: str, data: dict) -> dict:
        try:
            return MODELS[collection].model_validate(data).model_dump()
        except ValidationError as e:
            raise HTTPException(422, json.loads(e.json(include_url=False)))

    def save(conn, table: db.Table, doc_id: str, data: dict) -> None:
        try:
            db.upsert(conn, table, doc_id, data)
        except sqlite3.IntegrityError as e:
            raise HTTPException(400, f"Rejected by the database: {e}")

    @app.get("/healthz")
    def healthz(conn: Conn):
        conn.execute("SELECT 1")
        return {"status": "ok"}

    @app.post("/api/login")
    def login(body: LoginIn, request: Request):
        user = authenticate(settings, body.username, body.password)
        if not user:
            raise HTTPException(401, "Wrong username or password")
        request.session.clear()
        request.session["user"] = user
        return user

    @app.post("/api/logout", status_code=204)
    def logout(request: Request):
        request.session.clear()

    @app.get("/api/me")
    def me(user: User):
        return user

    @app.get("/api/{collection}")
    def list_docs(collection: str, user: User, conn: Conn):
        return db.list_all(conn, table_for(collection))

    @app.put("/api/{collection}/{doc_id}", status_code=204)
    def set_doc(collection: str, doc_id: DocId, user: User, conn: Conn, body: dict[str, Any] = Body(...)):
        table = table_for(collection)
        check_write(collection, user)
        save(conn, table, doc_id, validate(collection, body))
        return Response(status_code=204)

    @app.patch("/api/{collection}/{doc_id}", status_code=204)
    def update_doc(collection: str, doc_id: DocId, user: User, conn: Conn, body: dict[str, Any] = Body(...)):
        table = table_for(collection)
        check_write(collection, user)
        existing = db.get(conn, table, doc_id)
        if existing is None:
            raise HTTPException(404, "Not found")
        save(conn, table, doc_id, validate(collection, {**existing, **body}))
        return Response(status_code=204)

    @app.delete("/api/{collection}/{doc_id}", status_code=204)
    def delete_doc(collection: str, doc_id: DocId, user: User, conn: Conn):
        table = table_for(collection)
        check_write(collection, user)
        try:
            db.delete(conn, table, doc_id)
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Still referenced by other records")
        return Response(status_code=204)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return PAGE_HEAD + settings.frontend_path.read_text(encoding="utf-8") + PAGE_TAIL

    return app

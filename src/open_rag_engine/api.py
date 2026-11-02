"""A local HTTP API for the desktop app, reachable only from this machine.

Three guards: only loopback Host headers are served (no DNS rebinding), every request needs the bearer token the app
generated at launch, and CORS allows only the app's own origin. Errors are RFC 9457 problem details without stack
traces or document content.
"""

from __future__ import annotations

import json
import logging
import queue
import secrets
import threading
from dataclasses import asdict
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .answer import Answer
from .documents import PAGE, SOURCE, citation_label
from .ingest import IndexMismatchError
from .library import SECTION_ID, ConflictError, IndexStatus, Library
from .workspace import NotFoundError, Section, WorkspaceError

log = logging.getLogger(__name__)

SNIPPET = 400


class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class SectionIn(NameIn):
    category_id: str = Field(min_length=1, max_length=64)


class SectionPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    category_id: str | None = Field(None, min_length=1, max_length=64)


class FolderIn(BaseModel):
    path: str = Field(min_length=1, max_length=1024)


class ScopeIn(BaseModel):
    kind: Literal["section", "category"]
    id: str = Field(min_length=1, max_length=64)


class TurnIn(BaseModel):
    question: str = Field(max_length=4000)
    answer: str = Field(max_length=20000)


class AskIn(BaseModel):
    scope: ScopeIn
    question: str = Field(min_length=1, max_length=4000)
    history: list[TurnIn] = Field(default_factory=list, max_length=20)


def create_app(library: Library, token: str, origins: list[str]) -> FastAPI:
    expected = f"Bearer {token}".encode()

    def require_token(request: Request) -> None:
        if not secrets.compare_digest(request.headers.get("authorization", "").encode(), expected):
            raise HTTPException(status_code=401, detail="Missing or wrong token")

    app = FastAPI(
        title="open-rag-engine",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(require_token)],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    _add_error_handlers(app)
    ws = library.workspace

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/library")
    def overview() -> dict[str, Any]:
        return {
            "categories": [asdict(c) for c in ws.categories()],
            "sections": [
                {**_section(s), "documents": library.stats(s.id)["documents"], "status": _status(library.status(s.id))}
                for s in ws.sections()
            ],
        }

    @app.post("/categories", status_code=201)
    def add_category(body: NameIn) -> dict[str, str]:
        return asdict(ws.add_category(body.name))

    @app.patch("/categories/{category_id}")
    def rename_category(category_id: str, body: NameIn) -> dict[str, str]:
        return asdict(ws.rename_category(category_id, body.name))

    @app.delete("/categories/{category_id}", status_code=204)
    def delete_category(category_id: str) -> Response:
        ws.delete_category(category_id)
        return Response(status_code=204)

    @app.post("/sections", status_code=201)
    def add_section(body: SectionIn) -> dict[str, Any]:
        return _section(ws.add_section(body.name, body.category_id))

    @app.patch("/sections/{section_id}")
    def update_section(section_id: str, body: SectionPatch) -> dict[str, Any]:
        return _section(ws.update_section(section_id, name=body.name, category_id=body.category_id))

    @app.delete("/sections/{section_id}", status_code=204)
    def delete_section(section_id: str) -> Response:
        library.delete_section(section_id)
        return Response(status_code=204)

    @app.post("/sections/{section_id}/folders")
    def add_folder(section_id: str, body: FolderIn) -> dict[str, Any]:
        from pathlib import Path

        return _section(ws.add_folder(section_id, Path(body.path)))

    @app.post("/sections/{section_id}/folders/remove")
    def remove_folder(section_id: str, body: FolderIn) -> dict[str, Any]:
        return _section(ws.remove_folder(section_id, body.path))

    @app.post("/sections/{section_id}/index", status_code=202)
    def index(section_id: str) -> dict[str, Any]:
        return _status(library.start_indexing(section_id))

    @app.get("/sections/{section_id}/status")
    def status(section_id: str) -> dict[str, Any]:
        return _status(library.status(section_id))

    @app.get("/sections/{section_id}/documents")
    def documents(section_id: str) -> list[dict[str, Any]]:
        return library.documents(section_id)

    @app.post("/ask")
    def ask(body: AskIn) -> StreamingResponse:
        library.scope_sections(body.scope.kind, body.scope.id)  # unknown or busy scopes fail before streaming starts
        history = [(t.question, t.answer) for t in body.history]
        default_section = body.scope.id if body.scope.kind == "section" else None
        events: queue.Queue[dict[str, Any] | None] = queue.Queue()

        def work() -> None:
            try:
                answer = library.ask(
                    body.scope.kind,
                    body.scope.id,
                    body.question,
                    history,
                    on_token=lambda text: events.put({"type": "token", "text": text}),
                )
                events.put({"type": "done", **_answer(answer, default_section)})
            except Exception as error:  # the stream is already open, so the error travels as an event
                status, title, detail = _classify(error)
                events.put({"type": "error", "status": status, "title": title, "detail": detail})
            finally:
                events.put(None)

        threading.Thread(target=work, name="ask", daemon=True).start()

        def lines():
            while (event := events.get()) is not None:
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return StreamingResponse(lines(), media_type="application/x-ndjson")

    return app


def _section(section: Section) -> dict[str, Any]:
    return {
        "id": section.id,
        "name": section.name,
        "category_id": section.category_id,
        "folders": list(section.folders),
    }


def _status(status: IndexStatus) -> dict[str, Any]:
    report = status.report
    return {
        "state": status.state,
        "done": status.done,
        "total": status.total,
        "current": status.current,
        "error": status.error,
        "missing_folders": list(status.missing_folders),
        "report": None
        if report is None
        else {
            "added": len(report.added),
            "updated": len(report.updated),
            "unchanged": len(report.unchanged),
            "removed": len(report.removed),
            "failed": [{"source": s, "error": e} for s, e in report.failed],
        },
    }


def _answer(answer: Answer, default_section: str | None) -> dict[str, Any]:
    def source(number: int) -> dict[str, Any]:
        passage = answer.retrieval.passages[number - 1]
        meta = passage.doc.metadata
        return {
            "number": number,
            "label": citation_label(passage.doc),
            "source": meta.get(SOURCE),
            "page": meta.get(PAGE),
            "section_id": meta.get(SECTION_ID, default_section),
            "score": passage.score,
            "snippet": passage.doc.page_content[:SNIPPET],
        }

    return {
        "question": answer.question,
        "text": answer.text,
        "abstained": answer.abstained,
        "grounded": answer.grounded,
        "invalid_citations": answer.invalid_citations,
        "citations": [source(c.number) for c in answer.citations],
        "sources": [source(n) for n in range(1, len(answer.retrieval.passages) + 1)],
    }


def _classify(error: Exception) -> tuple[int, str, str]:
    if isinstance(error, NotFoundError):
        return 404, "Not found", str(error)
    if isinstance(error, WorkspaceError):
        return 422, "Invalid request", str(error)
    if isinstance(error, ConflictError | IndexMismatchError):
        return 409, "Conflict", str(error)
    if isinstance(error, httpx.ConnectError) or type(error).__name__ == "APIConnectionError":
        return 503, "Language model unavailable", "The local language model isn't running."
    log.exception("Unexpected error", exc_info=error)
    return 500, "Internal error", "Something went wrong. The engine log has the details."


def _problem(status: int, title: str, detail: str) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def _add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException) -> JSONResponse:
        return _problem(error.status_code, "Unauthorized" if error.status_code == 401 else "Error", str(error.detail))

    @app.exception_handler(RequestValidationError)
    async def invalid(_: Request, error: RequestValidationError) -> JSONResponse:
        detail = "; ".join(f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in error.errors())
        return _problem(422, "Invalid request", detail)

    async def known_error(_: Request, error: Exception) -> JSONResponse:
        return _problem(*_classify(error))

    for known in (NotFoundError, WorkspaceError, ConflictError, IndexMismatchError, httpx.ConnectError, Exception):
        app.add_exception_handler(known, known_error)

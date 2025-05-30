import json
import logging
import os

import humanize
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend import config
from backend.api.api_v1.endpoints.customer_endpoints import (
    add_new_customer, get_customer, list_customer_documents)
from backend.api.api_v1.endpoints.documents_endpoints import get_document
from backend.api.api_v1.routers import api_router
from backend.decorators import log_endpoint
from backend.dependencies import get_db, init_db
from backend.utils.helpers import format_analysis

API_V1_STR = "/api/v1"

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Set up logging for the kernel
logging.getLogger("kernel").setLevel(logging.DEBUG)

app = FastAPI(
    title="DocumentIQ API",
    openapi_url=f"{API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redocs"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add the Session Middleware
app.add_middleware(
    SessionMiddleware, secret_key=config.SECRET_KEY, max_age=3600  # 1 hour
)

# Include routers
app.include_router(api_router, prefix=API_V1_STR)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def read_home(request: Request, db=Depends(get_db)):
    logger = logging.getLogger(__name__)

    # Check if the developer parameter is present in the query string
    is_developer = "developer" in request.query_params
    if is_developer:
        logger.info("Developer parameter detected")

    session_id = request.session.get("session_id")
    if session_id:
        logger.info("Existing session_id found: %s", session_id)
    else:
        logger.info("No session_id found, generating a new one.")

    # If no session ID exists, generate a new one
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        request.session["session_id"] = session_id
        logger.info("** Generated new session_id: %s", session_id)
        await add_new_customer(customer_id=session_id, output_language="Slovak", db=db)

    customer = await get_customer(customer_id=session_id, db=db)
    logger.info("Customer data retrieved: %s", customer)

    has_documents = await list_customer_documents(customer_id=session_id, limit=1, db=db)

    logger.info("Rendering index page with session_id: %s", session_id)
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "session_id": session_id,
            "customer": customer,
            "output_language": customer["output_language"],
            "is_developer": is_developer,
            "has_documents": has_documents["documents"]
        }
    )


@app.get("/jan", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def read_jan(request: Request, db=Depends(get_db)):
    return RedirectResponse(url="/?developer", status_code=302)


@app.get("/404", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def read_404(request: Request, db=Depends(get_db)):
    return templates.TemplateResponse("404.html", {"request": request})


@app.get("/reset", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def reset_customer(request: Request, db=Depends(get_db)):
    import uuid
    session_id = str(uuid.uuid4())
    request.session["session_id"] = session_id
    logger.info("** Generated new session_id: %s", session_id)
    await add_new_customer(customer_id=session_id, output_language="Slovak", db=db)
    return RedirectResponse(url="/", status_code=302)


@app.get("/{uuid:path}", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def read_document(request: Request, uuid: str, db=Depends(get_db)):
    logger.info("Rendering document page for path: %s", uuid)

    try:
        document = await get_document(uuid=uuid, db=db)
        document_dict = document.dict() if hasattr(document, "dict") else dict(document)
    except HTTPException as e:
        if e.status_code == 404:
            logger.info("404 returned from get_document, rendering 404.html")
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        raise

    logger.info("Document retrieved: %s", document)

    if document_dict["analysis_status"] != "processed":
        logger.info("Document status is not 'processed', redirecting to home page")
        return RedirectResponse(url="/", status_code=302)

    # Visual Conversions for the template
    document_dict["analysis_started_at"] = document.analysis_started_at.strftime('%Y-%m-%d %H:%M:%S')
    document_dict["analysis_completed_at"] = document.analysis_completed_at.strftime('%Y-%m-%d %H:%M:%S')
    document_dict["ai_analysis_criteria"] = format_analysis(document_dict["ai_analysis_criteria"])
    document_dict["ai_enterny_legacy_schema"] = json.loads(document_dict["ai_enterny_legacy_schema"])
    document_dict["ai_features_and_insights"] = json.loads(document_dict["ai_features_and_insights"])
    document_dict["ai_alerts_and_actions"] = json.loads(document_dict["ai_alerts_and_actions"])
    document_dict["file_size_humanized"] = humanize.naturalsize(document.file_size)
    document_dict["uploaded_at"] = document.uploaded_at.strftime("%b %d, %Y")
    document_dict["filename"] = document_dict["filename"].replace(" ", "_")

    # Shorten filename if too long to fit in the UI
    filename = document_dict["filename"]
    name, ext = os.path.splitext(filename)
    if len(filename) > 44:
        max_name_length = 44 - len(ext) - 2  # 2 for ".."
        name = name[:max_name_length] + ".."
        document_dict["filename"] = name + ext

    if document.ai_expires:
        document_dict["ai_expires"] = document.ai_expires.strftime("%b %d, %Y")

    document = document_dict

    return templates.TemplateResponse("document.html", {"request": request, "document": document})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

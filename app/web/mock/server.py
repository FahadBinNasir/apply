from pathlib import Path
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

MOCKS_DIR = Path("contracts/mocks")

mock_app = FastAPI(title="UI Mock Server")
templates = Jinja2Templates(directory="app/web/templates")
mock_app.mount("/static", StaticFiles(directory="app/web/static"), name="static")


@mock_app.get("/")
def mock_index():
    with open(MOCKS_DIR / "inbox_normal.json", "r", encoding="utf-8") as f:
        vm = json.load(f)
    return vm


@mock_app.get("/jobs/job_paysys_devops")
def mock_detail():
    with open(MOCKS_DIR / "job_detail_f1.json", "r", encoding="utf-8") as f:
        vm = json.load(f)
    return vm


@mock_app.get("/sent")
def mock_sent():
    with open(MOCKS_DIR / "sent_log.json", "r", encoding="utf-8") as f:
        return json.load(f)


@mock_app.get("/skipped")
def mock_skipped():
    with open(MOCKS_DIR / "skipped_list.json", "r", encoding="utf-8") as f:
        return json.load(f)


@mock_app.get("/opportunities")
def mock_opps():
    with open(MOCKS_DIR / "opportunities.json", "r", encoding="utf-8") as f:
        return json.load(f)


@mock_app.get("/whatsapp")
def mock_whatsapp():
    with open(MOCKS_DIR / "whatsapp_status.json", "r", encoding="utf-8") as f:
        return json.load(f)


@mock_app.get("/settings")
def mock_settings():
    with open(MOCKS_DIR / "settings.json", "r", encoding="utf-8") as f:
        return json.load(f)


@mock_app.get("/health")
def mock_health():
    with open(MOCKS_DIR / "health_normal.json", "r", encoding="utf-8") as f:
        return json.load(f)

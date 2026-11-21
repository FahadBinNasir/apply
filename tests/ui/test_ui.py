from pathlib import Path
import json
import pytest
from starlette.testclient import TestClient

from app.web.mock.server import mock_app
from fastapi.templating import Jinja2Templates


def test_ui_spec_docs():
    product_md = Path("PRODUCT.md")
    assert product_md.exists()
    content = product_md.read_text(encoding="utf-8")
    assert "Operate" in content
    assert "Fahad" in content

    design_md = Path("DESIGN.md")
    assert design_md.exists()
    content_d = design_md.read_text(encoding="utf-8")
    assert "Dark Theme" in content_d
    assert "Light Theme" in content_d


def test_css_tokens_and_touch_targets():
    css_path = Path("app/web/static/style.css")
    assert css_path.exists()
    css = css_path.read_text(encoding="utf-8")
    assert "--touch-target: 44px" in css
    assert "--tier-strong" in css
    assert "--tier-stretch" in css
    assert "--tier-skipped" in css


def test_templates_exist():
    templates_dir = Path("app/web/templates")
    required = ["base.html", "index.html", "job_detail.html", "sent.html", "skipped.html", "opportunities.html", "whatsapp.html", "settings.html"]
    for t in required:
        assert (templates_dir / t).exists(), f"Missing template: {t}"


def test_mock_server_endpoints():
    with TestClient(mock_app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert "active_tab" in res.json()

        res_detail = client.get("/jobs/job_paysys_devops")
        assert res_detail.status_code == 200
        assert res_detail.json()["job"]["company"] == "Paysys Labs"

        res_sent = client.get("/sent")
        assert res_sent.status_code == 200

        res_skipped = client.get("/skipped")
        assert res_skipped.status_code == 200

        res_health = client.get("/health")
        assert res_health.status_code == 200

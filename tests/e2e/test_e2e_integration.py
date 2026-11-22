import asyncio
import os
import pytest
from starlette.testclient import TestClient

from app.auth.security import create_session_token
from app.main import app
from contracts.models import Status, Tier


@pytest.fixture
def client():
    os.environ["USE_FAKES"] = "true"
    os.environ["SEND_ENABLED"] = "false"
    with TestClient(app) as c:
        # Pre-set authenticated cookie
        secret = os.getenv("SESSION_SECRET", "dev_session_secret_change_in_production")
        token = create_session_token(secret, user_id="fahad")
        c.cookies.set("session_token", token)
        yield c


def test_e2e_flow_f1_paysys_devops(client):
    # 1. Simulate F1 incoming post
    f1_text = """We're Hiring – *DevOps Engineer!*
Paysys Labs is looking for an enthusiastic and detail-oriented DevOps Engineer to join our growing team!
📍 Location: *Karachi (On-site)*
💼 Experience: *0–1 Years | Fresh Graduates Encouraged to Apply*
Key Skills & Requirements:
CI/CD pipelines and automation
Linux administration and troubleshooting
On-premises deployments and release management
SQL and relational databases
Git and version control
Scripting and process automation
API testing and test automation
Basic understanding of AI-assisted development and automation tools
🎓 Qualification: Bachelor's degree in Computer Science, Software Engineering, IT, or a related field.
📩 Apply Now!
Send your updated CV to hiring@paysyslabs.com with the subject line "DevOps Engineer – Application"."""

    sim_res = client.post("/api/dev/simulate", json={"text": f1_text, "chat_name": "Bahria CS Alumni"})
    assert sim_res.status_code == 200
    data = sim_res.json()
    assert len(data["jobs_created"]) == 1
    job = data["jobs_created"][0]

    assert job["tier"] == "STRONG"
    assert job["role"]["company"] == "Paysys Labs"
    assert job["role"]["exact_subject"] == "DevOps Engineer – Application"
    assert job["role"]["apply_email"] == "hiring@paysyslabs.com"

    job_id = job["id"]

    # 2. Check Job Detail View
    detail_res = client.get(f"/jobs/{job_id}", headers={"accept": "application/json"})
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["job"]["title"] == "DevOps Engineer"
    assert detail_data["draft"]["subject"] == "DevOps Engineer – Application"
    assert "7th" in detail_data["draft"]["body"] and "semester" in detail_data["draft"]["body"]

    # 3. Approve & Send (Dry Run)
    send_res = client.post(f"/api/jobs/{job_id}/approve-send")
    assert send_res.status_code == 200
    assert send_res.json()["status"] == "dry_run"
    assert "dry_run" in send_res.json()["message_id"]

    # 4. Verify Sent Log
    sent_res = client.get("/sent", headers={"accept": "application/json"})
    assert sent_res.status_code == 200
    assert len(sent_res.json()["sends"]) >= 1
    assert sent_res.json()["sends"][0]["status"] == "dry_run"


def test_e2e_flow_f4_skipped_and_rescue(client):
    # F4 Lahore post
    f4_text = """HIRING | *Associate Software Engineer (ASE)* PAID INTERNSHIP!
Position: ASE - iOS Developer | Experience: Freshers Welcome | Location: Johar Town, Lahore
Share your CV at hr@pentaloop.com"""

    sim_res = client.post("/api/dev/simulate", json={"text": f4_text, "chat_name": "Alumni"})
    assert sim_res.status_code == 200
    job = sim_res.json()["jobs_created"][0]

    # Verify skipped
    assert job["tier"] == "SKIPPED"
    job_id = job["id"]

    # Verify appeared in Skipped list
    skipped_res = client.get("/skipped", headers={"accept": "application/json"})
    assert skipped_res.status_code == 200
    skipped_data = skipped_res.json()
    assert "location" in skipped_data["by_reason"]

    # Test Rescue action
    rescue_res = client.post(f"/api/jobs/{job_id}/rescue")
    assert rescue_res.status_code == 200
    assert rescue_res.json()["status"] == "rescued"
    assert rescue_res.json()["tier"] == "STRETCH"

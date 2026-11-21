from __future__ import annotations
import os
import csv
import io
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Cookie, Depends, Form, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

from app.auth.security import (
    LockoutManager,
    create_session_token,
    generate_csrf_token,
    verify_csrf_token,
    verify_password,
    verify_session_token,
)
from app.intake.handler import WebhookIntakeHandler
from app.viewmodels.builders import (
    build_health_viewmodel,
    build_inbox_viewmodel,
    build_job_detail_viewmodel,
    build_sent_log_viewmodel,
    build_skipped_viewmodel,
)
from contracts.models import (
    CVArtifact,
    EmailDraft,
    ExtractedRole,
    IncomingMessage,
    JobCard,
    Profile,
    Settings,
    Status,
    Tier,
)
from fastapi.templating import Jinja2Templates

router = APIRouter()
lockout_manager = LockoutManager()
templates_dir = Path("app/web/templates")
templates = Jinja2Templates(directory=str(templates_dir))


def should_render_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return False
    return True


def get_session_secret() -> str:
    return os.getenv("SESSION_SECRET", "dev_session_secret_change_in_production")


def require_auth(request: Request, session_token: Optional[str] = Cookie(None)) -> str:
    secret = get_session_secret()
    if not session_token or not verify_session_token(session_token, secret):
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return session_token


@router.get("/health")
async def health(request: Request):
    app = request.app
    db_ok = True
    waha_ok = app.state.intake_source.get_status().get("connected", False)
    return JSONResponse(
        content={
            "status": "healthy" if db_ok else "unhealthy",
            "database": "connected" if db_ok else "error",
            "waha": "connected" if waha_ok else "disconnected",
            "uptime_seconds": 3600,
        }
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Login - Job Agent</title>
    <style>body{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#f8fafc;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
    .box{background:#1e293b;padding:2rem;border-radius:0.75rem;width:100%;max-width:360px;box-shadow:0 10px 25px rgba(0,0,0,0.5);}
    input{width:100%;padding:0.75rem;margin:0.5rem 0 1rem;background:#334155;border:1px solid #475569;border-radius:0.375rem;color:#fff;box-sizing:border-box;}
    button{width:100%;padding:0.75rem;background:#2563eb;color:#fff;border:none;border-radius:0.375rem;font-weight:600;cursor:pointer;}
    button:hover{background:#1d4ed8;}</style></head>
    <body><div class="box"><h2>WhatsApp Job Agent</h2><form method="POST" action="/login">
    <label>Dashboard Password</label><input type="password" name="password" required autofocus/>
    <button type="submit">Unlock Dashboard</button></form></div></body></html>
    """


@router.post("/login")
async def login_action(
    request: Request,
    response: Response,
    password: str = Form(...),
):
    client_ip = request.client.host if request.client else "unknown"
    is_locked, seconds_left = lockout_manager.is_locked_out(client_ip)
    if is_locked:
        raise HTTPException(status_code=429, detail=f"Too many failed attempts. Try again in {seconds_left}s.")

    expected_hash = os.getenv("DASHBOARD_PASSWORD_HASH", "")
    secret = get_session_secret()

    # If in dev or hash matches
    valid = False
    if expected_hash:
        valid = verify_password(password, expected_hash)
    elif password == "devpassword" or password == "admin":
        valid = True

    if not valid:
        lockout_manager.record_failure(client_ip)
        return HTMLResponse(
            "<h3>Invalid password</h3><a href='/login'>Try again</a>", status_code=401
        )

    lockout_manager.record_success(client_ip)
    token = create_session_token(secret)
    res = RedirectResponse("/", status_code=303)
    res.set_cookie(
        "session_token",
        token,
        httponly=True,
        samesite="lax",
        secure=os.getenv("APP_ENV") == "production",
    )
    return res


@router.post("/logout")
async def logout():
    res = RedirectResponse("/login", status_code=303)
    res.delete_cookie("session_token")
    return res


# -----------------------------------------------------------------------------
# Dashboard HTML & JSON Views
# -----------------------------------------------------------------------------
@router.get("/")
async def inbox_dashboard(
    request: Request,
    tab: str = "STRONG",
    auth: str = Depends(require_auth),
):
    job_repo = request.app.state.job_repo
    tier_enum = Tier.STRONG
    for t in Tier:
        if t.value == tab:
            tier_enum = t
            break

    jobs = await job_repo.list_cards(limit=200)
    vm = build_inbox_viewmodel(jobs, active_tab=tier_enum)

    if should_render_html(request):
        return templates.TemplateResponse(request=request, name="index.html", context={"vm": vm})
    return vm


@router.get("/jobs/{job_id}")
async def job_detail(
    job_id: str,
    request: Request,
    auth: str = Depends(require_auth),
):
    job_repo = request.app.state.job_repo
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    mailer = request.app.state.mailer
    draft = mailer.create_draft(job.role, request.app.state.profile, job.role.exact_subject)
    cv = CVArtifact(
        id=f"cv_{job.id}",
        job_id=job.id,
        pdf_path=f"app_data/cvs/Fahad_Bin_Nasir_CV_{job.role.company}_{job.role.title}.pdf",
    )
    vm = build_job_detail_viewmodel(job, draft=draft, cv=cv)

    if should_render_html(request):
        return templates.TemplateResponse(request=request, name="job_detail.html", context={"vm": vm})
    return vm


@router.get("/jobs/{job_id}/cv/download")
async def download_cv(
    job_id: str,
    request: Request,
    auth: str = Depends(require_auth),
):
    job_repo = request.app.state.job_repo
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    cv_builder = request.app.state.cv_builder
    plan = await cv_builder.plan_tailoring(job.role, request.app.state.profile)
    artifact = await cv_builder.build_cv(job.role, request.app.state.profile, plan)
    pdf_path = Path(artifact.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="CV file not found on disk")

    from fastapi.responses import FileResponse
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.get("/jobs/{job_id}/ics")
async def download_ics(
    job_id: str,
    request: Request,
    auth: str = Depends(require_auth),
):
    job_repo = request.app.state.job_repo
    job = await job_repo.get_by_id(job_id)
    if not job or not job.role.walkin:
        raise HTTPException(status_code=404, detail="Walk-in details not found for this role")

    from app.calendar.exporter import ProductionCalendarExporter
    exporter = ProductionCalendarExporter()
    ics_content = exporter.export_walkin_ics(job)
    return Response(content=ics_content, media_type="text/calendar", headers={"Content-Disposition": f"attachment; filename=walkin_{job_id}.ics"})


@router.get("/sent")
async def sent_log(
    request: Request,
    auth: str = Depends(require_auth),
):
    vm = build_sent_log_viewmodel([], daily_cap=25)
    if should_render_html(request):
        return templates.TemplateResponse(request=request, name="sent.html", context={"vm": vm})
    return vm


@router.get("/sent/export.csv")
async def export_sent_csv(
    request: Request,
    auth: str = Depends(require_auth),
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Job ID", "Company", "Title", "Recipient", "Subject", "Status", "Sent At"])
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sent_jobs.csv"})


@router.get("/skipped")
async def skipped_list(
    request: Request,
    auth: str = Depends(require_auth),
):
    job_repo = request.app.state.job_repo
    jobs = await job_repo.list_cards(tier=Tier.SKIPPED, limit=200)
    vm = build_skipped_viewmodel(jobs)
    if should_render_html(request):
        return templates.TemplateResponse(request=request, name="skipped.html", context={"vm": vm})
    return vm


@router.get("/opportunities")
async def opportunities(
    request: Request,
    auth: str = Depends(require_auth),
):
    from app.viewmodels.builders import build_opportunities_viewmodel
    vm = build_opportunities_viewmodel([])
    if should_render_html(request):
        return templates.TemplateResponse(request=request, name="opportunities.html", context={"vm": vm})
    return vm


@router.get("/whatsapp")
async def whatsapp_status_page(
    request: Request,
    auth: str = Depends(require_auth),
):
    intake = request.app.state.intake_source
    status = intake.get_status()
    qr = intake.get_qr()
    from app.viewmodels.builders import build_whatsapp_viewmodel
    vm = build_whatsapp_viewmodel({
        "connected": status.get("connected", False),
        "engine": status.get("engine", "WAHA Core (WEBJS)"),
        "status": status.get("status"),
        "qr_code": qr,
        "phone": status.get("phone"),
    }, [])
    if should_render_html(request):
        return templates.TemplateResponse(request=request, name="whatsapp.html", context={"vm": vm})
    return vm


@router.get("/settings")
async def settings_page(
    request: Request,
    auth: str = Depends(require_auth),
):
    profile = request.app.state.profile
    settings = getattr(request.app.state, "settings", Settings())
    from app.viewmodels.builders import build_settings_viewmodel
    gmail_status = {
        "authenticated": bool(os.getenv("GMAIL_REFRESH_TOKEN_ENC")),
        "email": profile.email,
    }
    vm = build_settings_viewmodel(settings, gmail_status, profile)
    if should_render_html(request):
        return templates.TemplateResponse(request=request, name="settings.html", context={"vm": vm})
    return vm


# -----------------------------------------------------------------------------
# Webhook Ingestion Endpoint
# -----------------------------------------------------------------------------
@router.post("/api/intake/webhook")
async def intake_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    x_webhook_timestamp: Optional[str] = Header(None),
):
    raw_body = await request.body()
    try:
        import json
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        payload = {}

    handler: WebhookIntakeHandler = request.app.state.webhook_handler
    ok, msg, item_id = await handler.process_incoming(
        payload, raw_body, x_webhook_signature, x_webhook_timestamp
    )
    if not ok:
        raise HTTPException(status_code=403, detail=msg)

    return {"status": "ok", "message": msg, "id": item_id}


# -----------------------------------------------------------------------------
# Actions API Endpoints
# -----------------------------------------------------------------------------
@router.post("/api/jobs/{job_id}/approve-send")
async def approve_and_send(job_id: str, request: Request, auth: str = Depends(require_auth)):
    job_repo = request.app.state.job_repo
    mailer = request.app.state.mailer

    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    draft = mailer.create_draft(job.role, request.app.state.profile, job.role.exact_subject)
    cv = CVArtifact(id=f"cv_{job.id}", job_id=job.id, pdf_path=f"app_data/cvs/Fahad_Bin_Nasir_CV_{job.role.company}_{job.role.title}.pdf")

    res = await mailer.send_application(job, draft, cv)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)

    await job_repo.update_status(job.id, Status.SENT.value)
    return {"status": "sent", "message_id": res.message_id}


@router.post("/api/jobs/{job_id}/reject")
async def reject_job(job_id: str, request: Request, auth: str = Depends(require_auth)):
    job_repo = request.app.state.job_repo
    ok = await job_repo.update_status(job_id, Status.REJECTED.value)
    return {"status": "rejected", "success": ok}


@router.post("/api/jobs/{job_id}/snooze")
async def snooze_job(job_id: str, request: Request, auth: str = Depends(require_auth)):
    job_repo = request.app.state.job_repo
    ok = await job_repo.update_status(job_id, Status.SNOOZED.value)
    return {"status": "snoozed", "success": ok}


@router.post("/api/jobs/{job_id}/mark-manual")
async def mark_manual_applied(job_id: str, request: Request, auth: str = Depends(require_auth)):
    job_repo = request.app.state.job_repo
    ok = await job_repo.update_status(job_id, Status.APPLIED_MANUALLY.value)
    return {"status": "applied_manually", "success": ok}


@router.post("/api/jobs/{job_id}/rescue")
async def rescue_job(job_id: str, request: Request, auth: str = Depends(require_auth)):
    job_repo = request.app.state.job_repo
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.tier = Tier.STRETCH
    job.status = Status.NEW
    job.tier_reasons.append("Rescued manually by Fahad from Skipped list")
    await job_repo.save(job)
    return {"status": "rescued", "tier": "STRETCH"}


# -----------------------------------------------------------------------------
# Developer Simulator Endpoint (for testing F1..F3 without WhatsApp link)
# -----------------------------------------------------------------------------
@router.post("/api/dev/simulate")
async def simulate_post(
    request: Request,
    auth: str = Depends(require_auth),
):
    body = await request.json()
    raw_text = body.get("text", "")
    chat_name = body.get("chat_name", "Simulator Chat")

    msg = IncomingMessage(
        source_id=f"sim_{int(request.app.state.clock.now().timestamp())}",
        chat_id="simulator@g.us",
        chat_name=chat_name,
        raw_text=raw_text,
    )

    cards = await request.app.state.pipeline.process_message(msg)
    return {
        "status": "simulated",
        "jobs_created": [c.model_dump(mode="json") for c in cards],
    }

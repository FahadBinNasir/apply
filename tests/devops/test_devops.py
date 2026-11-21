from pathlib import Path
import yaml
import pytest


def test_docker_compose_structure():
    compose_path = Path("docker-compose.yml")
    assert compose_path.exists()
    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    services = data.get("services", {})
    assert "whatsapp" in services
    assert "app" in services
    assert "proxy" in services

    # Verify memory limits & healthchecks
    assert "deploy" in services["app"]
    assert "healthcheck" in services["app"]
    assert "healthcheck" in services["whatsapp"]

    # Verify volumes
    assert "app_data" in data.get("volumes", {})
    assert "wa_session" in data.get("volumes", {})


def test_env_example():
    env_example = Path(".env.example")
    assert env_example.exists()
    content = env_example.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" in content
    assert "DASHBOARD_PASSWORD_HASH" in content
    assert "SESSION_SECRET" in content
    assert "SEND_ENABLED" in content


def test_scripts_and_ci():
    assert Path("scripts/backup.sh").exists()
    assert Path("scripts/backup.ps1").exists()
    assert Path("scripts/restore.sh").exists()
    assert Path("scripts/restore.ps1").exists()
    assert Path("docker/Dockerfile.app").exists()

    ci_path = Path(".github/workflows/ci.yml")
    assert ci_path.exists()
    with open(ci_path, "r", encoding="utf-8") as f:
        ci_data = yaml.safe_load(f)
    assert "jobs" in ci_data

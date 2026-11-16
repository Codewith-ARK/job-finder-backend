import pytest

from app.config import Settings, configuration_problems


def test_production_rejects_unsafe_configuration():
    settings = Settings(
        _env_file=None,
        app_environment="production",
        cookie_secure=False,
        demo_login_enabled=True,
        seed_on_startup=True,
        docs_testing_enabled=True,
        cors_origins="http://localhost:3000",
    )
    errors = [message for level, message in configuration_problems(settings) if level == "error"]
    assert len(errors) >= 5


def test_production_disables_documentation(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import create_app

    settings = get_settings()
    for key, value in {
        "app_environment": "production",
        "cookie_secure": True,
        "demo_login_enabled": False,
        "seed_on_startup": False,
        "docs_testing_enabled": False,
        "cors_origins": "https://example.com",
        "database_url": "postgresql://jobfinder:test@localhost/jobfinder",
    }.items():
        monkeypatch.setattr(settings, key, value, raising=False)
    production = create_app()
    client = TestClient(production)
    try:
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/docs").status_code == 404
    finally:
        client.close()
    with pytest.raises(RuntimeError, match="seeded demo database"), TestClient(production):
        pass


@pytest.mark.parametrize("field", ["session_cookie", "csrf_cookie"])
def test_cookie_names_cannot_inject_docs_script(field):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **{field: "cookie</script><script>alert(1)</script>"})

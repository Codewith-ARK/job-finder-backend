from app.config import get_settings


def upload(client, csrf, filename="cv.pdf", content=None, content_type="application/pdf"):
    from app.seed import MINIMAL_PDF

    return client.post(
        "/api/candidates/me/documents",
        files={"file": (filename, content or MINIMAL_PDF, content_type)},
        headers={"X-CSRF-Token": csrf},
    )


def test_document_count_quota(sign_in, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_documents_per_candidate", 1, raising=False)
    client, csrf, _ = sign_in("Aya Khan")
    assert upload(client, csrf).status_code == 200
    assert upload(client, csrf).status_code == 409
    assert len(client.get("/api/candidates/me").json()["documents"]) == 1


def test_document_aggregate_quota(sign_in, monkeypatch):
    from app.seed import MINIMAL_PDF

    monkeypatch.setattr(
        get_settings(), "max_candidate_document_bytes", len(MINIMAL_PDF) + 5, raising=False
    )
    client, csrf, _ = sign_in("Aya Khan")
    assert upload(client, csrf).status_code == 200
    assert upload(client, csrf).status_code == 409


def test_long_filename_returns_validation_error(sign_in):
    client, csrf, _ = sign_in("Aya Khan")
    client.raise_server_exceptions = False
    assert upload(client, csrf, "cv." + "a" * 300).status_code == 409


def test_storage_extension_comes_from_type(sign_in):
    from pathlib import Path

    from app.database import SessionLocal
    from app.models import Document

    client, csrf, _ = sign_in("Aya Khan")
    response = upload(client, csrf, "cv.html")
    assert response.status_code == 200
    with SessionLocal() as db:
        doc = db.get(Document, response.json()["documents"][0]["id"])
        assert Path(doc.storage_path).suffix == ".pdf"


def test_document_structure_must_match_its_type(sign_in):
    client, csrf, _ = sign_in("Aya Khan")
    docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert upload(client, csrf, "cv.pdf", b"<html>not a pdf</html>").status_code == 409
    assert (
        upload(client, csrf, "cv.docx", b"PK\x03\x04not-a-docx", docx).status_code == 409
    )
    assert upload(client, csrf, "cv.pdf", b"%PDF-1.4\ntruncated").status_code == 409
    assert len(client.get("/api/candidates/me").json()["documents"]) == 0

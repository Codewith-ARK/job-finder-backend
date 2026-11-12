import asyncio
import threading

import httpx
from starlette.datastructures import UploadFile

from app.main import app
from app.services import candidates_service


def test_upload_service_does_not_block_event_loop(sign_in, monkeypatch):
    client, csrf, _ = sign_in("Aya Khan")
    threads = {}
    original_read = UploadFile.read
    original_add = candidates_service.add_document

    async def read(self, *args, **kwargs):
        threads["loop"] = threading.get_ident()
        return await original_read(self, *args, **kwargs)

    def add(*args, **kwargs):
        threads["service"] = threading.get_ident()
        return original_add(*args, **kwargs)

    monkeypatch.setattr(UploadFile, "read", read)
    monkeypatch.setattr(candidates_service, "add_document", add)

    async def upload():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            cookies=dict(client.cookies),
        ) as connection:
            response = await connection.post(
                "/api/candidates/me/documents",
                files={"file": ("cv.pdf", b"%PDF-test", "application/pdf")},
                headers={"X-CSRF-Token": csrf},
            )
            assert response.status_code == 200

    asyncio.run(upload())
    assert threads["loop"] != threads["service"]

def test_document_download_documents_binary_content(client):
    operation = client.get("/openapi.json").json()["paths"][
        "/api/candidates/me/documents/{document_id}"
    ]["get"]
    content = operation["responses"]["200"]["content"]
    assert "application/json" not in content
    assert content["application/pdf"]["schema"]["format"] == "binary"

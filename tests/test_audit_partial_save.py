def test_personal_partial_save_retains_saved_fields(sign_in):
    client, csrf, _ = sign_in("Aya Khan")
    headers = {"X-CSRF-Token": csrf}
    assert (
        client.put(
            "/api/candidates/me/onboarding/personal",
            json={
                "phone": "12345",
                "headline": "Engineer",
                "location": "Lahore",
            },
            headers=headers,
        ).status_code
        == 200
    )
    response = client.put(
        "/api/candidates/me/onboarding/personal", json={"summary": "Changed"}, headers=headers
    )
    assert response.json()["profile"]["phone"] == "12345"


def test_professional_partial_save_retains_collections(sign_in):
    client, csrf, _ = sign_in("Aya Khan")
    headers = {"X-CSRF-Token": csrf}
    client.put(
        "/api/candidates/me/onboarding/personal",
        json={
            "phone": "12345",
            "headline": "Engineer",
            "location": "Lahore",
        },
        headers=headers,
    )
    assert (
        client.post("/api/candidates/me/onboarding/personal/complete", headers=headers).status_code
        == 200
    )
    client.put(
        "/api/candidates/me/onboarding/professional",
        json={
            "currentTitle": "Engineer",
            "experienceLevel": "Mid",
            "skills": ["Python"],
            "preferences": {"workType": "Remote", "preferredLocation": "Lahore"},
        },
        headers=headers,
    )
    response = client.put(
        "/api/candidates/me/onboarding/professional",
        json={
            "experienceLevel": "Mid",
            "preferences": {"workType": "Remote"},
        },
        headers=headers,
    )
    assert response.json()["skills"] == ["Python"]
    assert response.json()["preferences"]["preferredLocation"] == "Lahore"

def test_private_responses_are_not_cacheable(sign_in):
    candidate, _, _ = sign_in("Aya Khan")
    for path in ("/api/auth/session", "/api/candidates/me", "/api/jobs/workspace"):
        response = candidate.get(path)
        assert response.headers.get("cache-control") == "no-store"
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("referrer-policy") == "no-referrer"

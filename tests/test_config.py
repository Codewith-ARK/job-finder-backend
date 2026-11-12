from app.config import Settings, configuration_problems


def settings_with(**overrides) -> Settings:
    values = {
        "cors_origins": "http://localhost:3000",
        "docs_testing_enabled": False,
        "demo_login_enabled": False,
        "seed_on_startup": False,
        "cookie_secure": True,
        "session_days": 7,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_clean_configuration_has_no_problems():
    assert configuration_problems(settings_with()) == []


def test_unsafe_configuration_is_reported():
    problems = configuration_problems(
        settings_with(
            cors_origins=(
                " http://localhost:3000/ , *, http://localhost:3000, "
                "http://localhost:3000 ,"
            ),
            docs_testing_enabled=True,
            demo_login_enabled=True,
            seed_on_startup=True,
            cookie_secure=False,
            session_days=90,
        )
    )
    levels = {level for level, _message in problems}
    assert "error" in levels
    messages = " ".join(message for _level, message in problems)
    for fragment in (
        "surrounding whitespace",
        "ends with '/'",
        "every site",
        "duplicated",
        "Swagger UI",
        "demo persona",
        "seeded at startup",
        "plain HTTP",
        "longer than 30 days",
    ):
        assert fragment in messages


def test_wildcard_and_empty_origins_are_reported():
    wildcard = configuration_problems(settings_with(cors_origins="*"))
    assert any(level == "error" for level, _message in wildcard)

    empty = configuration_problems(settings_with(cors_origins=" , "))
    messages = " ".join(message for _level, message in empty)
    assert "empty entry" in messages
    assert "CORS_ORIGINS is empty" in messages

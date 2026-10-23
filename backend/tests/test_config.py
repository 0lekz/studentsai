from app.config import Settings

RETIRED_SMTP_VARIABLES = {
    "MAIL_USERNAME": "someone@example.com",
    "MAIL_PASSWORD": "app-password",
    "MAIL_SERVER": "smtp.example.com",
    "MAIL_PORT": "587",
    "MAIL_TLS": "True",
    "MAIL_SSL": "False",
    "MAIL_TIMEOUT": "120",
}


def test_retired_and_unknown_variables_in_an_env_file_are_ignored(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("MAIL_FROM", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "".join(f"{name}={value}\n" for name, value in RETIRED_SMTP_VARIABLES.items())
        + "NOT_A_SETTING=x\n"
        + "MAIL_FROM=study@example.com\n"
    )

    settings = Settings(_env_file=env_file)

    assert settings.mail_from == "study@example.com"
    assert "mail_server" not in settings.model_dump()

from flightscout.config import _apply_env_notifiers


def test_regression(monkeypatch):
    smtp_variables = (
        "FLIGHTSCOUT_SMTP_HOST",
        "FLIGHTSCOUT_SMTP_PORT",
        "FLIGHTSCOUT_SMTP_USER",
        "FLIGHTSCOUT_SMTP_PASS",
        "FLIGHTSCOUT_SMTP_FROM",
        "FLIGHTSCOUT_SMTP_TO",
    )
    for variable in smtp_variables:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("FLIGHTSCOUT_SMTP_HOST", "override.smtp.example")

    notifiers = {
        "email": {
            "host": "smtp.example",
            "port": 465,
            "username": "alerts@example.com",
            "password": "secret",
            "from_addr": "fares@example.com",
            "to_addr": "traveler@example.com",
        }
    }

    _apply_env_notifiers(notifiers)

    assert notifiers["email"] == {
        "host": "override.smtp.example",
        "port": 465,
        "username": "alerts@example.com",
        "password": "secret",
        "from_addr": "fares@example.com",
        "to_addr": "traveler@example.com",
    }

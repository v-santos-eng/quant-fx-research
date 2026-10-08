from research.notify import _telegram_conf, telegram_send


def test_no_secrets_file(tmp_path):
    assert _telegram_conf(tmp_path / "nope.yaml") is None
    assert telegram_send("oi", secrets_path=tmp_path / "nope.yaml") == "not_configured"


def test_secrets_without_telegram_key(tmp_path):
    p = tmp_path / "secrets.yaml"
    p.write_text("mt5:\n  login: 1\n", encoding="utf-8")
    assert _telegram_conf(p) is None
    assert telegram_send("oi", secrets_path=p) == "not_configured"


def test_secrets_incomplete_telegram(tmp_path):
    p = tmp_path / "secrets.yaml"
    p.write_text("telegram:\n  token: abc\n", encoding="utf-8")  # falta chat_id
    assert _telegram_conf(p) is None


def test_secrets_complete_telegram_parsed(tmp_path):
    p = tmp_path / "secrets.yaml"
    p.write_text("telegram:\n  token: abc\n  chat_id: 123\n", encoding="utf-8")
    conf = _telegram_conf(p)
    assert conf == {"token": "abc", "chat_id": 123}

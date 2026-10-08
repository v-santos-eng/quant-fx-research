from research.attempt_registry import AttemptRegistry


def test_log_and_read(tmp_path):
    reg = AttemptRegistry(tmp_path / "attempts.db")
    assert reg.count() == 0
    aid = reg.log(
        phase="0.1", name="smoke", config_hash="abc",
        params={"x": 1}, result={"sharpe": 0.0}, notes="teste",
    )
    got = reg.get(aid)
    assert got is not None
    assert got.params == {"x": 1}
    assert got.result == {"sharpe": 0.0}
    assert got.phase == "0.1"
    assert reg.count() == 1


def test_persists_across_instances(tmp_path):
    db = tmp_path / "attempts.db"
    AttemptRegistry(db).log(phase="0.1", name="a", config_hash="h", params={}, result={})
    assert AttemptRegistry(db).count() == 1  # mesma db, nova instância -> auditoria persiste


def test_get_missing_returns_none(tmp_path):
    assert AttemptRegistry(tmp_path / "attempts.db").get(999) is None

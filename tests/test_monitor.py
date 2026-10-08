import json

from research.monitor import ProgressReporter


def _read_status(d):
    return json.loads((d / "status.json").read_text(encoding="utf-8"))


def _read_events(d):
    return [json.loads(x) for x in (d / "events.jsonl").read_text(encoding="utf-8").splitlines()]


def test_status_and_events_written(tmp_path):
    rep = ProgressReporter("t", phase="0.4", monitor_dir=tmp_path)
    rep.set_step("etapa X", total=10)
    rep.set_task("lendo", data_source="data/x", storage="data/bars")
    rep.advance(3, current_file="a.parquet")
    st = _read_status(tmp_path)
    assert st["step"] == "etapa X"
    assert st["total"] == 10 and st["done"] == 3 and st["remaining"] == 7
    assert st["data_source"] == "data/x" and st["storage"] == "data/bars"
    assert st["current_file"] == "a.parquet"
    ev = _read_events(tmp_path)
    assert ev[0]["msg"].startswith("run iniciado")
    assert any(e["msg"] == "etapa: etapa X" for e in ev)


def test_counters_and_retry(tmp_path):
    rep = ProgressReporter("t", monitor_dir=tmp_path)
    rep.log("ERROR", "falhou", file="b.parquet")
    rep.retry("tentando de novo", reason="ConnectionReset")
    st = _read_status(tmp_path)
    assert st["counters"]["errors"] == 1
    assert st["counters"]["retries"] == 1
    assert st["counters"]["warnings"] == 1  # retry loga WARNING
    ev = _read_events(tmp_path)
    assert any(e.get("reason") == "ConnectionReset" for e in ev)


def test_resources_sampled(tmp_path):
    rep = ProgressReporter("t", monitor_dir=tmp_path)
    rep.heartbeat()
    res = _read_status(tmp_path)["resources"]
    for k in ("cpu_pct", "ram_pct", "disk_pct", "net_down_kbps", "proc_rss_mb"):
        assert k in res


def test_finish_sets_state(tmp_path):
    rep = ProgressReporter("t", monitor_dir=tmp_path)
    rep.finish("done")
    assert _read_status(tmp_path)["state"] == "done"

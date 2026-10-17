"""The web UI's API (simargl.ui.server): stores, guards, setup."""
import json
import os

from simargl.ui import server


def _store(tmp_path):
    st = tmp_path / "proj" / ".simargl"
    (st / "default").mkdir(parents=True)
    (st / "default" / "meta.json").write_text(json.dumps({"dim": 8}), encoding="utf-8")   # no model_key: an old index
    return st


def test_stores_models_and_guards(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "HOME", tmp_path / "home")
    monkeypatch.setattr(server, "REGISTRY", tmp_path / "home" / "stores.json")
    monkeypatch.setattr(server, "_start", str(tmp_path))
    st = _store(tmp_path)
    c = server.create_app().test_client()
    stores = c.get("/api/stores").get_json()["stores"]
    assert [s["store"] for s in stores] == [os.path.abspath(st)]
    assert stores[0]["indexes"][0]["model_key"] == "bge-small"          # an index without model_key is the legacy model
    m = c.post("/api/models", json={}).get_json()
    assert m["default"].startswith("ollama://") and "bge-small" in m["local"]
    # never reads outside a store, never an index path with separators
    assert c.post("/api/search", json={"store": str(tmp_path), "project": "default", "query": "x"}).status_code == 400
    assert c.post("/api/status", json={"store": str(st), "project": "../x"}).status_code == 400
    assert c.get(f"/api/download?store={st}&project=nope").status_code == 400


def test_no_dataset_gathering_here(tmp_path, monkeypatch):
    """project.yaml and the ingest are mokosh's (mokosh ui): simargl's UI only reads indexes."""
    monkeypatch.setattr(server, "_start", str(tmp_path))
    c = server.create_app().test_client()
    for path in ("/api/init", "/api/mask_preview"):
        assert c.post(path, json={}).status_code == 404
    page = c.get("/").data.decode("utf-8")
    assert 'data-tab="init"' not in page and 'id="i-go"' not in page

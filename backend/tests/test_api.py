"""End-to-end flow against SQLite: users, workflow approval, branching project, archive."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

P = "/api/v1"


def login(client, email, password):
    r = client.post(f"{P}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def test_full_flow():
    with TestClient(app) as admin:
        login(admin, "admin@example.com", "admin12345")
        people = {}
        for name in ("alice", "bob", "carol"):
            c = TestClient(app)
            assert c.post(f"{P}/auth/register", json={"email": f"{name}@x.com", "name": name, "password": "password123"}).status_code == 201
            assert c.post(f"{P}/auth/login", json={"email": f"{name}@x.com", "password": "password123"}).status_code == 403  # pending
            people[name] = c
        pending = admin.get(f"{P}/users", params={"status": "pending"}).json()
        ids = {u["name"]: u["id"] for u in pending}
        for uid in ids.values():
            assert admin.post(f"{P}/users/{uid}/approve").status_code == 200
        for name, c in people.items():
            login(c, f"{name}@x.com", "password123")

        alice, bob, carol = people["alice"], people["bob"], people["carol"]
        wf = alice.post(f"{P}/workflows", json={"title": "Purchase request"}).json()
        graph = {
            "title": "Purchase request", "description": "",
            "steps": [
                {"key": "1", "name": "Request", "is_start": True, "fields": [
                    {"key": "title", "type": "text", "label": "Title", "required": True},
                    {"key": "amount", "type": "number", "label": "Amount", "required": True},
                    {"key": "kind", "type": "dropdown", "label": "Kind", "config": {"options": ["goods", "services"]}}]},
                {"key": "2A", "name": "Manager sign-off", "fields": [{"key": "note", "type": "textarea", "label": "Note"}]},
                {"key": "2B", "name": "Finance review", "fields": []},
                {"key": "3", "name": "Done", "is_terminal": True, "fields": []},
            ],
            "transitions": [
                {"from_key": "1", "to_key": "2B", "condition": {"all": [{"field": "amount", "op": "gt", "value": 1000}]}, "priority": 0},
                {"from_key": "1", "to_key": "2A", "is_default": True, "priority": 1},
                {"from_key": "2A", "to_key": "3"}, {"from_key": "2B", "to_key": "3"},
            ],
        }
        assert alice.put(f"{P}/workflows/{wf['id']}", json=graph).status_code == 200
        assert alice.post(f"{P}/workflows/{wf['id']}/submit").status_code == 200
        assert bob.post(f"{P}/workflows/{wf['id']}/approve").status_code == 403
        assert admin.post(f"{P}/workflows/{wf['id']}/approve").json()["status"] == "approved"

        def run(amount):
            body = {"workflow_id": wf["id"], "name": f"PR {amount}",
                    "assignments": {k: ids["bob"] for k in ("1", "2A", "2B", "3")},
                    "approvers": {"1": [ids["carol"]]}}
            project = alice.post(f"{P}/projects", json=body).json()
            task = bob.get(f"{P}/tasks/mine").json()[-1]
            r = bob.post(f"{P}/step-instances/{task['id']}/submit",
                         json={"values": {"title": "Laptops", "amount": amount, "kind": "goods"}})
            assert r.status_code == 200, r.text
            appr = carol.get(f"{P}/approvals/mine").json()[-1]
            assert carol.post(f"{P}/step-instances/{appr['id']}/decision", json={"decision": "approved"}).status_code == 200
            return alice.get(f"{P}/projects/{project['id']}").json()

        small, big = run(500), run(5000)
        assert [i["step_key"] for i in small["instances"]] == ["1", "2A"]
        assert [i["step_key"] for i in big["instances"]] == ["1", "2B"]

        # finish the big one -> completed -> archive
        for step in ("2B", "3"):
            task = [t for t in bob.get(f"{P}/tasks/mine").json() if t["project_id"] == big["id"]][0]
            assert bob.post(f"{P}/step-instances/{task['id']}/submit", json={"values": {}}).status_code == 200
        done = alice.get(f"{P}/projects/{big['id']}").json()
        assert done["status"] == "completed"
        assert alice.post(f"{P}/projects/{big['id']}/archive").json()["status"] == "archived"

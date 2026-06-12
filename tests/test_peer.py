from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from padawan.app import create_app
from padawan.peer import decode_invite_token
from padawan.settings import REPO_ROOT, Settings


def make_client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            state_dir=tmp_path,
            content_dir=REPO_ROOT / "content" / "courses",
            docs_dir=REPO_ROOT / "docs" / "wiki",
            turn_host="turn.local",
            turn_secret="turn-secret",  # noqa: S106 - test credential only
        )
    )
    return TestClient(app)


def test_peer_identity_is_stable_and_role_scoped(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        first = client.post("/peer/identity", json={"username": "Leia", "role": "padawan"})
        second = client.post("/peer/identity", json={"username": " Leia ", "role": "padawan"})
        jedi = client.post("/peer/identity", json={"username": "Leia", "role": "jedi"})

    assert first.status_code == 200
    assert first.json()["identity"]["peer_id"] == second.json()["identity"]["peer_id"]
    assert first.json()["identity"]["peer_id"] != jedi.json()["identity"]["peer_id"]
    assert first.json()["identity"]["username"] == "Leia"


def test_peer_session_token_and_join(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post(
            "/peer/sessions",
            json={"username": "Obi-Wan", "role": "jedi", "ice_profile": "local-turn"},
        )
        token = created.json()["token"]
        joined = client.post(
            "/peer/sessions/join",
            json={"token": token, "username": "Ahsoka", "role": "padawan"},
        )

    assert created.status_code == 200
    assert joined.status_code == 200
    decoded = decode_invite_token(token)
    assert decoded.session_id == created.json()["session"]["session_id"]
    assert joined.json()["session"]["participants"][1]["username"] == "Ahsoka"


def test_peer_ice_profiles(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        local = client.get("/peer/ice-config?profile=local-turn")
        google = client.get("/peer/ice-config?profile=google-stun")

    assert local.status_code == 200
    assert local.json()["ice_servers"][0]["urls"] == "stun:turn.local:3478"
    assert local.json()["ice_servers"][1]["credential"] == "turn-secret"
    assert google.json()["ice_servers"] == [{"urls": "stun:stun.l.google.com:19302"}]


def test_peer_websocket_relays_signaling(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post(
            "/peer/sessions",
            json={"username": "Obi-Wan", "role": "jedi", "ice_profile": "local-turn"},
        ).json()
        joined = client.post(
            "/peer/sessions/join",
            json={"token": created["token"], "username": "Ahsoka", "role": "padawan"},
        ).json()
        session_id = created["session"]["session_id"]
        jedi_id = created["identity"]["peer_id"]
        padawan_id = joined["identity"]["peer_id"]
        token = created["token"]

        with (
            client.websocket_connect(
                f"/peer/ws/{session_id}?token={token}&peer_id={jedi_id}"
            ) as jedi_ws,
            client.websocket_connect(
                f"/peer/ws/{session_id}?token={token}&peer_id={padawan_id}"
            ) as padawan_ws,
        ):
            joined_message = jedi_ws.receive_json()
            padawan_ws.send_json({"type": "chat", "text": "hello"})
            chat_message = jedi_ws.receive_json()

    assert joined_message["type"] == "peer-joined"
    assert joined_message["peer_id"] == padawan_id
    assert chat_message == {"sender_id": padawan_id, "type": "chat", "text": "hello"}

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import WebSocket
from pydantic import BaseModel, Field

PeerRole = Literal["padawan", "jedi"]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_username(username: str) -> str:
    cleaned = " ".join(username.strip().split())
    return cleaned[:48] or "Local User"


def peer_suffix(username: str, role: PeerRole, seed: str) -> str:
    normalized = normalize_username(username).casefold()
    digest = hashlib.sha256(f"{seed}:{role}:{normalized}".encode()).hexdigest()
    return digest[:8]


def peer_id(username: str, role: PeerRole, seed: str) -> str:
    stem = "".join(ch.lower() if ch.isalnum() else "-" for ch in normalize_username(username))
    stem = "-".join(part for part in stem.split("-") if part)[:32] or "user"
    return f"{stem}-{peer_suffix(username, role, seed)}"


class PeerIdentity(BaseModel):
    peer_id: str
    username: str
    role: PeerRole
    suffix: str


class PeerIdentityRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    role: PeerRole


class PeerSessionRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    role: PeerRole
    ice_profile: str = "local-turn"
    origin: str = ""
    ttl_seconds: int = Field(default=3600, ge=60, le=24 * 3600)


class PeerJoinRequest(BaseModel):
    token: str
    username: str = Field(min_length=1, max_length=80)
    role: PeerRole


class PeerInviteToken(BaseModel):
    version: str = "padsim1"
    session_id: str
    invite_secret: str
    issuer_role: PeerRole
    origin: str = ""
    ice_profile: str = "local-turn"
    expires_at: str

    @property
    def expired(self) -> bool:
        expires = datetime.fromisoformat(self.expires_at)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return datetime.now(UTC) >= expires


class PeerSessionPublic(BaseModel):
    session_id: str
    issuer_role: PeerRole
    ice_profile: str
    origin: str = ""
    expires_at: str
    participants: list[PeerIdentity] = Field(default_factory=list)


def encode_invite_token(token: PeerInviteToken) -> str:
    payload = token.model_dump_json().encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"padsim1.{encoded}"


def decode_invite_token(raw: str) -> PeerInviteToken:
    prefix, _, encoded = raw.partition(".")
    if prefix != "padsim1" or not encoded:
        raise ValueError("Unsupported peer invite token.")
    padded = encoded + ("=" * (-len(encoded) % 4))
    try:
        data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid peer invite token.") from exc
    token = PeerInviteToken.model_validate(data)
    if token.version != "padsim1":
        raise ValueError("Unsupported peer invite token.")
    if token.expired:
        raise ValueError("Peer invite token expired.")
    return token


@dataclass
class PeerSession:
    token: PeerInviteToken
    participants: dict[str, PeerIdentity] = field(default_factory=dict)
    sockets: dict[str, WebSocket] = field(default_factory=dict)

    def public(self) -> PeerSessionPublic:
        return PeerSessionPublic(
            session_id=self.token.session_id,
            issuer_role=self.token.issuer_role,
            ice_profile=self.token.ice_profile,
            origin=self.token.origin,
            expires_at=self.token.expires_at,
            participants=list(self.participants.values()),
        )


class PeerHub:
    def __init__(self) -> None:
        self._sessions: dict[str, PeerSession] = {}

    def create_session(
        self,
        *,
        issuer: PeerIdentity,
        ice_profile: str,
        origin: str,
        ttl_seconds: int,
    ) -> tuple[PeerSessionPublic, str]:
        expires = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        token = PeerInviteToken(
            session_id=secrets.token_urlsafe(12),
            invite_secret=secrets.token_urlsafe(24),
            issuer_role=issuer.role,
            origin=origin,
            ice_profile=ice_profile,
            expires_at=expires.isoformat(),
        )
        session = PeerSession(token=token, participants={issuer.peer_id: issuer})
        self._sessions[token.session_id] = session
        return session.public(), encode_invite_token(token)

    def join_session(self, token: PeerInviteToken, participant: PeerIdentity) -> PeerSessionPublic:
        session = self._sessions.get(token.session_id)
        if session is None:
            session = PeerSession(token=token)
            self._sessions[token.session_id] = session
        if not secrets.compare_digest(session.token.invite_secret, token.invite_secret):
            raise ValueError("Peer invite token does not match the active session.")
        session.participants[participant.peer_id] = participant
        return session.public()

    def validate(self, session_id: str, raw_token: str) -> PeerInviteToken:
        token = decode_invite_token(raw_token)
        if token.session_id != session_id:
            raise ValueError("Peer invite token does not match the session.")
        session = self._sessions.get(session_id)
        if session and not secrets.compare_digest(session.token.invite_secret, token.invite_secret):
            raise ValueError("Peer invite token does not match the active session.")
        return token

    async def connect(self, session_id: str, peer_id_value: str, websocket: WebSocket) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Peer session not found.")
        if peer_id_value not in session.participants:
            raise ValueError("Peer identity has not joined this session.")
        await websocket.accept()
        session.sockets[peer_id_value] = websocket
        await self.broadcast(
            session_id,
            peer_id_value,
            {
                "type": "peer-joined",
                "peer_id": peer_id_value,
                "participants": [item.model_dump() for item in session.participants.values()],
            },
        )

    def disconnect(self, session_id: str, peer_id_value: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.sockets.pop(peer_id_value, None)

    async def broadcast(self, session_id: str, sender_id: str, payload: dict[str, Any]) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        message = {"sender_id": sender_id, **payload}
        stale: list[str] = []
        for peer_id_value, socket in session.sockets.items():
            if peer_id_value == sender_id:
                continue
            try:
                await socket.send_json(message)
            except RuntimeError:
                stale.append(peer_id_value)
        for peer_id_value in stale:
            session.sockets.pop(peer_id_value, None)


def ice_servers_for_profile(
    profile: str, *, turn_host: str = "", turn_secret: str = ""
) -> list[dict[str, Any]]:
    if profile == "google-stun":
        return [{"urls": "stun:stun.l.google.com:19302"}]
    if profile == "local-turn":
        host = turn_host or "127.0.0.1"
        servers: list[dict[str, Any]] = [{"urls": f"stun:{host}:3478"}]
        if turn_secret:
            servers.append(
                {
                    "urls": [f"turn:{host}:3478?transport=udp", f"turn:{host}:3478?transport=tcp"],
                    "username": "padawan",
                    "credential": turn_secret,
                }
            )
        return servers
    return []

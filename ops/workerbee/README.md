# Padawan WorkerBee Stage

The peer validation stage uses two native k1s workloads:

- `padawan.k1s.yaml`: FastAPI/Jinja app
- `coturn.k1s.yaml`: local STUN/TURN service for WebRTC tests

`PADAWAN_TURN_HOST` must be a host the browser can resolve. The local
WorkerBee stage uses `app.padawan.workerbee.home.arpa` with coturn published on
port 3478. Remote k1s-dev-a runs should override it with an externally
reachable node, load balancer, or DNS name for the deployed TURN endpoint.

Expected WorkerBee loop:

```bash
workerbee_v1_session_start(cwd="/home/m4xx3d0ut/git/k1s-wt/padawan", goal="validate peer flow")
workerbee_v1_image_build(context=".", dockerfile="Containerfile", tag="localhost/padawan:dev")
workerbee_v1_manifest_validate(stage="ops/workerbee")
workerbee_v1_manifest_deploy_local(stage="ops/workerbee")
workerbee_v1_ingress_probe(host="app.padawan.workerbee.home.arpa", path="/healthz")
workerbee_v1_ingress_probe(host="app.padawan.workerbee.home.arpa", path="/peer")
workerbee_v1_security_review_project(stage="ops/workerbee")
```

The committed TURN credential is a local development credential only. Simulation
runs that need sensitive credentials should inject them through `.local/` or the
runtime environment and must not write them to git.

For the non-WorkerBee track, `scripts/compose-peer-up` selects an available
Compose engine automatically. Set `PADAWAN_COMPOSE_ENGINE` to force one, for
example `PADAWAN_COMPOSE_ENGINE="docker compose" scripts/compose-peer-up`.

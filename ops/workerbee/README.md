# Padawan WorkerBee Stage

The peer validation stage uses two native k1s workloads:

- `padawan.k1s.yaml`: FastAPI/Jinja app
- `coturn.k1s.yaml`: local STUN/TURN service for WebRTC tests, using the
  fully qualified `docker.io/coturn/coturn:4.12.0` image so Podman does not
  need short-name registry aliases

`PADAWAN_TURN_HOST` must be a host the browser can resolve. The committed
manifest uses the neutral local default `app.padawan.workerbee.localhost`.
Measured simulation runs must rewrite the staged manifest to the active
WorkerBee project host before deployment, for example
`app.simcal2.workerbee.localhost`, so Caddy route ownership and TURN host values
do not collide with another WorkerBee project. Remote k1s-dev-a runs should
override it with an externally reachable node, load balancer, or DNS name for
the deployed TURN endpoint.

The local WorkerBee manifests intentionally omit `metadata.namespace` because
the project-local Podman-backed k1s path expects simple app identities for
status, logs, and ingress route generation. Pass a namespace at remote deploy
time when targeting k1s-dev-a.

The coturn container intentionally does not drop all Linux capabilities in this
local stage because the upstream image entrypoint will not execute under
Podman's fully dropped capability bounding set.

Expected direct-containerd WorkerBee simulation loop:

```bash
cd /home/m4xx3d0ut/git/k1s-wt/k1s-workerbee
WORKERBEE_REFRESH_SUDO=0 scripts/dev/wb-containerd --project simcal2 profile start \
  --profile k1s-dev-min-sqlite --k1s-root ../k1s
WORKERBEE_REFRESH_SUDO=0 scripts/dev/wb-containerd --project simcal2 build-image \
  --tag localhost/padawan:dev -f Containerfile /home/m4xx3d0ut/git/k1s-wt/padawan
WORKERBEE_REFRESH_SUDO=0 scripts/dev/wb-containerd --project simcal2 manifest prepare \
  --name padawan-peer --source /home/m4xx3d0ut/git/k1s-wt/padawan/ops/workerbee
cd /home/m4xx3d0ut/git/k1s-wt/simulacra-and-simulation
simctl patch-workerbee-stage --project simcal2 --stage-dir <returned stage_dir>
cd /home/m4xx3d0ut/git/k1s-wt/k1s-workerbee
WORKERBEE_REFRESH_SUDO=0 scripts/dev/wb-containerd --project simcal2 manifest validate \
  --stage <returned stage_dir>
WORKERBEE_REFRESH_SUDO=0 scripts/dev/wb-containerd --project simcal2 manifest deploy-local \
  --stage <returned stage_dir> --target profile --profile k1s-dev-min-sqlite --k1s-root ../k1s
```

If this WorkerBee runtime applies the workloads but does not materialize an app
Caddy route, validate the local service ports directly:

```bash
python3 - <<'PY'
import urllib.request

for path in ["/healthz", "/peer", "/peer/ice-config?profile=local-turn"]:
    with urllib.request.urlopen("http://127.0.0.1:8787" + path, timeout=5) as resp:
        print(path, resp.status)
PY
```

The committed TURN credential is a local development credential only. Simulation
runs that need sensitive credentials should inject them through `.local/` or the
runtime environment and must not write them to git.

For the non-WorkerBee track, `scripts/compose-peer-up` selects an available
Compose engine automatically. Set `PADAWAN_COMPOSE_ENGINE` to force one, for
example `PADAWAN_COMPOSE_ENGINE="docker compose" scripts/compose-peer-up`.

# Agent Guidance

This repo builds a local educational coding app. Prefer small, tested changes.

When work involves containers, services, manifests, ingress, runtime validation, or
security review, use WorkerBee MCP:

1. Call `workerbee_v1_session_start(cwd=<absolute repo cwd>, goal=<task>)`.
2. Use the returned project for image builds, manifest prepare/validate/deploy, status,
   logs, ingress probes, security review, and exports.
3. Do not stop at project start when deployable manifests exist; build, deploy, probe,
   inspect, and repair from evidence.

For local validation, run:

```bash
ruff format --check
ruff check
pytest
padawan course validate --course all-seed
```

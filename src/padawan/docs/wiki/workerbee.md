# WorkerBee Validation

WorkerBee is optional for novice seed-course use, but it is the validation
workbench for deployable app checks and publishable generated courses.

Use WorkerBee when you want evidence that Padawan works as a packaged local web
app, not just as a Python process from the repo.

## What WorkerBee Checks

WorkerBee can build or run the container image, apply the native k1s manifest,
probe the HTTPS ingress, inspect logs, run commands inside the app container,
and produce an advisory security report.

## User-Visible Status

Padawan now exposes draft validation status on the Drafts page. Users can see
whether a generated course is `queued`, `running`, `passed`, or `failed`.

The current MVP performs web-triggered validation locally inside Padawan.
WorkerBee validation is run by the operator through WorkerBee tools, then
recorded as validation evidence in the QA/UAT notes. A future runner can attach
to the same status surface so users see WorkerBee progress without leaving the
app.

## Validation Flow

1. Start a WorkerBee session for this repo.
2. Build the Padawan image.
3. Prepare, validate, and deploy the manifest.
4. Probe `/healthz`, `/`, `/courses`, `/docs`, and a seed lesson.
5. Confirm the retained `/data/padawan` state volume is mounted.
6. Export and import a backup from `/data`.
7. Validate a generated draft, publish it, and confirm it appears in `/courses`.
8. Run the security review.
9. Export k1s, Kubernetes, and Helm artifacts.

## Current App Route

The local WorkerBee route is:

```text
https://app.padawan.workerbee.home.arpa:19443/
```

If DNS is not available from the browser, use WorkerBee's ingress probe or
install/trust the WorkerBee local CA and DNS guidance for the host.

## Troubleshooting WorkerBee Runs

- Image build fails with a Podman or crun transport error: check whether the
  root Podman build path works and retag `localhost/padawan:dev`.
- Probe reaches the dashboard instead of Padawan: set the probe host to
  `app.padawan.workerbee.home.arpa`.
- Runtime lessons fail in WorkerBee but pass locally: exec into the app
  container and check `python`, `git`, `bash`, and `node` availability.
- Backup export fails: confirm `/data/padawan` is mounted and writable.
- Security review reports advisory findings: compare the finding with manifest
  and runtime evidence before changing behavior.

## What To Record For UAT

Capture:

- deployment revision
- app URL
- image ID
- probe results
- course validation result
- backup export result
- security review summary
- known residual findings

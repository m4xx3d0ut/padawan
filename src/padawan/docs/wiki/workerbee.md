# WorkerBee Validation

WorkerBee is optional for novice seed-course use, but it is the validation
workbench for deployable app checks and publishable generated courses.

Validation flow:

1. Start a WorkerBee session for this repo.
2. Build the Padawan image.
3. Prepare, validate, and deploy the manifest.
4. Probe `/healthz`, `/`, `/courses`, `/docs`, and a seed lesson.
5. Confirm the retained `/data/padawan` state volume is mounted.
6. Export and import a backup from `/data`.
7. Validate a generated draft, publish it, and confirm it appears in `/courses`.
8. Run the security review.
9. Export k1s, Kubernetes, and Helm artifacts.

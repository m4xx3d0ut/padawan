# Troubleshooting

Start with the exact command or page that failed. Then use the matching section
below.

## The App Does Not Start

Run:

```bash
padawan doctor
```

Common causes:

- Python is older than 3.11.
- The virtual environment is not activated.
- Dependencies were not installed with `python -m pip install -e .[dev]`.
- Another process is already using port `8787`.

Use a different port:

```bash
PADAWAN_PORT=8790 padawan serve
```

## The Browser Cannot Open Padawan

Check that the terminal running `padawan serve` is still open. The local URL is:

```text
http://127.0.0.1:8787/
```

If you changed `PADAWAN_PORT`, use that port in the browser.

## A Lesson Runtime Is Missing

Run:

```bash
padawan doctor
```

Install the missing runtime:

- Python lessons need Python.
- Bash lessons need Bash.
- Git lessons need Git and Bash.
- WebDev TS/React lessons need Node.js.
- Text lessons do not need an external runtime.

On Windows, Bash lessons usually require Git Bash or WSL.

## A Lesson Fails

Read the transcript first. Look for:

- expected output text
- exit code
- timeout message
- syntax error
- missing command

Then try the smallest change that could satisfy the prompt. Reveal the hint if
you are stuck.

## Codex Is Unavailable

Run:

```bash
codex login
padawan codex status
```

Padawan does not manage Codex credentials. If login fails, fix Codex in a normal
terminal first, then restart Padawan.

## A Generated Course Will Not Publish

Generated courses must pass validation before publishing. Use:

```bash
padawan course draft validate <course-id> --json
```

Common causes:

- unsupported runtime
- invalid badge metadata
- missing reference solution
- reference solution does not pass
- course ID conflicts with an existing course

Reject the draft if it is not worth repairing.

If the Drafts page stays on `queued` or `running`, refresh the page and check
the latest status. If it still does not finish, run the CLI validation command
above to see the raw error.

## Backup Import Fails

Inspect the archive:

```bash
padawan data inspect padawan-backup.zip
padawan data import padawan-backup.zip --dry-run
```

Padawan skips local course files that conflict with bundled seed courses. That
is expected.

## WorkerBee Looks Healthy But The App Probe Is Wrong

Make sure the probe targets the Padawan app host:

```text
app.padawan.workerbee.home.arpa
```

If the probe reaches the WorkerBee dashboard, the host was not set correctly.

## Still Stuck

Capture:

- operating system
- command or URL
- full error text
- `padawan doctor` output
- whether the issue happens in a bundled course or generated course

That information is usually enough to reproduce the problem.

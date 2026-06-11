# Runtime Safety

Lessons run in temporary local workspaces with timeouts, output caps, and a
scrubbed environment. The shell is not an unrestricted terminal. It executes the
current lesson code and returns a transcript.

## What This Means

Padawan tries to make lesson execution predictable, not magical. It creates a
fresh temporary directory, writes the learner's code to a file, runs the selected
runtime, captures stdout and stderr, grades the result, and removes the
temporary workspace.

The lesson runtime still runs on your computer. Only run courses you trust, and
review generated drafts before publishing them.

Bash lessons on Windows require Git Bash or WSL.

## Runtime Support

- `python` runs a temporary Python script.
- `bash` runs a temporary Bash script.
- `git` runs a Bash script inside a temporary Git workspace.
- `node` runs a temporary `.mjs` script with Node.js.
- `text` grades the learner's written answer.
- `none` acknowledges read-only conceptual lessons.

## Safety Controls

Padawan applies:

- temporary workspaces
- runtime timeouts
- output length limits
- a limited environment variable allowlist
- local grading rules
- hidden reference solutions for validation

These controls reduce accidental damage and noisy output. They are not a full
security sandbox for untrusted code.

## Practical Advice

- Start with bundled courses.
- Validate generated courses before publishing them.
- Avoid writing lessons that access personal files or network services.
- Keep destructive shell commands out of lesson prompts and reference solutions.
- Use backup/restore before broad UAT or course import testing.

## Runtime Troubleshooting

- Python lesson unavailable: confirm `python3` or `python` is on `PATH`.
- Bash lesson unavailable on Windows: install Git Bash or use WSL.
- Git lesson fails on identity: Padawan seed lessons configure local test Git
  identity inside the temporary workspace where needed.
- Node lesson unavailable: install Node.js or use the WorkerBee container image.
- Lesson times out: simplify the code and avoid infinite loops.

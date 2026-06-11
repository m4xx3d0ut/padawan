# Runtime Safety

Lessons run in temporary local workspaces with timeouts, output caps, and a
scrubbed environment. The shell is not an unrestricted terminal. It executes the
current lesson code and returns a transcript.

Bash lessons on Windows require Git Bash or WSL.

Runtime support:

- `python` runs a temporary Python script.
- `bash` runs a temporary Bash script.
- `git` runs a Bash script inside a temporary Git workspace.
- `node` runs a temporary `.mjs` script with Node.js.
- `text` grades the learner's written answer.
- `none` acknowledges read-only conceptual lessons.

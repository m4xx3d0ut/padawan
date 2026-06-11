# First Steps

This page is for anyone opening Padawan for the first time.

Padawan runs on your own computer. It does not upload learner progress,
exercise code, backups, or badges to a cloud service. Codex features are
optional and use the Codex CLI that you install and sign in to separately.

## What The App Shows

The landing page asks:

`What programming language or skills would you like to learn today?`

Below that prompt, Padawan shows available courses. Courses with recent scored
work appear first. Each card shows:

- the course title
- the track and level
- completion progress
- local badge status
- a link to open the course

## Take A Bundled Course

For a first run, use a bundled course instead of generating a new one.

1. Open `http://127.0.0.1:8787/`.
2. Choose a basic course such as Python Basics, Git CLI Basics, or Linux/Bash
   Basics.
3. Open the first lesson.
4. Read the teaching pane on the left.
5. Edit the starter code on the right.
6. Run the lesson.
7. If the result fails, read the message and try again.
8. Reveal the hidden hint only when you are stuck.

## Understanding Results

A passed result means the lesson's local grading rules succeeded. A failed
result usually means the code ran, but the output or behavior did not match the
lesson. An error means the runtime could not complete the command, timed out, or
could not start.

You do not need to finish a course in one sitting. Padawan records progress in
the local state directory and updates the course card when you return.

## Ask Codex

If Codex is installed and signed in, lesson pages can ask Codex for an
explanation. Use this when you want help understanding the idea, not just the
answer. Padawan stores only lightweight thread metadata so the same explanation
can continue later.

## Back Up Before Experimenting

Before importing data, generating many courses, or doing UAT, create a backup:

```bash
padawan data export --output padawan-backup.zip
padawan data inspect padawan-backup.zip
```

You can also use the Data page in the web UI.

## Draft Validation Status

Generated courses appear on the Drafts page first. A draft can show:

- `queued`: validation is waiting to start
- `running`: validation is in progress
- `passed`: the draft can be published
- `failed`: the draft needs review or should be rejected

Published courses move from Drafts into the main course list.

## Where To Go Next

- Install Padawan: setup commands for Linux, macOS, and Windows.
- Runtime Safety: what local lesson execution can and cannot do.
- Data Backup And Restore: how to protect local progress.
- Troubleshooting: common install, runtime, Codex, and WorkerBee issues.

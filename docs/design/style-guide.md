# Padawan Visual Style Guide

Padawan uses a k1s/WorkerBee-derived interface system. The source references are
`../k1s/docs/reference/style-guide.md`, the k1s docs lab CSS, and the WorkerBee
demo app.

## Tokens

- Page background: `#0f172a`
- Surface: `#111827`
- Panel: `#1f2937`
- Border: `#334155` and `#8884`
- Text: `#e5e7eb`
- Muted text: `#9ca3af`
- Primary action: `#2563eb`
- Highlight: `#60a5fa`
- Badge accent: `#fbc02d`
- Success: `#16a34a`
- Warning: `#f59e0b`
- Danger: `#ef4444`

## Type

Use `system-ui, -apple-system, "Segoe UI", "Roboto", sans-serif` for the app.
Use `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` for editors,
code, command examples, and runtime transcripts.

## Backgrounds

The default background is a dark slate overlay on the packaged WorkerBee/k1s
background image. The app must not depend on sibling repo asset paths at runtime.

## Component Rules

- Cards and panels use 8px radius, 1px soft border, and dense spacing.
- Blue is reserved for actions and focus.
- Gold is reserved for badges and achievements.
- Success, warning, and danger colors are only for runtime, validation, and
  progress states.
- Text must wrap inside cards, buttons, terminal panes, and lesson navigation.

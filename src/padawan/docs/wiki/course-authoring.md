# Course Authoring

Seed courses are JSON files under `content/courses`. Local user courses live in
the Padawan state directory under `courses/`, and generated drafts live under
`course-drafts/`.

Each course contains modules, lessons, grading rules, optional badges, and hidden
validation metadata. Every publishable lesson should include a `reference_solution`
that passes local validation.

Supported tracks are:

- `linux-bash`
- `git`
- `python`
- `webdev-ts-react`
- `webdev-python-htmx`
- `k1s-workerbee`
- `roblox`
- `unity`
- `unreal`

Supported runtimes are `python`, `bash`, `git`, `node`, `text`, and `none`.
Roblox, Unity, and Unreal lessons use `text` validation until engine adapters are
available.

Generated courses stay hidden until schema validation, badge checks, and reference
solution checks pass. Use the web Drafts page or the CLI:

Run:

```bash
padawan course validate --course all-seed
padawan course draft list
padawan course draft validate <course-id> --json
padawan course draft publish <course-id>
padawan course draft reject <course-id>
```

Create one Padawan course JSON object using schema_version `padawan.training-data.v1`.

Audience: a newcomer using a local coding teacher. Keep lessons small, practical,
and kind without being vague.

Use only these tracks:
- linux-bash
- git
- python
- webdev-ts-react
- webdev-python-htmx
- k1s-workerbee
- roblox
- unity
- unreal

Use only these levels:
- basic
- intermediate
- advanced

Use only these runtimes:
- python
- bash
- git
- node
- text
- none

Course requirements:
- Include id, title, track, level, summary, schema_version, content_version,
  author, maintainers, license, tags, prerequisites, learning_objectives,
  target_audience, estimated_minutes, provenance, share, created_at, updated_at,
  modules, badges, generated, and verified.
- Set generated to true and verified to false.
- Use content_version `0.1.0` unless the user asks for a specific version.
- Use a local share visibility unless the user asks for public sharing metadata.
- Include at least one module and at least two lessons.
- Include 50 percent and 100 percent completion badges with stable IDs.

Lesson requirements:
- Include concept_md, concept_summary, concept_links, examples, prompt,
  starter_code, language, runtime, hidden_hint, grading, codex_context,
  reference_solution, toolchain, and exercises.
- concept_summary must be two to four novice-friendly sentences.
- concept_links must point to relevant official project documentation where possible.
- examples must include at least one worked example with title, explanation, code
  or text, expected output when useful, and docs links when relevant.
- exercises must include at least one follow-up practice item with a prompt, hint,
  reference solution, and grading rules when runnable.
- Reference solutions must pass the grading rules for runnable lessons.
- Avoid broad survey lessons. Each lesson should teach one concept and ask for one
  concrete action.

User request:
{{USER_REQUEST}}

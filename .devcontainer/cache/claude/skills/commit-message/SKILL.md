---
name: eric-git-commits
description: Use when the user wants a git commit message drafted or refined in Eric Regina's preferred style. This skill inspects the current git changes, prefers a concise conventional-commit subject when the change type is clear, and for larger changes writes a structured body with a short summary paragraph followed by `Key changes:` and `Why:` sections.
---

# Eric Git Commits

## Overview

Use this skill when the task is to write, rewrite, or polish a git commit message in Eric's house style.

The style in the provided `commits` examples has two common modes:

- Small changes: a short subject, often `fix:` or another conventional-commit prefix when obvious.
- Larger changes: a conventional-commit subject plus a body with this structure:
  1. A short `This change ...` summary paragraph.
  2. `Key changes:` with concrete bullets.
  3. `Why:` with motivation bullets.

## Workflow

1. Inspect the actual change before drafting anything.
   Run `git status --short`, `git diff --stat`, and `git diff --cached --stat`.
   If the staged diff is empty, inspect `git diff` and note that the message is based on unstaged work.

2. Ground the message in the diff, not in guesses.
   Mention only changes that are visible in the working tree, staged diff, or user-provided context.

3. Choose the subject style.
   Prefer a lowercase conventional-commit subject when the category is clear:
   `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

4. Match the size of the body to the size of the change.
   For broad or multi-area changes, include the full body.
   For very small changes, a subject-only commit or a short body is acceptable.

## Subject Rules

- Keep the subject concise and specific.
- Use imperative phrasing such as `add`, `fix`, `refresh`, `reduce`, `update`.
- Avoid ending the subject with a period.
- Prefer one main theme; do not enumerate every file in the subject.

## Body Template

Use this template for substantial commits:

```text
<type>: <short subject>

This change <high-level summary of what changed across the diff>.

Key changes:
- <concrete change 1>
- <concrete change 2>
- <concrete change 3>

Why:
- <reason 1>
- <reason 2>
```

## Writing Guidance

- Start the summary paragraph with `This change ...` when writing a full body.
- Keep `Key changes:` factual and implementation-oriented.
- Keep `Why:` focused on outcomes, developer ergonomics, reliability, reproducibility, or user impact.
- If the motivation is obvious and the change is tiny, omit the body instead of padding it.
- If a change spans backend, frontend, tooling, and docs, group bullets by the most important outcomes rather than by file path.
- Mirror Eric's examples: practical, explanatory, and not overly formal.

## Validation

Before finalizing the message, check:

- The subject matches the dominant change.
- Every bullet is supported by the diff.
- The `Why:` section does not claim benefits that are not evidenced by the change.
- The message is shorter for small changes and more structured for large ones.

## Example Output

```text
feat: add cached evaluation endpoint for infer intent

This change adds a persisted post-game Infer Intent evaluation flow and returns cached results on later requests.

Key changes:
- add an endpoint that reconstructs completed sessions and computes evaluation results once
- persist the raw evaluation as an internal session event for later reuse
- extend tests to cover generation, caching, and free-play behavior

Why:
- make evaluations reproducible and available after session completion
- keep evaluation data tied to persisted session history instead of transient runtime state
```

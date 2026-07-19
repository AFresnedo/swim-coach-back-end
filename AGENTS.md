# SwimCoach back-end

## FastAPI docs

Before writing or reviewing FastAPI code (path operations, dependencies, streaming, responses, Pydantic integration), check the version-pinned docs shipped inside this project's virtualenv rather than relying on training data, which may be stale or describe a different version:

`.venv/lib/python*/site-packages/fastapi/.agents/skills/fastapi/SKILL.md`

and its `references/` subfolder. These match the exact FastAPI version installed (see `pyproject.toml` / `uv.lock`), which training knowledge cannot guarantee.

## Code review requires explicit permission

Never run the `/code-review` skill, or spawn code-review subagents/finder-angle agents, unless the user explicitly asks for it in that specific turn — not proactively, even right after implementing a nontrivial feature or fixing a bug. Manual verification (running tests, exercising the endpoint, checking types/lint) is expected and different from this; this rule is specifically about launching the `/code-review` skill or equivalent multi-agent review flows without being asked.

## Comments must stand alone

A comment must stand on its own. Never write a comment that points to another file or line to carry part of its meaning (e.g. "see app/models.py:User.token_valid_after for why") — inline the actual reasoning at the comment site instead. If the same rationale is genuinely needed in multiple places, repeat the relevant sentence rather than cross-referencing; don't make one comment's correctness depend on another file staying put.

## Local skill trigger (personal — only this contributor has this skill installed)

This contributor has a user-level Claude Code skill, `options-before-precedent` (`~/.claude/skills/options-before-precedent/SKILL.md`), covering how to compare and present multi-option technical decisions (precedent only ever expands the option space, never narrows it; reach for the field's established idiom, not just whatever satisfies the literal ask). It only fires if invoked — before presenting any design/schema/library/pattern choice with more than one viable approach, invoke it explicitly rather than relying on recalling its contents from memory. A contributor without this skill installed can ignore this section.

## Serious engineering effort

This is a serious, deliberate engineering effort, not a move-fast-and-skip-review project. Default to more discussion and more review passes, not less — even when nothing has gone wrong yet. Don't treat thoroughness as overhead to minimize; surface ambiguous calls for discussion rather than quietly resolving them solo.

## Clean code, not just correct code

Code that works correctly can still have a genuine, articulable maintainability problem — mixed concerns, domain-specific logic sitting in a general-purpose file, a missing single-responsibility split — that will bite the next person who builds on it. When asked to assess whether code is good or where something belongs, "it's correct" is not the same bar as "it's clean" — a real maintainability issue deserves to be named, not waved off because nothing is currently broken.

## Module organization

Module organization here is driven by conceptual unit, not caller count. `app/rag/`'s one-file-per-pipeline-step layout (`query.py`, `embeddings.py`, `retrieval.py`, `answer.py`, `sharpen.py`, `sharpen_flag.py`, `training.py`) is deliberate: each step has exactly one caller today, and that's fine — the split exists because each step is an independently-readable, independently-testable unit of the design, not because it's reused. "This only has one caller" is not a reason to inline something back into its caller if it represents a real conceptual unit; reserve colocation for genuinely incidental glue code with no identity of its own. For actual duplicated logic/constants (the same snippet copy-pasted, not a designed step), extract to a shared location once a real second duplicate appears — but use judgment rather than treating that as an automatic trigger: two superficially similar cases can be coincidentally similar rather than truly the same concept, and forcing a shared abstraction from only two data points is a common way to guess the wrong interface.

## Opinionated workflow preference (personal — delete if you don't agree)

This section reflects one contributor's local working setup, not a team convention. Remove it if it doesn't match your own layout or preferences.

You are an expert back-end programmer who specializes in Python, FastAPI, and SQLAlchemy. The front-end for this project lives at `../swim-coach` and shared infrastructure/deploy config lives at `../infra` — both are sibling checkouts on this machine. You can read, discover, and explore those sister folders, and you may edit `../infra` when a task calls for it (e.g. docker-compose, deploy config). Default to not editing `../swim-coach` — treat it as read-only unless explicitly asked in the conversation to change something there.

If `../swim-coach` or `../infra` aren't present (e.g. a fresh clone, an isolated worktree, or a cloud review run), ignore this section rather than trying to locate them.

This contributor drives git themselves and wants Claude read-only on it. Claude may run read-only git commands (`git status`, `git log`, `git diff`, `git branch --show-current`, etc.) freely to inspect repo state, but must never run any git command that changes state — no `checkout`, `branch`, `commit`, `stash`, `merge`, `push`, `reset`, `restore`, etc. Those are always this contributor's to run; Claude should describe what command to run and let them run it. Git state can change outside of any Claude tool call at any point in the session, so before asserting any fact about current repo state (which files are uncommitted, current branch, commit history, whether something merged) as the basis for advice, always run a read-only git command fresh in that same turn — never rely on git output from earlier in the conversation, no matter how recently it was checked.

When a fix doesn't verify the way expected (a test still fails, output is still wrong after a plausible-looking change), do at most one focused follow-up check. If that doesn't resolve it, stop — report what you found plus your best hypothesis, and ask how to proceed, rather than chaining more speculative debug attempts on your own.

This contributor wants direct, immediate answers, not softened ones. When asked to assess something ("is this good," "does this look right"), give the honest assessment right away — don't default to "fine as is" and wait to be argued into a truth you already reached. Also: when you notice a real observation on your own (a mismatch between stated intent and mechanism, a risk, a better option), keep surfacing it even if this contributor is obviously already aware — "they already know" is not a reason to stay quiet with them specifically.

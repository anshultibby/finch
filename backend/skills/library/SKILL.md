---
name: library
description: "Organize and navigate your notes the way a research desk does: one file per subject, dated entries in dated files, one file per task. Provides index/outline/read/find so you can locate material without pulling it into context — read the index, then one section, never a whole corpus."
metadata:
  emoji: "🗂️"
  category: memory
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Library

Your memory is a filing system, not a scroll. Every run starts fresh, so what
you can find later is what you filed well — and what you *read* is what you pay
for, repeatedly: a document you pull in early is re-sent to the model on every
later step of that run, so a 40K-token file read once is charged dozens of
times.

The fix is not to write less. It's to file things so you can retrieve a
paragraph instead of a corpus.

```python
from skills.library.scripts.notes import (index, outline, read, find,
                                          log, write_section, tasks, latest)
```

## Read in three moves

Never open a document blind. Go index → outline → section:

| Move | Call | Costs |
|---|---|---|
| What exists at all? | `index()` | ~1 token/doc, and tells you each doc's size |
| What's in this one? | `outline("stocks/NVDA/thesis.md")` | ~50 tokens |
| Give me the part I need | `read("stocks/NVDA/thesis.md", "Invalidation")` | the section only |
| Who mentions X? | `find("dilution")` | locations, not content |

`index()` reports a `tokens` count per document precisely so you can decide
what you can afford before you fetch. `find()` returns `{path, heading, line,
snippet}` — hits, not documents; read the one hit that matters.

Reading a whole file is a deliberate act, not a default. If you catch yourself
about to, ask which section you actually wanted.

## Where things go

File by **what changes it**, not what it's about. That question has exactly one
answer per fact, which is what makes filing unambiguous.

| Kind | Changes when | Goes in |
|---|---|---|
| A view on a company | news, earnings, your thesis shifts | `stocks/{SYMBOL}/thesis.md` |
| A piece of work in flight | you make progress on it | `tasks/{slug}.md`, one per task |
| A rule you operate by | you learn a lesson | `playbooks/{name}.md` |
| What happened today | every run | `journal/{YYYY-MM}.md`, `##` per entry |
| Who the user is | rarely | `preferences.md`, `user_model.md` |

Rules that follow:

1. **Anything ticker-specific goes in `stocks/{SYMBOL}/`** — write it with
   `write_chat_file("stocks/NVDA/thesis.md", ...)`, which syncs it to that
   stock's Analysis tab where the user can actually see it. A thesis buried in
   a diary is invisible and unfindable. This is the one hard rule.
2. **One subject per file.** Splitting is free; a file per company and a file
   per task cost nothing extra to store and are far cheaper to read than one
   file holding everything.
3. **Dated files, not rotated files.** `journal/2026-08.md` bounds itself — next
   month is a new file. Never build archiving or trimming machinery; that's the
   filing system doing what a filing system is for.
4. **Headings are the interface.** `read(path, heading=...)` only works if you
   wrote headings. A 5,000-line file with no headings can't be navigated by
   anything, including you.
5. **Write sections, not appends.** `write_section(path, "Thesis", ...)` updates
   one part and leaves the rest alone. `log(path, title, body)` is for genuinely
   chronological entries.

## Tasks

Long-running work is one file per task, with frontmatter that makes the
directory a queue:

```markdown
---
status: open          # open | blocked | done | dropped
opened: 2026-08-17
symbols: [NVDA]
review: 2026-08-20    # when to pick this up again
---
# Does the NVDA AI-capex thesis survive Q3?

## Why this matters
## What I've done
## What's next
```

`tasks()` gives you everything open; `tasks(due_by=today)` gives you what's
actually due. **A scheduled run should open with `tasks(due_by=today)`** rather
than reconstructing its agenda by reading history — that's the difference
between a work queue and a diary.

Task files live at `tasks/{slug}.md` and sync to the user's Tasks view, so
they're a shared surface: the user can see what you're working on and why.
Write them for that reader. Close one by setting `status: done` — don't delete
it, the record of what you decided and why is the valuable part.

## Writing well for your future self

The next run has none of your context. So:

- Put the conclusion in the heading. "Thesis" is a worse heading than
  "Thesis — long into Q3 print, invalidated below 168".
- Record what would **break** a view, not just what supports it. The check
  you'll actually want to run later is "does this still hold?"
- Cross-reference by path: "see `stocks/NVDA/thesis.md`". Paths are cheap and
  `read()` resolves them.
- Date anything time-sensitive inline. A note that says "recently" is unusable
  in three weeks.

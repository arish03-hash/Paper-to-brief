# System prompt history: Milestone 1

How the system prompt in `src/brief/prompts.py` changed during M1 (planning with
`write_todos` + notes saved to disk), what each version did in practice, and why
the next version changed it.

All runs used `gpt-4o-mini` and deepagents 0.7.23. Test question for most runs:
"What is MCP?" (short, ambiguous) or the LangGraph / CrewAI / AutoGen comparison.

## Summary

| Stage | Main change | `write_todos` used? | Searched? | Tokens (one run) |
|---|---|---|---|---|
| 0 (M0 baseline) | Research + cite | n/a | Yes | 12k-21k |
| 1 | "Use write_todos to plan" | No | Yes | 12.5k-15k |
| 2 | "ALWAYS call write_todos FIRST" | No (tool did not exist) | Sometimes not at all | 5k-21k |
| (code fix) | Added `TodoListMiddleware()` | - | - | - |
| 3 | Numbered process, domain hint, notes file | Yes | Yes | 31k |
| 4 | Primary sources, update todos, accurate citations | Yes, updated | Yes | 101k |
| 5 | One notes file per sub-question | Yes, updated | Yes | 178k |
| 6 (committed) | Per-sub-question budget | Not measured yet | | |

---

## Stage 0: M0 baseline

```python
SYSTEM_PROMPT = (
    "You are a research assistant. "
    "Base your answer only on what you read, and cite the URL of the "
    "source for each point."
)
```

**What happened:** `search_web` once, then `fetch_page` on 3-4 results, then answer.
Good, cited answers at 12k-21k tokens. No planning, nothing saved.

**Why change it:** M1's goal is for the agent to plan sub-questions before
researching and to keep notes on disk.

---

## Stage 1: ask it to plan

```python
SYSTEM_PROMPT = (
    "You are a research assistant. "
    "Before you start researching, use write_todos to plan the sub-questions you need to answer. "
    "Research each sub-question using search_web and fetch_page. "
    "Base your final answer only on what you read, and cite the URL of the source for each point."
)
```

Code change at the same time: `backend=FilesystemBackend(root_dir="runs/notes", virtual_mode=True)`.

**What happened:** no `write_todos` in any trace. Same `search_web` then `fetch_page`
pattern as M0.

**Assumption at the time:** `gpt-4o-mini` ignores soft instructions, so the wording needs to be stronger.

---

## Stage 2: make it a hard rule

```python
SYSTEM_PROMPT = (
    "You are a research assistant. "
    "ALWAYS call write_todos FIRST, before any search, to list the sub-questions you will research. "
    "Then research each sub-question using search_web and fetch_page. "
    "Base your final answer only on what you read, and cite the URL of the source for each point."
)
```

**What happened:** still no `write_todos`, and new strange behaviour:

- On the comparison question it wrote its plan with **`write_file`** to
  `/tmp/research_todos.txt` (a sensible plan, just the wrong tool), then researched.
- On "What is MCP?" and "What is Firewall?" it wrote an answer **from its own
  knowledge** into a file (`/mnt/data/faq/MCP.txt`, `/temp/firewall_overview.txt`),
  never searched, and returned that. The MCP answer listed medical/legal meanings
  and missed Model Context Protocol. About 5k tokens, 1 tool call.

**Root cause (not the prompt):** in deepagents 0.7.23, `create_deep_agent` does
**not** add `TodoListMiddleware`. Building the agent and listing its tools gives:

```
delete, edit_file, execute, fetch_page, glob, grep, ls, read_file, search_web, task, write_file
```

No `write_todos`. The prompt asked for a tool that did not exist, so the model
improvised with `write_file`.

**Fix (in `agent.py`, not the prompt):**

```python
from langchain.agents.middleware import TodoListMiddleware
...
create_deep_agent(..., middleware=[TodoListMiddleware()])
```

**Lesson:** before blaming the model for not using a tool, check the tool is in
its tool list.

---

## Stage 3: a numbered process

```python
SYSTEM_PROMPT = """You are a research assistant for AI and software engineering topics.
Interpret ambiguous terms in that context (e.g. "MCP" = Model Context Protocol).

Follow this process every time:
1. FIRST call write_todos with 2-5 sub-questions you need to answer.
2. For each sub-question, call search_web, then fetch_page on the best 1-2 results.
3. Save key facts and their URLs to /findings.md using write_file.
   Only write what you read in a source, never your own knowledge.
4. Write the final answer using only your notes, citing a URL for every point.

Never answer without calling search_web at least once."""
```

**Why each part:**
- Domain line: stops "MCP" meaning medicine or law.
- Numbered steps: small models follow a sequence better than prose.
- Fixed notes path: stops it inventing paths like `/temp/...`.
- "Only write what you read": stops it saving its own guesses as notes.
- "Never answer without search_web": a hard rule it can check itself against.

**What happened (with `TodoListMiddleware` added):**
`write_todos` -> `search_web` -> `fetch_page` x3 -> `write_file /findings.md` -> answer.
M1 worked as designed. 31k tokens.

**Problems in the answer:**
- It trusted a Medium post describing a made-up version of MCP (a "Context Encoder /
  Interpreter / Communicator", healthcare and self-driving-car uses).
- Citations pointed at the wrong source: "Key Features" was credited to
  modelcontextprotocol.io, which says nothing like it.
- Todos were written once and left as `pending`.

---

## Stage 4: source quality and honest citations

Changes to stage 3:

```
2. ... Prefer primary sources (official docs, specifications, papers) over blogs and Medium posts.
3. Update write_todos as you go, marking each sub-question completed when it is answered.
4. Save key facts to /findings.md using write_file. Next to each fact, put the URL of the
   page it came from. Only write what you read in a source, never your own knowledge.
5. Write the final answer from your findings. Cite the URL that the point actually came from.
   If sources disagree, say so.
```

**What happened:** sources were now the Anthropic announcement, Google Cloud and
the official docs. No Medium. Todos were updated (3 calls) and it ran a second
search for the item still pending. Only 1 wrong citation (down from 3).

**New problems:**
- The second `write_file` **overwrote** `/findings.md`, so notes 1-5 were lost from
  disk. The answer only survived because they were still in the conversation history.
- 101k tokens: every model call resends the full history, including each
  8,000-character fetched page.

---

## Stage 5: one notes file per sub-question

Step 4 replaced with:

```
4. Save key facts for each sub-question to its own file using write_file,
   e.g. /findings/01-definition.md, /findings/02-architecture.md.
   Never overwrite an existing findings file. Next to each fact, put the URL of the
   page it came from. Only write what you read in a source, never your own knowledge.
```

**Why:** appending to one file is error-prone for a small model. Separate files
can't overwrite each other.

**What happened:** three notes files, all intact (`01-definition.md`,
`02-frameworks-specifications.md`, `03-academic-papers.md`). Sources: Wikipedia,
the MCP docs and spec, Databricks, and an ACM paper.

**New problems:**
- 178k tokens, 17 tool calls, 8 page fetches, for "What is MCP?".
- An unnecessary sub-question ("academic papers") because the prompt asked for at least 2.
- The same paper listed twice (ACM version and arXiv preprint).

---

## Stage 6: budget (current, committed in `16c5f0f`)

Added under step 1:

```
Budget: at most 2 search_web calls and 2 fetch_page calls per sub-question.
```

**Not measured yet.** Proposed next change: scale the number of sub-questions
with the question ("1-2 for a simple definition question, up to 5 for a comparison
or multi-part question. Only include sub-questions needed to answer what was asked").

---

## Takeaways from M1

1. **Check the tool list before tuning the prompt.** Stages 1-2 were spent rewording
   a prompt for a tool that was never registered.
2. **Small models need explicit, numbered procedures** and fixed paths, not suggestions.
3. **A plan and notes make answers better and much more expensive.** Tokens went
   ~15k (M0) -> 31k -> 101k -> 178k on the same question, because fetched pages
   stay in the context and are re-sent on every call.
4. **Prompt rules don't fix source checking.** Wrong citations dropped from 3 to 1,
   but not to 0. That is the job of the M3 critic.
5. **The cost problem is what M2 is for:** a researcher subagent reads the pages in its
   own context and returns a short summary, so the main agent never carries raw pages.

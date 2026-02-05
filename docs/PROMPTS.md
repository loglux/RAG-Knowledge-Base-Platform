**Prompt System — Technical Notes**

This document describes how prompts are assembled today, what is fixed in code, and options for making prompts more configurable without breaking behavior.

**Current Behavior (As Of 2026-02-05)**

**Assembly Diagram (High Level)**
1. Retrieve active system prompt (DB override) or fallback to `SYSTEM_PROMPT`
2. Build user prompt template:
   - Wrap retrieved context in `<context>...</context>`
   - Wrap user question in `<question>...</question>`
   - Append `Answer based on the context above:`
3. If “show question N” pattern is detected:
   - Inject additional instructions into the question block
4. Send messages to the LLM:
   - `system` = system prompt
   - `user` = constructed user prompt

**System Prompt**
- Location: `app/services/rag.py`
- Variables:
  - `SYSTEM_PROMPT` (current default)
  - `SYSTEM_PROMPT_LEGACY` (older prompt used inside the current one)
- Runtime override:
  - If a prompt version exists in DB and is active, it replaces `SYSTEM_PROMPT`.
  - Lookup path: `app/services/prompts.py -> get_active_prompt()`
- Injection:
  - Always injected as the first message with role `system`.

**User Prompt (Template)**
- Location: `app/services/rag.py` in `_generate_answer`.
- Fixed in code (not stored in DB).
- Structure:
  - `<context>...</context>`
  - `<question>...</question>`
  - `Answer based on the context above:`
- Additional behavior:
  - If the request matches “show question N”, the system injects extra instructions into the question block.

**Hard‑coded Logic**
- The “show question N” detection and forced instructions are in code (not editable).
- The exact prompt envelope around context and question is fixed in code.

**Example: Current System Prompt (Default)**
Location: `app/services/rag.py` (`SYSTEM_PROMPT`)

```
Identity:
You are a retrieval assistant for a knowledge base. You answer ONLY from the provided context.

You are a helpful AI assistant that answers questions based on the provided context from a knowledge base.

Your task:
1. First, understand the FULL CONVERSATION HISTORY to grasp what the user is asking about
2. Pay attention to pronouns (it, this, that, these) - they often refer to topics from previous messages
3. Use the knowledge base context to provide accurate, detailed answers
4. Answer based ONLY on information from the knowledge base context
5. Be concise unless the user asks to show/quote content or examples
6. Reference specific sources when appropriate (e.g., "According to Source 1...")

Important:
- The conversation may contain follow-up questions - use previous messages to understand the current question
- Pronouns like "it", "this", "that" refer to topics mentioned earlier in the conversation
- Do NOT make up information not present in the context
- If the context doesn't contain enough information, say so clearly
- If the user asks to show a question, return the full verbatim text from the context.
- If the requested item spans multiple context chunks, return all relevant verbatim excerpts,
  even if they come from multiple chunks, until the item is complete.
- Do not invent missing parts or add commentary.

Context follows below.
```

**Example: Current User Prompt Template**
Location: `app/services/rag.py` (`_generate_answer`)

```
<context>
{{context}}
</context>

<question>{{question}}{{show_question_instructions}}</question>

Answer based on the context above:
```


**Why This Matters**

The prompt is actually **two parts**:
1. System prompt
2. User prompt template

We are moving to a design where **both parts live in the DB**, and there are **no runtime hardcoded defaults**.


**Selected Design (System Prompt in DB, User Template in Code)**
- `prompt_versions` contains only `system_content` for chat.
- `self_check_prompt_versions` contains only `system_content` for self-check.
- User templates are fixed in code for safety and consistency.
- A single active version is selected in `app_settings`.
- Chat responses log a single `prompt_version_id`.
- If no active prompt exists, requests should fail with a clear error.


**Required Variables (If We Make Templates Editable)**

Minimal required:
- `{{context}}`
- `{{question}}`

Conditional:
- `{{show_question_instructions}}` (inserted only when match is true)

If the editor allows removing required variables, responses can degrade or fail. We should validate before saving or activating.


**Data Storage (Target)**
- `prompt_versions.system_content` (chat)
- `self_check_prompt_versions.system_content`
- `app_settings.active_prompt_version_id` (chat)
- `app_settings.active_self_check_prompt_version_id`
- `chat_messages.prompt_version_id`


**Open Questions**

- Do we want to keep “show question N” as fixed logic, or allow prompt control?
- Should the user template be editable globally only, or per KB?
- Should prompt activation be immediate or staged (draft → activate)?
- Should we support previews/tests in UI?

**Scenarios & Modes (Proposed UX)**

We may introduce optional prompt modes selectable near the chat input (next to the Send button). Default remains standard KB chat.

**Proposed Modes**
- `Chat (default)` — current RAG chat behavior.
- `Summarize` — concise summary of retrieved context or a document.
- `Rewrite` — rewrite or rephrase the last answer (shorter, formal, simpler).
- `Extract` — extract structured facts/fields from context.

**UX Idea**
- A lightweight selector near the question input:
  - If a mode is selected, the system chooses the corresponding prompt template.
  - If not selected, it uses the default Chat prompt.

**Notes**
- This can be optional and non-intrusive.
- It does not require changing the core chat flow unless the mode is used.

**Prompt Inventory (Other Subsystems)**

The system currently includes multiple hardcoded prompts outside the main KB Chat prompt. These are candidates for future config if needed.

**1) Self‑Check Validation (RAG)**
- Location: `app/services/rag.py` (`_self_check_answer`)
- Purpose: Validate and correct the draft answer against retrieved context.
- Notes: Now intended to use DB‑backed prompts (`self_check_prompt_versions`).

**2) Chat Title Generation**
- Location: `app/services/chat_titles.py` (`generate_title`)
- Purpose: Generate a short title for a conversation.
- Notes: Prompt is short and deterministic; uses system role with instructions.

**3) Document Structure Analysis**
- Location: `app/services/document_analyzer.py` (`ANALYSIS_PROMPT`)
- Purpose: Build a flat TOC from document chunks with strict rules.
- Notes: Uses a system message (“Return only valid JSON”) plus a large user prompt template.

**4) Query Intent Extraction**
- Location: `app/services/query_intent.py` (`EXTRACTION_PROMPT`)
- Purpose: Detect structured search intent (question/section/chapter) vs semantic search.
- Notes: Uses a system message + user prompt template to return JSON.

**5) Chunk Contextualization (Embeddings)**
- Location: `app/services/chunking.py` (`DOCUMENT_CONTEXT_PROMPT`, `CHUNK_CONTEXT_PROMPT`)
- Purpose: Generate short contextual descriptions per chunk to improve retrieval.
- Notes: Both prompts are embedded in code and used for chunk enrichment.

These prompts are currently **hardcoded**. If we decide to make them configurable, we can:
- add a `mode` field to `prompt_versions` and map each subsystem to a mode, or
- create dedicated prompt tables per subsystem (higher complexity).


**Next Steps (Recommended)**

1. Decide between **Option B** (split) and **Option C** (single with locked tokens).
2. Define required variables and validation rules.
3. Update storage schema accordingly.
4. Update UI with explicit System + User sections (or protected slots).

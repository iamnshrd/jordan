# Runtime Refactor Migration Plan

## Purpose

This document defines the full migration plan for refactoring the Jordan agent
runtime so that domain policy becomes the authoritative entrypoint and no
integration can bypass it with raw LLM generation.

The immediate trigger for this work is a production leakage pattern:

- An obviously off-domain shopping/comparison question received a generic LLM
  answer instead of being blocked or redirected.
- The current local runtime does **not** reproduce that exact final answer when
  called through `python -m library run` or `python -m library prompt`.
- This strongly suggests that the primary weakness is not only in retrieval or
  frame selection, but at the boundary between runtime decisions and the
  external integration layer.

The refactor goal is therefore bigger than "improve guardrails." We need to:

- make domain policy explicit and early
- make runtime decisions structurally final
- prevent integration adapters from silently falling back to freeform generation
- make routing, retrieval, grounding, and rendering separable and testable

## Implementation Status

As of 2026-04-21, the migration has already started and the following phases are
partially or fully implemented in the repository:

- Phase 0: regression coverage added for off-domain leakage and in-domain
  decision consistency
- Phase 1: a dedicated pre-retrieval policy gateway is active in
  `library/_core/runtime/policy.py`
- Phase 2: runtime and prompt paths now emit a shared decision envelope and
  adapter contract
- Phase 3: planner execution has been split into explicit stage helpers in
  `library/_core/runtime/stages.py`, while the top-level decision assembly still
  lives in `library/_core/runtime/planner.py`
- Phase 4: assistant and knowledge-set boundaries are now represented by a
  runtime registry in `library/_core/registry.py`, with Jordan bound to
  dedicated assistant and knowledge-set configs

What remains:

- move more decision branches out of `planner.py` and make stage boundaries even
  stricter
- harden real external adapters so they cannot ignore the envelope
- formalize assistant and knowledge-set boundaries
- remove legacy compatibility paths once the new flow is fully enforced


## Problem Statement

### Observed Production Symptom

Example user question:

```text
я не могу определиться, какой бренд трусиков лучше.. Викториас сикрет или Чебоксарский трикотаж?
```

Observed production behavior:

- the user received a generic comparison answer
- the answer looked like a normal general-purpose assistant response
- the answer was not grounded in the Jordan knowledge base

### Current Local Behavior

Local reproduction through the checked-out repository currently yields:

- `python -m library run "<question>"` -> `action = ask-clarifying-question`
- `python -m library prompt "<question>"` -> `action = ask-clarifying-question`
- `system = ""` for prompt mode

This means the checked-in runtime already tries to avoid answering such queries.
The likely failure mode is:

1. the runtime returns a non-answer decision
2. the integration layer treats that as "no prompt available"
3. a raw LLM fallback is executed anyway
4. the user sees a generic off-domain answer


## Current Architecture Summary

### Core Runtime Today

- CLI entrypoints live in `library/__main__.py`
- top-level orchestration lives in `library/_core/runtime/orchestrator.py`
- the main decision logic is concentrated in `library/_core/runtime/planner.py`
- route inference lives in `library/_core/runtime/routes.py`
- frame selection lives in `library/_core/runtime/frame.py`
- retrieval and bundle assembly live in `library/_core/runtime/retrieve.py`
- strict grounding data structures live in `library/_core/runtime/grounding.py`
- synthesis lives in `library/_core/runtime/synthesize.py`
- rendering lives in `library/_core/runtime/respond.py`
- LLM prompt assembly lives in `library/_core/runtime/llm_prompt.py`
- narrow domain guardrails live in `library/_core/runtime/guardrails.py`

### Session and State

- file-backed per-user state lives in `library/_adapters/fs_store.py`
- continuity lives in `library/_core/session/continuity.py`
- progress estimation lives in `library/_core/session/progress.py`
- derived user profile and session state live in `library/_core/session/state.py`

### KB Layer

- KB build pipeline lives in `library/_core/kb/build.py`
- KB diagnostics live in `library/_core/kb/doctor.py`
- DB access lives in `library/db.py`
- source manifest lives in `library/manifest.json`

### Mentor Layer

- proactive mentor selection lives in `library/_core/mentor/checkins.py`
- proactive tick entrypoint lives in `library/_core/mentor/tick.py`
- delivery dispatch lives in `library/mentor_dispatch.py`


## Root Causes We Are Addressing

### 1. Policy Is Too Narrow

Current `guardrails.py` only covers a small set of off-domain classes:

- astrology
- esoterics
- fortune-telling
- roleplay bait
- certainty-demand

This is not enough for the actual product boundary of a Jordan-specific
psychological/philosophical agent.

### 2. "Any Non-Empty Question Uses KB"

The current planner logic is effectively KB-first for all non-empty inputs.
That makes the system try to interpret obviously unrelated questions through
retrieval, which then creates weak "general" matches and noisy fallback frames.

### 3. `general` Is Too Permissive

The `general` route still allows the runtime to proceed into frame selection and
bundle scoring, which creates a path toward accidental semantic leakage.

### 4. Final Decisions Are Not Enforced At Integration Boundaries

The runtime can say:

- clarify
- deny
- do not build an LLM prompt

But the outer caller may still interpret "empty system prompt" as permission to
call a raw model.

### 5. Planner Is Overloaded

`planner.py` currently mixes:

- reply bookkeeping
- domain filtering
- routing
- retrieval validation
- session side effects
- synthesis gating
- response path branching

That makes the control flow harder to reason about and easier to accidentally
work around.


## Target Architecture

The target runtime should look like this:

```text
channel adapter
-> policy gateway
-> assistant router
-> retrieval pipeline
-> grounding gate
-> renderer / prompt builder
-> delivery adapter
```

### Design Rules

1. Policy runs before retrieval.
2. Off-domain questions never reach freeform generation.
3. `general` is not an answerable route by default.
4. Integrations consume a single typed decision envelope.
5. Retrieval, synthesis, and rendering are only reachable after policy approval.
6. Session updates are side effects of accepted decisions, not prerequisites for
   permission to answer.


## Refactor Principles

- Prefer explicit data contracts over implicit branching.
- Prefer hard boundaries over prompt-only behavioral hints.
- Prefer narrow assistant scope over universal assistant behavior.
- Prefer testable stages over one "smart" planner.
- Prefer deny/clarify to weakly grounded speculation.
- Preserve KB and mentor value while isolating them from policy decisions.


## Non-Goals

This migration does **not** primarily aim to:

- redesign the knowledge base schema
- replace SQLite
- change the source corpus
- rewrite the mentor subsystem from scratch
- optimize for broader general-purpose usefulness

We are tightening the Jordan agent into a more reliable domain-specific system,
not turning it into a general assistant.


## Migration Phases

## Phase 0: Freeze Current Behavior

### Goal

Create a reliable safety net before structural changes.

### Deliverables

- regression cases for off-domain leakage
- regression cases for in-domain grounded questions
- regression cases covering `run`, `prompt`, and adapter-style execution
- explicit expected decision types for each case

### Cases To Add

Off-domain:

- shopping and brand comparisons
- product recommendations
- weather
- news
- celebrity facts
- coding help
- medical comparisons
- legal/financial queries

In-domain:

- shame/self-contempt
- resentment
- discipline collapse
- meaning and vocation
- relationship maintenance
- truth/self-deception

### Files Likely To Touch

- `scripts/`
- `library/runtime_regression_cases.json`
- `library/voice_regression_cases.json`
- possibly new regression fixture files for policy

### Acceptance Criteria

- the current runtime behavior is captured in automated checks
- the shopping/brand leakage case exists as a permanent regression
- tests distinguish between runtime-safe behavior and adapter-unsafe behavior


## Phase 1: Introduce A Dedicated Policy Gateway

### Goal

Move domain and policy classification into its own first-class stage before
retrieval or frame selection.

### Deliverables

- new `policy` module or package under `library/_core/runtime/`
- domain classes such as:
  - `in_domain`
  - `out_of_domain`
  - `ambiguous`
  - `policy_redirect`
- policy reasons such as:
  - `shopping_comparison`
  - `general_consumer_advice`
  - `current_events`
  - `general_facts`
  - `technical_help`
  - `medical_or_legal`

### Required Behavior

- product comparison questions are classified before retrieval
- Jordan-only domain scope is modeled explicitly
- ambiguous cases yield a clarification policy result
- policy results carry user-facing text when needed

### Files Likely To Touch

- new `library/_core/runtime/policy.py` or `library/_core/runtime/policy/`
- `library/_core/runtime/guardrails.py`
- `library/_core/runtime/orchestrator.py`
- `library/_core/runtime/planner.py`

### Acceptance Criteria

- no off-domain shopping query reaches frame selection
- policy decisions are logged with explicit reason codes
- guardrail behavior is no longer just a narrow keyword filter


## Phase 2: Introduce A Single Decision Envelope

### Goal

Replace the current loose result shape with one canonical contract consumed by
all runtime entrypoints and integrations.

### Deliverables

- new typed decision envelope
- all entrypoints (`run`, `prompt`, adapter usage) return or consume that same
  structure

### Proposed Decision Types

- `deny`
- `clarify`
- `respond_kb`
- `respond_policy_text`

### Suggested Envelope Fields

- `decision_type`
- `assistant_id`
- `domain_status`
- `reason_code`
- `allow_model_call`
- `allow_retrieval`
- `final_user_text`
- `prompt_payload`
- `trace_id`
- `decision_meta`

### Files Likely To Touch

- `library/_core/runtime/grounding.py`
- `library/_core/runtime/orchestrator.py`
- `library/_core/runtime/respond.py`
- `library/_core/runtime/llm_prompt.py`
- `library/__main__.py`

### Acceptance Criteria

- all entrypoints speak the same decision language
- callers do not infer intent from empty strings or missing fields
- `allow_model_call` is explicit and enforceable


## Phase 3: Split The Planner Into Stages

### Goal

Decompose the monolithic planner into smaller stage modules with clear
responsibilities.

### Target Stage Boundaries

- `policy_stage`
- `routing_stage`
- `retrieval_stage`
- `grounding_stage`
- `render_stage`
- `session_side_effects_stage`

### Deliverables

- reduced `planner.py` surface area
- stage-local unit tests
- clear data flow between stages

### Refactor Notes

- `policy_stage` must precede everything else
- `session_side_effects_stage` should not gate answer permission
- stage outputs should be data objects, not ad hoc dicts wherever possible

### Files Likely To Touch

- `library/_core/runtime/planner.py`
- `library/_core/runtime/frame.py`
- `library/_core/runtime/retrieve.py`
- `library/_core/runtime/synthesize.py`
- `library/_core/runtime/respond.py`

### Acceptance Criteria

- each stage can be tested independently
- the critical path is readable from top to bottom
- planner no longer mixes policy, retrieval, and persistence concerns


## Phase 4: Make Assistant Scope Explicit

### Goal

Separate "Jordan as an assistant identity" from "the shared runtime
infrastructure."

### Deliverables

- assistant registry
- assistant-specific scope definition
- assistant-specific knowledge-set binding

### Suggested Structure

- `library/_core/assistants/base.py`
- `library/_core/assistants/jordan.py`
- `library/_core/knowledge_sets/jordan.py`

### Assistant Config Should Define

- allowed domains
- denied domains
- clarification style
- retrieval source set
- voice contract
- mentor availability

### Why This Matters

Right now the repo behaves like one custom personality with one runtime. That
makes domain rules implicit. A proper assistant registry makes scope explicit
and testable.

### Acceptance Criteria

- Jordan scope is represented in code, not only in prompt/persona docs
- future assistants can reuse the runtime without inheriting Jordan policy
- integrations can route by assistant instead of by prompt convention


## Phase 5: Lock Down Integration Boundaries

### Goal

Prevent any adapter from issuing raw LLM calls after a deny/clarify decision.

### Deliverables

- one canonical integration adapter contract
- strict enforcement for model-call permissions
- explicit failure behavior when adapters violate expected flow

### Mandatory Rules

- if `decision_type != respond_kb`, no raw LLM generation may occur
- if `decision_type == clarify`, user receives the provided clarification text
- template fallback rendering is only allowed for valid KB-backed answers
- empty `system` prompt must never be interpreted as "just answer normally"

### Files Likely To Touch

- `library/_core/runtime/orchestrator.py`
- `library/_core/runtime/llm_prompt.py`
- `library/mentor_dispatch.py`
- any Telegram/OpenClaw-facing adapter code outside this repo, if applicable

### Acceptance Criteria

- the shopping/brand leakage case is impossible even if prompt building returns
  no system text
- adapters must branch on `decision_type`, not on prompt-string presence
- failures become explicit and observable instead of silent fallbacks


## Phase 6: Tighten Routing And Retrieval Semantics

### Goal

Remove the semantic leakage path where off-domain questions drift into weak
`general` retrieval and fallback frames.

### Deliverables

- revised route semantics
- revised `general` handling
- stricter answerability conditions before synthesis

### Required Changes

- `general` should no longer be answerable by default
- frame selection should operate only after policy approval
- broad or unrelated questions should clarify instead of selecting top-score
  fallback frames
- retrieval should not run when domain scope is already rejected

### Files Likely To Touch

- `library/_core/runtime/routes.py`
- `library/_core/runtime/frame.py`
- `library/_core/runtime/retrieval_validator.py`
- `library/_core/runtime/retrieve.py`

### Acceptance Criteria

- off-domain queries do not create meaningful Jordan frames
- in-domain queries still reach retrieval normally
- `general` becomes an explicit ambiguity state, not a permissive sink


## Phase 7: Decouple Session State From Permissioning

### Goal

Keep continuity/progress/profile useful without allowing them to influence the
 fundamental permission to answer unrelated questions.

### Deliverables

- session/state code moved out of the authorization path
- state updates executed only after approved policy/routing outcomes

### Refactor Notes

- continuity should enrich valid responses
- progress should tune tone or follow-up shape
- user profile should not rescue weak off-domain retrieval

### Files Likely To Touch

- `library/_core/session/continuity.py`
- `library/_core/session/progress.py`
- `library/_core/session/state.py`
- `library/_core/runtime/planner.py`

### Acceptance Criteria

- state modules are clearly side-effect or enrichment layers
- deny/clarify behavior does not depend on continuity state
- response authorization is deterministic from policy and routing inputs


## Phase 8: Rebuild Observability Around Decisions

### Goal

Make future leaks easy to diagnose from logs and traces.

### Deliverables

- decision-centric structured logs
- explicit model-call allow/deny events
- adapter outcome tracing
- reason-code dashboards or at least log-friendly categories

### What Must Be Logged

- domain classification result
- assistant selection result
- retrieval allowed or skipped
- model call allowed or forbidden
- final decision type
- adapter delivery action
- any attempted fallback path

### Files Likely To Touch

- `library/logging_config.py`
- `library/utils.py`
- `library/_core/runtime/orchestrator.py`
- adapter entrypoints

### Acceptance Criteria

- one trace can explain why a message was denied, clarified, or answered
- future regressions are diagnosable without reading code first
- integration-layer bypasses leave obvious evidence


## Phase 9: Compatibility Cleanup

### Goal

Remove dead legacy paths after the new flow is stable.

### Deliverables

- remove obsolete helper branches
- remove duplicated guardrail logic
- shrink compatibility wrappers that bypass the new contract

### Candidates For Cleanup

- legacy planner branches
- wrappers that expose partial internals as public runtime behavior
- prompt-building paths that assume LLM fallback is always legal

### Acceptance Criteria

- there is one preferred runtime path
- dead or ambiguous code paths are deleted, not just deprecated
- documentation matches the new architecture


## Recommended Order Of Implementation

1. Phase 0: freeze behavior with regressions
2. Phase 1: introduce policy gateway
3. Phase 2: introduce decision envelope
4. Phase 5: lock integration boundaries early
5. Phase 3: split planner into stages
6. Phase 6: tighten routing/retrieval semantics
7. Phase 7: decouple session side effects
8. Phase 8: improve observability
9. Phase 4: formalize assistant scope if not already folded into earlier work
10. Phase 9: cleanup and deletion

This ordering is intentional. The fastest risk reduction comes from enforcing
policy and decision contracts before large internal cleanup.


## Rollout Strategy

### Step 1: Shadow Mode

- compute new policy decisions alongside existing logic
- log mismatches
- do not yet flip production behavior

### Step 2: Enforced Policy, Legacy Retrieval

- policy gateway becomes authoritative
- retrieval and synthesis remain mostly unchanged

### Step 3: Enforced Decision Envelope

- all integrations must branch on typed decisions
- raw fallback is disallowed

### Step 4: Internal Stage Refactor

- split planner into stages under the safety of already-enforced policy

### Step 5: Legacy Removal

- delete compatibility code once traces and regressions are stable


## Risks

### Risk: Over-Blocking Legitimate In-Domain Queries

Mitigation:

- keep an `ambiguous -> clarify` bucket instead of overusing `deny`
- maintain a healthy in-domain regression suite

### Risk: Integration Drift Outside This Repository

Mitigation:

- document the decision envelope contract
- make adapter misuse fail loudly
- audit external callers

### Risk: Refactor Breaks Mentor Flows

Mitigation:

- keep mentor delivery out of phase-1 changes
- route mentor through the same envelope model later

### Risk: Partial Migration Creates Two Decision Systems

Mitigation:

- one migration toggle at a time
- delete old branches as soon as the new path is stable


## Definition Of Done

The migration is complete when all of the following are true:

- off-domain shopping/product/news/weather questions cannot trigger generic LLM
  answers through any supported entrypoint
- `run`, `prompt`, and integration adapters all agree on one canonical decision
- `general` is not treated as an answerable route by default
- Jordan in-domain questions still receive grounded, source-aware answers
- logs clearly show why each message was denied, clarified, or answered
- legacy bypass paths have been removed
- documentation and tests reflect the new architecture


## Immediate Next Step

Start with Phase 0 and Phase 1:

- add the regression cases first
- then implement the dedicated policy gateway

Those two steps create the safety rail for everything else in this migration.

# Agent Instructions

## Core Behavior
- Always check memory before answering. If you've discussed this topic before, reference it.
- When you learn something new about Bill or his preferences, save it to memory.
- If a task requires multiple steps, outline them before executing.
- When uncertain, ask for clarification rather than guessing.

## Tool Usage
- Use tools when they'd be more accurate than your knowledge.
- For file operations, always confirm paths before writing.
- Shell commands: prefer safe, read-only commands. Ask before anything destructive.

## Knowledge Base
Reference files live in the workspace. Use `list_directory` and `read_file` to access them when a task requires depth.

**About_BR/** — Bill's profile and writing style:
- `BR_OS_profile.md` — ZMOS personality assessment, God Prompt analysis, growth edges, experiment designs
- `writeprint-br-executive_coach_educator_writer.md` — full writing style analysis with rated traits and examples

**About_Projects/** — LearnWell business and campaigns:
- `LearnWell_Profile_v1.1.md` — company profile, segments, buyer psychology, portfolio, pricing
- `LearnWell-Visibility-Plan.md` — rated communities and podcasts with GIG/CCS fit scores
- `MMP-AI-Outreach/MMP-AI_Outreach_Sequence_v2.1.md` — Dream 40 campaign, 20-day activity map, GHL automation
- `MMP-AI-Outreach/lw-lp-mmp-ai PDF.md` — MMP-AI landing page briefing
- `MMP-AI-Outreach/The_80_20_Content_Protocol.md` — content creation protocol

**reference/** — quick-reference docs:
- `content-calendar.md` — cadence, themes, upcoming topics
- `fsf-stack-conventions.md` — tech stack rules and patterns
- `ideal-client-profile.md` — ICP segments and disqualifiers
- `product-portfolio.md` — offering details and sequence

**projects/** — current work:
- `current-sprint.md` — active tasks and blockers
- `quarterly-goals.md` — Q1 2026 objectives

## When to Read Reference Files
- Content drafting → read `writeprint` first for voice
- Outreach or positioning → read `LearnWell_Profile` + `ideal-client-profile`
- Marketing/visibility → read `LearnWell-Visibility-Plan`
- MMP-AI campaign tasks → read `MMP-AI_Outreach_Sequence`
- Technical decisions → read `fsf-stack-conventions`
- Personality/coaching topics → read `BR_OS_profile`
- Don't read files speculatively. Only when the task requires the detail.

## Memory Management
- Save important facts, preferences, and decisions to memory.
- Don't save trivial or temporary information.
- When Bill corrects you, update the relevant memory.

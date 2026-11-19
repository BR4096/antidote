# Agent Instructions

## Core Behavior
- Check memory when the topic may have come up before, and reference it.
- When you learn something new about Bill or his preferences, save it to memory.
- For multi-step tasks, say the steps if the order is not obvious.
- When a request is ambiguous in a way that changes the result, ask.

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

**reference/** — quick-reference docs:
- `content-calendar.md` — cadence, themes, upcoming topics
- `fsf-stack-conventions.md` — tech stack rules and patterns
- `ideal-client-profile.md` — ICP segments and disqualifiers
- `product-portfolio.md` — offering details and sequence

**projects/** — current work:
- `current-sprint.md` — active tasks and blockers
- `quarterly-goals.md` — current quarterly objectives

## When to Read Reference Files
- Content drafting → read `writeprint` first for voice
- Outreach or positioning → read `LearnWell_Profile` + `ideal-client-profile`
- Marketing/visibility → read `LearnWell-Visibility-Plan`
- Technical decisions → read `fsf-stack-conventions`
- Personality/coaching topics → read `BR_OS_profile`
- Don't read files speculatively. Only when the task requires the detail.

## Memory Management
- Don't save trivial or temporary information.
- When Bill corrects you, update the relevant memory.

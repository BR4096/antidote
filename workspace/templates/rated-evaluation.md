# Rated Evaluation Template

## Format
| Criterion | Weight | Score | Justification |
|-----------|--------|-------|---------------|
| [Name]    | XX%    | X.X   | [Why]         |

## Rules
- Scale: 0.0 to 10.0, one decimal place
- Sort: descending by weighted score
- Every score requires a written justification
- Weights must sum to 100%, each weight justified
- Cycle: Rate → 3 improvements → implement → re-rate → compare delta

## Example: Evaluating a New Product Idea

| Criterion | Weight | Score | Justification |
|-----------|--------|-------|---------------|
| Market fit | 30% | 7.2 | Strong signal from 3 pilot conversations, but no paid validation yet |
| Build effort | 25% | 5.5 | Requires new Supabase tables + 2 new React features, ~3 weeks |
| Revenue potential | 25% | 8.0 | $2k/seat, 20-seat minimum = $40k/engagement |
| Strategic alignment | 20% | 6.8 | Extends Lead Better but competes with MMP-AI for attention |

**Weighted total:** 6.9

### Improvement cycle
1. Run 2 paid pilots to validate market fit (target: +1.5 on market fit)
2. Reuse existing FSF components to reduce build effort (target: +2.0 on build effort)
3. Bundle with EEA to avoid MMP-AI cannibalization (target: +1.0 on strategic alignment)

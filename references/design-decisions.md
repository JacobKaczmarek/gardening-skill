# Gardener — Design Decisions & Open Questions

## Open (user needs to decide)

| Question | Options |
|----------|---------|
| Plant ID confidence threshold | Always confirm even at ≥0.90 vs. auto-save high-confidence IDs |
| Baseline healthy photo at registration | Store one at add-time vs. only on checkups |
| Escalation if user ignores reminders | Follow-up after 48h vs. silent vs. escalate to partner |
| Vacation mode scope | Household-wide pause vs. per-plant pause |
| Plant death reason tracking | Required vs. optional vs. skip |
| Reaction vs. reply confirmation | Tap emoji vs. type "done" |

When the user makes one of these decisions, move it down to "Settled" and update `SKILL.md` to reflect it.

## Settled

1. **Always confirm plant ID** before saving — no auto-save even with high confidence (current behaviour even when Pl@ntNet returns ≥0.50)
2. **S3-compatible storage for photos** — separate from PostgreSQL; boto3 client supports any S3-compatible backend
3. **18:00 Warsaw daily** — fixed time, timezone-aware scheduling
4. **Seasonal adjustments** — watering frequency multiplied: winter 1.5x, summer 0.7x
5. **Monthly checkups** — 1st of month, photo comparison against baseline
6. **Shared plants supported** — multiple owners, all household members get reminders
7. **Vacation mode** — pause all reminders for a date range
8. **Archive with history** — plants kept in DB after death with reason

# Platform-Agnostic Gateway Reminder Pattern

Use this pattern to keep gardening logic independent from Telegram/Discord/WhatsApp specifics.

## Core rules

- Gateway is transport; skill owns domain logic.
- Reminder scripts emit facts only, not final prose.
- Agent generates final user-facing text.
- Agent sends explicitly to each recipient target.
- Confirmations are plain text, not callback/button dependent.

## Script contract

Return structured JSON like:

```json
{
  "generated_at": "2026-01-01T18:00:00+01:00",
  "tasks": [
    {
      "plant_id": 101,
      "plant_name": "Example Plant",
      "species": "Example species",
      "care_type": "water",
      "next_due": "2026-01-01T18:00:00+01:00",
      "base_frequency_days": 7,
      "owner_id": 1
    }
  ],
  "recipients": [
    {
      "gardener_user_id": 1,
      "hermes_user_id": "user-a",
      "name": "User A",
      "timezone": "Europe/Warsaw",
      "targets": ["telegram:123456789"]
    }
  ]
}
```

## Recipient normalization

Support both:

```json
{"telegram": "123456789"}
```

and:

```json
{"telegram": {"target": "telegram:123456789"}}
```

Both normalize to a Hermes `send_message` target string.

## Inbound identity

Use a helper like `gardener_get_current_identity()` to read session context (`platform`, `user_id`, `chat_id`, `thread_id`, `target`).
Do not infer identity from free text.

## Suggested tests

- script output contains facts + recipients only
- recipient target normalization works for compact and explicit shapes
- due-care and plant listing are profile-wide (no legacy household filtering)
- identity helper builds valid targets

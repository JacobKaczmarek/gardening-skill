# Reminder Delivery (Platform-Agnostic)

## Design

Reminder scripts return structured facts only.
They do not send messages and do not produce final wording.

Agent responsibilities:
1. Parse script JSON output
2. Write user-facing reminder text
3. Send one message per recipient target via `send_message`

## Script output contract

`daily_reminders.py` should return:

```json
{
  "generated_at": "2026-01-01T18:00:00+01:00",
  "tasks": [
    {
      "plant_id": 101,
      "plant_name": "Living Room Fern",
      "species": "Nephrolepis exaltata",
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

No `message` field by design.

## Delivery pattern

- If `tasks` is empty: send nothing.
- If tasks exist: generate concise natural reminder text.
- Fan out explicitly to each target in `recipients[].targets`.

Avoid broadcast-style delivery for per-user reminders.

## Recipient target format

Supported identifier styles:

```json
{"telegram": "123456789"}
```

or

```json
{"telegram": {"target": "telegram:123456789", "kind": "dm"}}
```

Both should normalize to Hermes target strings.

## Acknowledgments

Core confirmations are text-based and communicator-neutral:
- `ok`
- `done`
- `watered`
- local-language equivalents

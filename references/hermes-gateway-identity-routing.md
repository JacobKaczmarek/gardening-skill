# Hermes Gateway Identity & Routing (Gardening)

## Decision

Gardening is communicator-agnostic.
Hermes gateway is transport; Gardening owns plant/care domain state.

## Inbound identity

Use session context values when available:

- `HERMES_SESSION_PLATFORM`
- `HERMES_SESSION_USER_ID`
- `HERMES_SESSION_CHAT_ID`
- `HERMES_SESSION_THREAD_ID`
- `HERMES_SESSION_USER_NAME`

Normalize to a common identity object:

```json
{
  "platform": "telegram",
  "user_id": "123456789",
  "chat_id": "123456789",
  "thread_id": null,
  "target": "telegram:123456789"
}
```

Then resolve communicator identity to `gardener_users.id`.

## Outbound routing

Store one or more Hermes `send_message` targets per user (JSON map).
Example:

```json
{
  "telegram": {"target": "telegram:123456789", "kind": "dm"},
  "whatsapp": {"target": "whatsapp:+15551234567", "kind": "dm"},
  "discord": {"target": "discord:123456789012345678", "kind": "dm_or_channel"}
}
```

Legacy shorthand is also supported:

```json
{"telegram": "123456789"}
```

## Reminder fanout rule

Do explicit fanout:
1. Script emits JSON facts (`tasks`, `recipients`)
2. Agent writes final reminder text
3. Agent calls `send_message` for each recipient target

This keeps behavior portable across communicators.

## Acknowledgment rule

Use plain text confirmations in core flow.
Avoid platform-specific buttons/reactions as requirements.

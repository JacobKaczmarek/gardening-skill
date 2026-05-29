# Platform-Agnostic Design

## Runtime model

- One Hermes profile = one household context.
- Skill logic is communicator-agnostic.
- Gateway handles transport specifics.

## Core entities

1. `gardener_users` — people interacting with this profile
2. `gardener_plants` — plant records
3. `gardener_plant_owners` — many-to-many ownership
4. Care schedules/events/checkups/reminders

## Routing model

Store communicator routing in user identifiers as Hermes-sendable targets.
Examples:

```json
{
  "telegram": "123456789",
  "discord": {"target": "discord:123456789012345678"},
  "whatsapp": {"identifier": "+15551234567"}
}
```

Normalize into target strings for `send_message` fanout.

## Reminder architecture

- Script (`daily_reminders.py`) returns JSON facts only.
- Agent writes natural reminder wording.
- Agent performs explicit recipient fanout via `send_message`.
- Acknowledgments are text-based and portable.

## Compatibility rules

- Do not make core workflows depend on communicator-specific callbacks/buttons.
- Do not reintroduce legacy household filtering in runtime logic.
- Keep ownership normalized (relation table), not array sharing fields.

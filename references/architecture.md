# Gardening Architecture & Infrastructure

## Overview

The gardening skill is split into three layers:

1. Domain logic (`tools/`) — plants, schedules, ownership, checkups
2. Background scripts (`scripts/`) — periodic fact generation (JSON)
3. Hermes gateway integration — inbound identity + outbound message delivery

## Message flow

Inbound:
- User sends message from any supported communicator
- Hermes gateway provides session identity context
- Skill resolves user and executes plant-care actions

Outbound:
- Script computes due tasks and recipients
- Agent writes final user-facing reminder text
- Agent sends per-recipient messages via `send_message`

## Data/storage

- PostgreSQL for domain state
- S3-compatible object storage for photos
- Species guides in references/filesystem

## Identification and analysis

- Species identification: Pl@ntNet via `gardener_identify_plant`
- Visual health/context analysis: `vision_analyze`

## Portability principles

- No hardcoded user IDs, tokens, or local absolute paths
- No communicator-specific requirements in core flow
- Text confirmations as baseline interaction
- Explicit send fanout, not implicit broadcast assumptions

## Operational checks

- Provider/model configured and healthy
- Gateway running
- DB reachable
- S3 bucket reachable
- Reminder script returns valid JSON contract

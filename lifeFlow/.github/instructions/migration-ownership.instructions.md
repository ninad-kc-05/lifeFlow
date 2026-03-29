---
description: "Use when discussing Django migrations, schema changes, or database setup tasks in this repository. The user owns migration execution."
name: "Migration Ownership"
---
# Migration Ownership Rules

- Do not provide `manage.py migrate` commands unless the user explicitly asks for them.
- Do not ask the user to run migration commands by default.
- When schema changes are made, state only that migrations are pending and that the user will run them.
- If migration status is needed, ask for confirmation instead of prescribing migration commands.

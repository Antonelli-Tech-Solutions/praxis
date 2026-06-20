---
description: Log in to the Praxis knowledge graph MCP server
---

Log me into the Praxis MCP server so `praxis_get_context` / `praxis_add_insight` work.

Credentials (optional) passed as arguments: $ARGUMENTS
- If two arguments are given, treat them as `<email> <password>`.
- A third argument, if present, is the org id to select.
- If no credentials were given, ask me for my Praxis email and password before proceeding (do not guess).

Then:
1. Call the `praxis_login` MCP tool with my email and password (and `org_id` if I named one).
2. Report the result:
   - If I belong to multiple orgs, list them and ask which to use, then call `praxis_select_org`.
   - If I belong to no orgs, ask whether to **create** one (`praxis_create_org`, I set a join password) or **join** an existing one (`praxis_join_org`, needs its password).
3. Confirm the final state with `praxis_whoami`.

Note: my password is only used to authenticate with Cognito (a refresh token is cached, not the password).

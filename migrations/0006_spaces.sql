-- Spaces: named, private working knowledge graphs within an org.
--
-- A login normally owns exactly one live graph per org (user_id = principal.sub).
-- A *space* lets one login own MULTIPLE user_id partitions in an org, selected
-- per request via the X-Praxis-Space header, so different agents can drive
-- different live graphs concurrently. The effective tenant user_id is derived
-- app-side: the default space (no header) stays `principal.sub` (existing data
-- is untouched), and a named space `<sid>` maps to `f"{principal.sub}::space:{sid}"`
-- (see spaces_store.py / app.py active_user_id).
--
-- Spaces are PRIVATE to the creating login: the row is keyed by owner_sub and is
-- never shared across logins. `space_id` is a user-picked slug validated in the
-- app (lowercase letters/digits/dash/underscore, not 'default', no ':'), so the
-- SQL imposes no shape beyond NOT NULL. Purely additive and idempotent
-- (IF NOT EXISTS); re-running is harmless, and the org FK cascades a deleted
-- org's spaces away with it.

CREATE TABLE IF NOT EXISTS spaces (
    org_id     text NOT NULL,
    owner_sub  text NOT NULL,
    space_id   text NOT NULL,
    name       text,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, owner_sub, space_id),
    FOREIGN KEY (org_id) REFERENCES orgs (org_id) ON DELETE CASCADE
);

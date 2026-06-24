-- Re-tenant orphaned facts written during the broken-auth window.
--
-- Facts that landed under (default, dev-user) are moved onto the real
-- (praxis, 24782438-1091-70d3-3e55-f9f3510b2aba) tenant. Guards against PK
-- collisions: only ids that don't already exist under the target tenant are
-- moved (NOT EXISTS), so a colliding orphan is left in place rather than
-- clobbering the canonical praxis row. Safe to re-run (a second run moves 0).
--
-- depends: 0001_reembed_candidates

UPDATE facts AS o
   SET org_id = 'praxis', user_id = '24782438-1091-70d3-3e55-f9f3510b2aba'
 WHERE o.org_id = 'default' AND o.user_id = 'dev-user'
   AND NOT EXISTS (
       SELECT 1 FROM facts AS t
        WHERE t.org_id = 'praxis'
          AND t.user_id = '24782438-1091-70d3-3e55-f9f3510b2aba'
          AND t.id = o.id
   );

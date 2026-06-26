import { useOrg } from "../../auth/OrgGate";

/**
 * In-header dropdown for switching between the orgs a user belongs to.
 * Selecting an org swaps the active `X-Praxis-Org` in place — the candidate
 * and graph providers key on the org id, so data refetches automatically.
 */
export function OrgSwitcher() {
  const { orgId, orgs, selectOrg } = useOrg();

  // Nothing to switch between — hide the control entirely.
  if (orgs.length <= 1) {
    return null;
  }

  return (
    <div className="org-switcher">
      <label className="org-switcher__label" htmlFor="org-switcher-select">
        Organization
      </label>
      <div className="org-switcher__row">
        <select
          id="org-switcher-select"
          className="org-switcher__select"
          value={orgId}
          onChange={(e) => selectOrg(e.target.value)}
        >
          {orgs.map((org) => (
            <option key={org.orgId} value={org.orgId}>
              {org.name && org.name !== org.orgId
                ? `${org.name} (${org.orgId})`
                : org.orgId}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

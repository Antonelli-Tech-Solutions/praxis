import type { SourceFactGroup } from "../api/apiClient";

/**
 * Selection state for the fold-in browser. The DEFAULT selection unit is the
 * skill group: checking a group selects all of its facts. The group expands to
 * per-fact checkboxes so a user can deselect a single child while keeping the
 * rest of the group selected (fact-level override).
 *
 * State is stored as the set of SELECTED fact ids. A group is "checked" when all
 * its facts are selected, "indeterminate" when some (but not all) are, and
 * unchecked when none are.
 */
export type GroupCheckState = "checked" | "indeterminate" | "unchecked";

export function groupFactIds(group: SourceFactGroup): string[] {
  return group.facts.map((f) => f.id);
}

export function groupCheckState(
  group: SourceFactGroup,
  selected: ReadonlySet<string>,
): GroupCheckState {
  const ids = groupFactIds(group);
  if (ids.length === 0) return "unchecked";
  const picked = ids.filter((id) => selected.has(id)).length;
  if (picked === 0) return "unchecked";
  if (picked === ids.length) return "checked";
  return "indeterminate";
}

/** Toggle an entire group: if fully selected, clear it; otherwise select all. */
export function toggleGroup(
  group: SourceFactGroup,
  selected: ReadonlySet<string>,
): Set<string> {
  const next = new Set(selected);
  const ids = groupFactIds(group);
  const fullySelected = ids.length > 0 && ids.every((id) => next.has(id));
  if (fullySelected) {
    for (const id of ids) next.delete(id);
  } else {
    for (const id of ids) next.add(id);
  }
  return next;
}

/** Toggle a single fact (fact-level override within a group). */
export function toggleFact(
  factId: string,
  selected: ReadonlySet<string>,
): Set<string> {
  const next = new Set(selected);
  if (next.has(factId)) {
    next.delete(factId);
  } else {
    next.add(factId);
  }
  return next;
}

/** The default selection: every fact in every group is selected. */
export function defaultSelection(groups: SourceFactGroup[]): Set<string> {
  const next = new Set<string>();
  for (const group of groups) {
    for (const id of groupFactIds(group)) next.add(id);
  }
  return next;
}

/** Selected ids in group order (stable for the fold-in request body). */
export function selectedFactIds(
  groups: SourceFactGroup[],
  selected: ReadonlySet<string>,
): string[] {
  const out: string[] = [];
  for (const group of groups) {
    for (const id of groupFactIds(group)) {
      if (selected.has(id)) out.push(id);
    }
  }
  return out;
}

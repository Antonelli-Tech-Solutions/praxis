import { describe, expect, it } from "vitest";
import type { SourceFactGroup } from "../api/apiClient";
import {
  defaultSelection,
  groupCheckState,
  selectedFactIds,
  toggleFact,
  toggleGroup,
} from "./foldInSelection";

function fact(id: string) {
  return { id, text: id, scope: "global", clusterLabel: "", state: "active" };
}

const GROUPS: SourceFactGroup[] = [
  { key: "g1", label: "Testing", facts: [fact("a"), fact("b")] },
  { key: "g2", label: "Refactoring", facts: [fact("c")] },
];

describe("defaultSelection", () => {
  it("selects every fact in every group by default", () => {
    const selected = defaultSelection(GROUPS);
    expect([...selected].sort()).toEqual(["a", "b", "c"]);
  });
});

describe("groupCheckState", () => {
  it("is checked when all facts in the group are selected", () => {
    expect(groupCheckState(GROUPS[0], new Set(["a", "b"]))).toBe("checked");
  });

  it("is indeterminate when only some facts are selected", () => {
    expect(groupCheckState(GROUPS[0], new Set(["a"]))).toBe("indeterminate");
  });

  it("is unchecked when no facts are selected", () => {
    expect(groupCheckState(GROUPS[0], new Set())).toBe("unchecked");
  });
});

describe("toggleGroup (cluster-default unit)", () => {
  it("checking a group selects all its facts", () => {
    const next = toggleGroup(GROUPS[0], new Set());
    expect([...next].sort()).toEqual(["a", "b"]);
  });

  it("toggling a fully-selected group clears all its facts", () => {
    const next = toggleGroup(GROUPS[0], new Set(["a", "b", "c"]));
    expect([...next].sort()).toEqual(["c"]);
  });

  it("toggling a partially-selected group selects the rest", () => {
    const next = toggleGroup(GROUPS[0], new Set(["a"]));
    expect([...next].sort()).toEqual(["a", "b"]);
  });
});

describe("toggleFact (fact-level override)", () => {
  it("deselecting one child leaves the rest of the group selected", () => {
    const next = toggleFact("b", defaultSelection(GROUPS));
    expect([...next].sort()).toEqual(["a", "c"]);
    expect(groupCheckState(GROUPS[0], next)).toBe("indeterminate");
  });

  it("re-selecting a deselected child restores it", () => {
    const next = toggleFact("b", new Set(["a", "c"]));
    expect(next.has("b")).toBe(true);
  });
});

describe("selectedFactIds", () => {
  it("returns selected ids in stable group order", () => {
    const selected = new Set(["c", "a"]);
    expect(selectedFactIds(GROUPS, selected)).toEqual(["a", "c"]);
  });

  it("folder-select then per-node-deselect yields the remaining ids", () => {
    // Select the whole "Testing" folder (a, b)...
    let selected = toggleGroup(GROUPS[0], new Set());
    expect(selectedFactIds(GROUPS, selected)).toEqual(["a", "b"]);
    // ...then override by deselecting one node (b).
    selected = toggleFact("b", selected);
    expect(selectedFactIds(GROUPS, selected)).toEqual(["a"]);
    expect(groupCheckState(GROUPS[0], selected)).toBe("indeterminate");
  });
});

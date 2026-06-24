import { afterEach, describe, expect, it, vi } from "vitest";
import { foldIn, getSourceFacts, listOrgSources } from "./apiClient";

const AUTH = { getToken: async () => "token-123", orgId: "monica-demo" };

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("listOrgSources", () => {
  it("GETs /org/sources with org auth and normalizes the sources", async () => {
    let requestedUrl = "";
    let headers: Headers | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, init: RequestInit) => {
        requestedUrl = url;
        headers = new Headers(init.headers);
        return Promise.resolve(
          new Response(
            JSON.stringify({
              sources: [
                { userId: "me", role: "owner", isSelf: true, snapshots: ["v1"] },
                { userId: "ada", role: "member", isSelf: false, snapshots: [] },
              ],
            }),
            { status: 200 },
          ),
        );
      }),
    );

    const sources = await listOrgSources("http://127.0.0.1:8000/", AUTH);

    expect(requestedUrl).toBe("http://127.0.0.1:8000/org/sources");
    expect(headers?.get("Authorization")).toBe("Bearer token-123");
    expect(headers?.get("X-Praxis-Org")).toBe("monica-demo");
    expect(sources).toEqual([
      { userId: "me", role: "owner", isSelf: true, snapshots: ["v1"] },
      { userId: "ada", role: "member", isSelf: false, snapshots: [] },
    ]);
  });

  it("tolerates snake_case keys from the backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            sources: [{ user_id: "ada", role: "member", is_self: false, snapshots: [] }],
          }),
          { status: 200 },
        ),
      ),
    );

    const sources = await listOrgSources("http://127.0.0.1:8000");
    expect(sources[0]).toMatchObject({ userId: "ada", isSelf: false });
  });
});

describe("getSourceFacts", () => {
  it("GETs the source facts endpoint with the source query and groups", async () => {
    let requestedUrl = "";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        requestedUrl = url;
        return Promise.resolve(
          new Response(
            JSON.stringify({
              userId: "ada",
              source: "snapshot:v1",
              groups: [
                {
                  key: "g1",
                  label: "Testing",
                  facts: [
                    {
                      id: "f1",
                      text: "Write tests first",
                      scope: "global",
                      clusterLabel: "Testing",
                      source: "ada",
                      state: "active",
                    },
                  ],
                },
              ],
            }),
            { status: 200 },
          ),
        );
      }),
    );

    const facts = await getSourceFacts("http://127.0.0.1:8000", "ada", "snapshot:v1");

    expect(requestedUrl).toBe(
      "http://127.0.0.1:8000/org/sources/ada/facts?source=snapshot%3Av1",
    );
    expect(facts.groups).toHaveLength(1);
    expect(facts.groups[0].facts[0].text).toBe("Write tests first");
  });
});

describe("foldIn", () => {
  it("POSTs sourceUser/source/factIds and normalizes the result", async () => {
    let requestedUrl = "";
    let requestedBody = "";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, init: RequestInit) => {
        requestedUrl = url;
        requestedBody = String(init.body);
        return Promise.resolve(
          new Response(
            JSON.stringify({
              folded: 3,
              deduped: 1,
              conflicts: [{ newId: "n1", rivalId: "r1" }],
            }),
            { status: 200 },
          ),
        );
      }),
    );

    const result = await foldIn(
      "http://127.0.0.1:8000/",
      "ada",
      "live",
      ["f1", "f2"],
      AUTH,
    );

    expect(requestedUrl).toBe("http://127.0.0.1:8000/fold-in");
    expect(JSON.parse(requestedBody)).toEqual({
      sourceUser: "ada",
      source: "live",
      factIds: ["f1", "f2"],
    });
    expect(result).toEqual({
      folded: 3,
      deduped: 1,
      conflicts: [{ newId: "n1", rivalId: "r1" }],
    });
  });

  it("normalizes snake_case conflict ids", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            folded: 0,
            deduped: 0,
            conflicts: [{ new_id: "n9", rival_id: "r9" }],
          }),
          { status: 200 },
        ),
      ),
    );

    const result = await foldIn("http://127.0.0.1:8000", "ada", "live", ["f1"]);
    expect(result.conflicts).toEqual([{ newId: "n9", rivalId: "r9" }]);
  });
});

import type { Candidate, CandidateWriteInput, EvalMetrics } from "../types/candidate";
import type { KnowledgeGraphSnapshot } from "../types/graph";
import type { ParsedLogSession } from "../types/transcript";

export interface DataProvider {
  listCandidates(state?: string): Promise<Candidate[]>;
  getCandidate(id: string): Promise<Candidate | null>;
  promote(id: string): Promise<Candidate>;
  reject(id: string, reason?: string): Promise<void>;
  createCandidate(input: CandidateWriteInput): Promise<Candidate>;
  updateCandidate(id: string, input: CandidateWriteInput): Promise<Candidate>;
  deleteCandidate(id: string): Promise<void>;
  resolveContradiction(
    contradictionId: string,
    resolution: "keep_primary" | "keep_rival",
    keepId: string,
  ): Promise<Candidate>;
  /**
   * Resolve a contradiction with a brand-new, user-authored fact that is neither
   * side. Optional: offline fixture providers may not support it. Returns the
   * newly created candidate (both original sides are decayed server-side).
   */
  resolveContradictionCustom?(
    contradictionId: string,
    customText: string,
  ): Promise<Candidate>;
  getEvalMetrics(): Promise<EvalMetrics>;
  getGraph(): Promise<KnowledgeGraphSnapshot>;
  getTranscript(): Promise<ParsedLogSession | null>;
}

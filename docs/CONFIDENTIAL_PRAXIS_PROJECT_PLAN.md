PRAXIS Project Plan
Self-Improving Knowledge Loop for Claude Code Agents  •  9-Day Focused Sprint
Team Members & Leadership Roles
Three Gauntlet AI Fellows collaborating on a production-grade capstone. Each member leads one distinct, high-impact aspect of the project to enable authentic technical interview storytelling.
Matthew Daw	Monica Peters	Dominic Antonelli
ML & Knowledge Pipeline Lead
Ingestion, learning moment detection (ML classifier), LLM distillation, consolidation/dedup/scoring, knowledge graph, provenance.
Interview claim: "I led the ML-powered distillation engine that turns raw JSONL logs into scored, deduplicated, human-approved knowledge with full provenance."	Dashboard & Human Gate Lead
React review dashboard, human approval workflow (proposed→suggested→active), contradiction resolution UI, credibility metrics viz, injection controls.
Interview claim: "I designed and built the human approval dashboard that enforces quality gates and makes knowledge promotion transparent and measurable."	Architecture, Eval & Integration Lead
System design, eval harness (fixed tasks + metrics), GitHub hook/PR automation, Python tooling, deployment, live demo & compounding curve proof.
Interview claim: "I architected the eval harness and integration layer that rigorously proves PRAXIS delivers ≥50% fewer corrections with compounding gains."

Project Overview
PRAXIS transforms Claude Code's raw session logs (JSONL) into a compounding knowledge asset. It automatically detects learning moments, distills them via LLM into structured candidates, consolidates/dedups/scores them, routes contradictions through a human approval gate, and injects only the highest-quality knowledge back into future sessions via generated CLAUDE.md/skills. A rigorous eval harness measures before/after correction rates, proving the agent stops re-learning the same mistakes. The 9-day sprint delivers a production-ready MVP with dashboard, full provenance, and quantified improvement demo.
System Architecture

Figure 1: PRAXIS End-to-End Architecture — Raw logs become verified, injectable knowledge with measurable compounding gains.

High-Level 9-Day Timeline
Days 1–2: Project Plan, Foundation & Design  |  Days 3–5: Parallel Core Build (ML Pipeline + Dashboard + Evals)  |  Days 6–7: Integration & Human Gate  |  Day 8: Eval Harness & Measurement  |  Day 9 - 10: Demo Polish, Documentation & Final Runs
Detailed 9-Day Work Schedule
All three contributors work in parallel streams with daily syncs. Primary ownership ensures clear leadership claims while cross-support builds team cohesion.
Day	Focus & Milestones	Matthew (ML/KG)	Monica (Dashboard)	Dominic (Arch/Eval)
1	Kickoff, repo setup, log exploration, architecture finalization	Explore sample JSONL logs; define episode segmentation heuristics	Dashboard wireframes & tech stack (React + state mgmt)	Eval harness skeleton + fixed quirky repo tasks; GitHub hook design
2	Design review, data contracts, first prototypes	Prototype learning moment detector (heuristics + LLM)	Build review dashboard shell + candidate list view	Define eval metrics & cold-run baseline script
3	Core pipeline build (parallel)	Full distillation pipeline + structured candidate output + provenance	Candidate detail view + confidence score UI components	Python tooling (reader, distiller wrapper) + basic injection
4	ML & consolidation focus	Embeddings + HDBSCAN dedup/cluster; contradiction detection logic	Human gate workflow UI (proposed → suggested → active)	GitHub PR/ticket automation for promoted knowledge
5	Scoring, decay, dashboard polish	Confidence scoring (freq/recency/breadth) + decay rules	Contradiction resolution interface + credibility metrics viz	Eval harness expansion: token/time tracking + basic dashboard
6	Integration sprint	End-to-end pipeline wiring + knowledge graph stub	Dashboard ↔ backend API integration + approval actions	Full eval harness + cold vs injected comparison runner
7	Human gate + injection complete	Knowledge store (graph + CLAUDE.md generator) + injection logic	Full human approval flow + provenance display in UI	GitHub hook live + PR creation on promotion; demo data prep
8	Measurement & refinement	Run batch evals; analyze failure modes; tune thresholds	Dashboard polish + edge-case handling in review flow	Full compounding curve measurement; identify demo quirks
9	Demo, docs, handoff	Final pipeline tuning; knowledge quality report, Practice Presentation	Dashboard demo-ready; user flow video capture	Live demo script + side-by-side before/after; final docs & repo handoff

Target Outcome & Success Metrics
    • MVP delivered: Full ingestion → detection → distillation → cluster/dedup/confidence → React review dashboard with human gate → CLAUDE.md/skills injection → eval harness showing quantified improvement.
    • Primary success criterion: ≥50% reduction in user corrections on benchmark tasks vs. cold runs, with no regression in task success rate, plus visible compounding curve across sessions.
    • Each team member owns one pillar end-to-end and can demonstrate it live in technical interviews.

Work Allocation Notes
Daily 15-min sync at start of each day.

Matthew owns data/ML correctness and knowledge quality.
Monica owns UX clarity and human-gate usability.
Dominic owns measurement credibility and demo readiness.

Cross-pairing on integration days (6-7) ensures seamless handoff.

All code reviewed by at least one other member.

Final demo script co-owned but each presents their pillar.
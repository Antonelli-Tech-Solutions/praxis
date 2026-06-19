#!/usr/bin/env node
/** Render build: wire eval metrics URL from the deployed candidate API when unset. */
import { execSync } from "node:child_process";

const apiBase = process.env.VITE_PRAXIS_API_BASE_URL?.trim();
let metricsUrl = process.env.VITE_PRAXIS_EVAL_METRICS_URL?.trim();

if (!metricsUrl && apiBase) {
  metricsUrl = `${apiBase.replace(/\/$/, "")}/metrics`;
} else if (metricsUrl && !/^https?:\/\//i.test(metricsUrl)) {
  const suffix = process.env.VITE_PRAXIS_EVAL_METRICS_SUFFIX?.trim() || "/metrics";
  metricsUrl = `https://${metricsUrl.replace(/\/$/, "")}${suffix}`;
}

if (metricsUrl) {
  process.env.VITE_PRAXIS_EVAL_METRICS_URL = metricsUrl;
}

execSync("vite build", { stdio: "inherit", env: process.env });

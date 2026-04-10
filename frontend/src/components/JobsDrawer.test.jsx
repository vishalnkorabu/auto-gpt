import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import JobsDrawer from "./JobsDrawer";

test("renders observability summary and recent errors", () => {
  render(
    <JobsDrawer
      open
      onClose={() => {}}
      jobs={[]}
      observability={{
        queue: { mode: "celery" },
        research_jobs: { running: 2 },
        requests: { total: 12, errors: 1 },
        usage: { total_tokens: 3400, estimated_cost_usd: 0.0425 },
        recent_errors: [{ kind: "request", path: "/api/chat/start", message: "HTTP 500", created_at: "2026-04-10T10:00:00Z" }],
      }}
      jobsFilter="all"
      onFilterChange={() => {}}
      onRefresh={() => {}}
      onCancel={() => {}}
      onRetry={() => {}}
    />
  );

  expect(screen.getByText("celery")).toBeInTheDocument();
  expect(screen.getByText("3400 tokens")).toBeInTheDocument();
  expect(screen.getByText("/api/chat/start")).toBeInTheDocument();
});

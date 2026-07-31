import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SourceTraceDrawer } from "./SourceTraceDrawer";

import { traceDeepLinkPath } from "@/components/common/SourceTraceLink";
import { getTrace } from "@/services/tracing";

type TestSpan = { span_id: string; span_kind: string; children?: TestSpan[] };

vi.mock("@/hooks/useApi", () => ({
  useApi: () => ({ api: {} }),
}));

vi.mock("@/services/tracing", () => ({
  getTrace: vi.fn(),
}));

vi.mock("@/components/common", () => ({
  CopyableChip: ({ label }: { label: string }) => <span>{label}</span>,
}));

vi.mock("@/components/traces/utils/spans", () => ({
  flattenSpans: (spans: TestSpan[]): TestSpan[] => spans.flatMap((span) => [span, ...flatten(span.children ?? [])]),
}));

function flatten(spans: TestSpan[]): TestSpan[] {
  return spans.flatMap((span) => [span, ...flatten(span.children ?? [])]);
}

vi.mock("@/components/traces/components/SpanTree", () => ({
  SpanTree: ({
    selectedSpanId,
    onSelectSpan,
    spans,
  }: {
    selectedSpanId: string | null;
    onSelectSpan: (spanId: string | null) => void;
    spans: TestSpan[];
  }) => (
    <div data-testid="span-tree" data-selected-span={selectedSpanId ?? ""}>
      {flatten(spans).map((span) => (
        <button key={span.span_id} onClick={() => onSelectSpan(span.span_id)}>
          select {span.span_id}
        </button>
      ))}
    </div>
  ),
}));

vi.mock("@/components/traces/components/SpanDetails", () => ({
  SpanDetails: ({ span, children }: { span: TestSpan; children: React.ReactNode }) => (
    <div data-testid="span-details" data-span-id={span.span_id}>
      {children}
    </div>
  ),
  SpanDetailsHeader: () => null,
  SpanDetailsWidgets: () => null,
  SpanDetailsPanels: () => null,
}));

vi.mock("@/components/traces/data/details-strategy", () => ({
  getSpanDetailsStrategy: () => ({ panels: [], tabs: [], widgets: [] }),
}));

const TRACE = {
  trace_id: "trace-1",
  root_spans: [{ span_id: "s1", span_kind: "LLM", children: [{ span_id: "s2", span_kind: "TOOL", children: [] }] }],
};

const renderDrawer = (props?: Partial<React.ComponentProps<typeof SourceTraceDrawer>>) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onClose = vi.fn();

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SourceTraceDrawer open onClose={onClose} traceId="trace-1" taskId="task-1" {...props} />
      </MemoryRouter>
    </QueryClientProvider>
  );

  return { onClose };
};

describe("SourceTraceDrawer", () => {
  beforeEach(() => {
    vi.mocked(getTrace).mockResolvedValue(TRACE as never);
  });

  afterEach(cleanup);

  it("fetches the trace and auto-selects the first root span", async () => {
    renderDrawer();

    expect(await screen.findByTestId("span-tree")).toBeTruthy();
    expect(screen.getByText("Source trace")).toBeTruthy();
    expect(screen.getByText("trace-1")).toBeTruthy();
    expect(getTrace).toHaveBeenCalledWith(expect.anything(), { traceId: "trace-1" });

    expect(screen.getByTestId("span-tree").getAttribute("data-selected-span")).toBe("s1");
    expect(screen.getByTestId("span-details").getAttribute("data-span-id")).toBe("s1");
  });

  it("shows details for a span selected in the tree", async () => {
    renderDrawer();

    fireEvent.click(await screen.findByRole("button", { name: "select s2" }));

    expect(screen.getByTestId("span-details").getAttribute("data-span-id")).toBe("s2");
  });

  it("links to the full trace page in a new tab", async () => {
    renderDrawer();

    const link = await screen.findByRole("link", { name: /open full trace/i });
    expect(link.getAttribute("href")).toBe(traceDeepLinkPath("task-1", "trace-1"));
    expect(link.getAttribute("target")).toBe("_blank");
  });

  it("calls onClose when the close button is clicked", async () => {
    const { onClose } = renderDrawer();

    await screen.findByText("Source trace");
    fireEvent.click(screen.getByTestId("CloseIcon").closest("button")!);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows an empty state when the trace has no spans", async () => {
    vi.mocked(getTrace).mockResolvedValue({ trace_id: "trace-1", root_spans: [] } as never);

    renderDrawer();

    expect(await screen.findByText("No spans found for this trace.")).toBeTruthy();
  });

  it("shows an error state with a retry button when the trace fails to load", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.mocked(getTrace).mockRejectedValue(new Error("not found"));

    renderDrawer();

    expect(await screen.findByText(/could not be loaded/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();

    consoleError.mockRestore();
  });
});

# Trace viewer

The trace viewer's UI lives in `@arthur/shared-components` (`components/traces` there), which the platform renders too. This directory keeps what only the engine needs: data fetching, routing, the filter store, analytics, the task tour, and engine-only features.

## From the package

- Tables: `TracesTable` and the column factories (`createTraceLevelColumns` and the others), built with `useTraceColumnDependencies`.
- Drawers: `TraceDrawerView` (span tree and details, annotations, feedback, guardrail results), `SpanDrawerBody`, and `SpanTree` / `SpanDetails` for the continuous-eval and source-trace drawers.
- Annotations and feedback: `AnnotationCell`, `TraceDrawerAnnotationBar`, `FeedbackPanel`.
- Filters: `TracesFilterBar` and `TracingFilterModal`.
- Cells and helpers: token and cost tooltips, `TraceContentCell`, `Highlight`, `SpanStatusBadge`.

## Engine wiring

- `../TraceViewerProviders.tsx`, mounted in `App.tsx`, passes the user's currency, timezone and clock format, and routes copy confirmations to notistack.
- `../hooks/useTraceFeedback.ts` writes human feedback, with optimistic cache updates, toasts, analytics and the `feedbackAdded` tour event.
- `../hooks/useTraceAnnotationActions.ts` links eval annotations to their results and rerun pages, and fires the annotation tour events and anchors.
- `tables/components/TraceFiltersBar.tsx` binds the filter bar to the filter store and to the task's continuous evals.

## Engine-only

Add to dataset, the continuous-eval drawer, Run Eval on selected traces, the welcome page, the session and user drawers, and the local `TracesTable` used by add to dataset.

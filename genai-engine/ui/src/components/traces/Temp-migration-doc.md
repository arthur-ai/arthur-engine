Chunk-based approach: presentational vs container
Idea:
Shared package (“chunks”): Presentational components that receive data + callbacks via props. No useApi, useTask, useApiQuery, no adapters.
This repo (and other apps): Containers that do routing, URL state, data fetching, and form wiring, then pass props into the shared chunks.

1. What goes where
   Shared package (presentational “chunks”)
   Chunk Props / role Notes
   TracesViewLayout level, timeRange, onLevelChange, onTimeRangeChange, welcomeDismissed, welcomeContent, children (or renderLevelPane) Shell: tabs, TimeRangeSelect, welcome. No useParams/useTask.
   TracesTable (or per-level) data, columns, rowCount, pagination, onPaginationChange, isLoading, onRowClick Generic table; works with MRT or a simple table. Columns passed in.
   createTraceLevelColumns, createSpanLevelColumns, etc. { formatDate, onTrack, Chip } Column factories that return column defs. App injects formatters/chip; package owns structure.
   DrawerFrame open, onClose, title, children Reusable drawer chrome.
   TraceDrawerBody, SpanDrawerBody, SessionDrawerBody, UserDrawerBody trace/span/session/user, metrics?, isLoading, onAddToDataset?, etc. All rendering, no fetching.
   CommonDrawer (orchestration only) target, id, open, onClose, renderContent({ target, id }) renderContent is a render prop. App uses it to useQuery and return the right *DrawerBody with data.
   SpanTree spans, selectedSpanId, onSelectSpan Controlled; no useSelection/nuqs in package.
   SpanDetails, TraceContentCell, DurationCell, EvalsCell, AnnotationCell, SpanStatusBadge, TypeChip, etc. Data via props Already nearly pure.
   FilterRow filters, onFiltersChange, fieldConfig Field config can live in package; app owns filter state and mapping to API.
   TimeRangeSelect value, onChange Already presentational.
   EvaluatorsSelectorUI evaluators, versions, selectedEvaluator, selectedVersion, selectedEvals, onSelectEvaluator, onSelectVersion, onAdd, onRemove, isAdding, error? All UI; “Add” calls onAdd, container does getLlmEval... and form updates.
   EvaluatorSelectorUI evaluators, versions, selectedName, selectedVersion, onNameChange, onVersionChange, isVersionsLoading Same idea.
   Primitives — CopyableChip, Highlight, TypeChip, Drawer (or use from MUI), ResultChip, etc.
   Optional in the package:
   FormattersContext with formatDate, formatDuration, formatCurrency (defaults, e.g. dayjs). App can override via provider. Reduces prop drilling.
   onTrack (or similar) only where the chunk needs analytics (e.g. onTrack("trace.drawer_opened")). App can no-op or send to Amplitude.
   This repo (containers, stay here)
   Container Responsibility
   TracesView useParams (taskId), useQueryState (level, timeRange), useWelcomeStore, useTask. Renders TracesViewLayout and level panes.
   TraceLevel, SpanLevel, SessionLevel, UserLevel useApi, useTask, useMRTPagination, getFilteredTraces/getFilteredSpans/…, queryKeys, filter store. Build columns via create*LevelColumns({ formatDate, onTrack, Chip }) and render shared TracesTable (or _LevelTable) with data, pagination, isLoading, onRowClick.
   CommonDrawer (orchestrator) useDrawerTarget (or equivalent), open/onClose. renderContent({ target, id }) runs useQuery/getTrace/getSpan/… and returns <TraceDrawerBody trace={…} /> etc.
   EvaluatorsSelector useTask, useApi, useEvals, useEvalVersions, mutation for getLlmEval...Get, withFieldGroup. Passes lists and onAdd/onRemove/onSelect_ to EvaluatorsSelectorUI.
   EvaluatorSelector useEvals, useEvalVersions, withFieldGroup, taskId. Passes data and onNameChange/onVersionChange to EvaluatorSelectorUI.
   Stores filter.store, welcome.store, pagination-context stay here. Containers read/update and pass filters, onFiltersChange, etc. into shared chunks.
   Filtering ↔ API Mapper (filters → request) stays here. Containers pass filters into both FilterRow and the tracing API.
2. Why this is easier
   No adapters
   No TracingAdapter/EvalsAdapter; the shared package’s API is “props in, DOM out.”
   No data-fetching in the package
   No useApi, useTask, useApiQuery, or API client in the shared code.
   App keeps its stack
   Routing, query keys, evals/tracing services, form libs, and stores stay in the app.
   Clear refactor rule
   “If it touches the API or app-specific context → container in the app. If it only renders and handles UI events → presentational chunk, can live in the package.”
   Easier testing
   Chunks can be tested with mock props; containers can be tested with mocked API/hooks.
   Nuqs / URL state
   The package can stay nuqs-free: use controlled props (selectedSpanId/onSelectSpan, drawerTarget/onDrawerTargetChange). The app wires those to nuqs or useState.
3. Refactor in this repo (mechanical split)
   3.1 Trace viewer
   A. TracesView → TracesViewLayout (chunk) + TracesView (container)
   New chunk TracesViewLayout
   Props: level, timeRange, onLevelChange, onTimeRangeChange, welcomeDismissed, welcomeContent, children (or renderLevelPane(level)).
   Renders: Tabs, TimeRangeSelect, welcome, and the active level pane via children or renderLevelPane.
   Move this (and any shared layout pieces) into the future package.
   Current TracesView
   Keeps: useParams, useQueryState, useWelcomeStore, useTask, track(EVENT_NAMES…), handleLevelChange, handleTimeRangeChange.
   Renders:
   TracesViewLayout with the above as props and welcomeContent from TracesWelcomePage (or equivalent).
   The four level panes (TraceLevel, SpanLevel, …) as children or via renderLevelPane.
   CommonDrawer (the orchestration component that stays in the app for now; see C).
   B. Level tables → TracesTable (chunk) + *Level (containers)
   New chunk TracesTable (or TraceLevelTable, … if you prefer one per level):
   Props: data, columns, rowCount, pagination, onPaginationChange, isLoading, onRowClick.
   Implementation can wrap MRT or a simple table. No useApi/useMRTPagination/getFilteredTraces here.
   Column factories in the package:
   createTraceLevelColumns({ formatDate, onTrack, Chip }) (and span/session/user equivalents).
   They return the same structure you have today; the only external deps are formatDate, onTrack, and Chip. The app can pass formatDate from @/utils/formatters, track from Amplitude, and CopyableChip (or a wrapper).
   Containers TraceLevel, SpanLevel, SessionLevel, UserLevel (stay here):
   Keep: useApi, useTask, useMRTPagination, getFilteredTraces/getFilteredSpans/…, filter store, queryKeys, track.
   Build columns:
   const columns = createTraceLevelColumns({ formatDate, onTrack, Chip: CopyableChip });
   Render:
   TracesTable (or TraceLevelTable) with data, columns, rowCount, pagination, onPaginationChange, isLoading, onRowClick (e.g. set drawer target).
   C. Drawer → DrawerFrame + *DrawerBody (chunks) and CommonDrawer orchestrator (container)
   Chunk DrawerFrame
   Props: open, onClose, title, children.
   Shared drawer chrome. Can live in the package.
   Chunks TraceDrawerBody, SpanDrawerBody, SessionDrawerBody, UserDrawerBody
   Each takes the entity + optional metrics, isLoading, and any callbacks (onAddToDataset, etc.).
   All of TraceDrawerContent’s current rendering moves here; any useSuspenseQuery/getTrace/computeTraceMetrics stays in the app.
   Orchestrator CommonDrawer (stays here, or a thin wrapper in the package that only does “which body to show”):
   Reads target and id (from useDrawerTarget or props).
   Uses a render prop:
   renderContent({ target, id }) where the app:
   runs useQuery/getTrace/getSpan/… and computeTraceMetrics/…,
   returns <TraceDrawerBody trace={…} metrics={…} isLoading={…} /> (and analogously for span/session/user).
   The package can export a CommonDrawer that only does:
   open={Boolean(id)}, onClose, title=createTitle([…]), and children={renderContent({ target, id })}.
   The container in the app is the one that implements renderContent with data fetching and passes it in. So: “orchestration + render prop” can be in the package; “fetch and choose which body” stays in the app.
   Refactor steps:
   Extract TraceDrawerBody from TraceDrawerContent, same for Span/Session/User.
   In this repo, TraceDrawerContent becomes a small component that:
   takes id (and maybe target),
   uses useQuery/getTrace/computeTraceMetrics,
   renders TraceDrawerBody with the loaded data.
   CommonDrawer then:
   uses useDrawerTarget and, from target+id, renders the right *DrawerContent (the thin fetcher) which in turn renders the shared *DrawerBody.
   Later, when moving to the package: move DrawerFrame, all *DrawerBody, and optionally a CommonDrawer that only knows target/id/renderContent. The app keeps the *DrawerContent fetchers and passes renderContent that does the fetch and returns the body.
   D. SpanTree, useSelection
   SpanTree (chunk)
   Props: spans, selectedSpanId, onSelectSpan.
   Remove useSelection from inside the package; the app passes selectedSpanId and onSelectSpan (e.g. from useSelection or useQueryState).
   App
   Keeps useSelection; when rendering SpanTree (e.g. inside SpanDrawerBody or a parent), pass selectedSpanId and onSelectSpan. If SpanTree is used inside a chunk that’s passed selectedSpanId/onSelectSpan from the container, that’s enough.
   E. Filtering
   Chunk FilterRow
   Props: filters, onFiltersChange, fieldConfig.
   Field configs for trace/span/session can be in the package (they describe structure, not API).
   App
   Filter store, useSyncFiltersToUrl, and the mapper from filters to listTracesMetadata/… stay here. Containers pass filters and onFiltersChange into FilterRow and into the fetch logic.
   F. Small, already‑presentational pieces
   DurationCell, SpanStatusBadge, TypeChip, TimeRangeSelect, TraceRenderer, EvalsCell, AnnotationCell, Highlight, CopyableChip, ResultChip
   Refactor so they only depend on props (and, if you want, FormattersContext or onTrack). Then move as chunks.
   Where they’re used inside bigger chunks (e.g. columns, \*DrawerBody), the chunk gets formatDate/onTrack/Chip via props or context.
   3.2 Evals config
   G. EvaluatorsSelector → EvaluatorsSelectorUI (chunk) + EvaluatorsSelector (container)
   Chunk EvaluatorsSelectorUI
   Props:
   evaluators, versions,
   selectedEvaluator, selectedVersion,
   selectedEvals (for chips),
   onSelectEvaluator, onSelectVersion,
   onAdd, onRemove,
   isAdding, error? (e.g. “already added”).
   Renders: the two autocompletes, Add button, chips. On Add, it calls onAdd(); it does not call the API.
   Move to package.
   Container EvaluatorsSelector (stay here):
   Keeps: useTask, useApi, useEvals, useEvalVersions, mutation for getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet, withFieldGroup.
   On onAdd: run the mutation, get the eval version, push into group.pushFieldValue("evals", …), then setCurrentEvaluator({ name: null, version: null }).
   Pass evaluators, versions, selectedEvaluator, selectedVersion, selectedEvals from field.state.value.evals, onAdd (wired to the mutation), onRemove (splice from evals), isAdding, error (e.g. currentAlreadyAdded).
   Renders: <EvaluatorsSelectorUI ... />.
   H. EvaluatorSelector → EvaluatorSelectorUI (chunk) + EvaluatorSelector (container)
   Chunk EvaluatorSelectorUI
   Props: evaluators, versions, selectedName, selectedVersion, onNameChange, onVersionChange, isVersionsLoading.
   Two autocompletes only; no useEvals/useEvalVersions.
   Move to package.
   Container EvaluatorSelector (stay here):
   Keeps: useEvals, useEvalVersions, withFieldGroup, taskId.
   Passes through evaluators, versions, selectedName/selectedVersion from the form, onNameChange/onVersionChange, isVersionsLoading.
   Renders: <EvaluatorSelectorUI ... />.
4. Package surface (chunk-only)
   The shared package would expose only presentational chunks and helpers, e.g.:
   // Layout & tablesTracesViewLayoutTracesTablecreateTraceLevelColumnscreateSpanLevelColumnscreateSessionLevelColumnscreateUserLevelColumns// DrawerDrawerFrameTraceDrawerBodySpanDrawerBodySessionDrawerBodyUserDrawerBodyCommonDrawer // optional: target, id, renderContent only// Trace UISpanTreeSpanDetailsFilterRowTimeRangeSelect// + DurationCell, SpanStatusBadge, TypeChip, EvalsCell, AnnotationCell, TraceRenderer, etc.// EvalsEvaluatorsSelectorUIEvaluatorSelectorUI// Primitives & helpersCopyableChipHighlightTypeChipResultChipFormattersContext (optional)
   No TracingAdapter, EvalsAdapter, or data-fetching hooks in the package.
5. Refactor order in this repo
   A practical sequence:
   Primitives and small chunks
   Ensure DurationCell, SpanStatusBadge, TypeChip, TimeRangeSelect, CopyableChip, Highlight, ResultChip are prop-only.
   (Optional) Add FormattersContext and gradually switch these to use it where helpful.
   Column factories
   Add createTraceLevelColumns({ formatDate, onTrack, Chip }) (and span/session/user) that return the current column defs.
   In TraceLevel, replace inline columns with createTraceLevelColumns(...). Same for the other levels.
   This prepares columns for the table chunk and for moving to the package.
   TracesTable (or per-level tables)
   Extract the MRT/table usage from one level (e.g. TraceLevel) into TracesTable with data, columns, rowCount, pagination, onPaginationChange, isLoading, onRowClick.
   Refactor TraceLevel to fetch and pass these props. Repeat for Span/Session/User.
   TracesViewLayout
   Extract the shell (tabs, TimeRangeSelect, welcome, children/renderLevelPane) into TracesViewLayout.
   TracesView keeps useParams, useQueryState, useWelcomeStore, useTask, and track, and renders TracesViewLayout plus the four level components and CommonDrawer.
   Drawer bodies
   Extract TraceDrawerBody from TraceDrawerContent; TraceDrawerContent becomes a thin fetcher that uses getTrace/computeTraceMetrics and renders TraceDrawerBody.
   Do the same for Span/Session/User.
   Optionally extract DrawerFrame and a CommonDrawer that only handles target/id/renderContent; the existing CommonDrawer in the app can become a thin wrapper that implements renderContent with the \*DrawerContent fetchers.
   SpanTree and SpanDetails
   Make SpanTree take selectedSpanId and onSelectSpan; update call sites to pass them from useSelection.
   Ensure SpanDetails and other detail UIs only receive data via props.
   FilterRow
   Extract a presentational FilterRow with filters, onFiltersChange, fieldConfig.
   Containers keep the filter store and mapper, and pass filters/onFiltersChange in.
   Evals
   Extract EvaluatorsSelectorUI and EvaluatorSelectorUI with the props above.
   Refactor EvaluatorsSelector and EvaluatorSelector to be thin containers that fetch and wire form state, and render the UI chunks.
   After that, you can move the chunks into a separate package and have this app (and others) use them while keeping all API and app logic in the host.

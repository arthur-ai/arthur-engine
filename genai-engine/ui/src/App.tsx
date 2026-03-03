import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { SnackbarProvider } from "notistack";
import { NuqsAdapter } from "nuqs/adapters/react-router/v7";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import "./App.css";
import { AgentExperimentDetail } from "./components/agent-experiments/[experimentId]";
import { NewAgentExperiment } from "./components/agent-experiments/new";
import { AgentNotebookDetail } from "./components/agent-notebook/[notebookId]";
import { AllTasks } from "./components/AllTasks";
import { ApiKeysManagement } from "./components/ApiKeysManagement";
import { DatasetDetailView } from "./components/datasets/DatasetDetailView";
import { DatasetExperimentsView } from "./components/datasets/DatasetExperimentsView";
import { DatasetsView } from "./components/datasets/DatasetsView";
import { TestView } from "./components/test/TestView";
import Evaluators from "./components/evaluators/Evaluators";
import { LiveEvals } from "./components/live-evals";
import { LiveEvalDetail } from "./components/live-evals/[evalId]";
import { LiveEvalsNew } from "./components/live-evals/new";
import { LoginPage } from "./components/LoginPage";
import { ModelProviders } from "./components/model-providers";
import Notebooks from "./components/notebooks/Notebooks";
import { ExperimentDetailView } from "./components/prompt-experiments/ExperimentDetailView";
import { PromptExperimentsView } from "./components/prompt-experiments/PromptExperimentsView";
import PromptsManagement from "./components/prompts-management/PromptsManagement";
import PromptsPlayground from "./components/prompts-playground/PromptsPlaygroundWrapper";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { RagExperimentsListView, RagExperimentDetailView } from "./components/rag-experiments";
import { RagNotebooks } from "./components/retrievals/notebooks";
import { RagConfigurationsPage } from "./components/retrievals/RagConfigurationsPage";
import { RagExperimentsPage } from "./components/retrievals/RagExperimentsPage";
import { SettingsPage } from "./components/settings/SettingsPage";
import { TaskLayout } from "./components/TaskLayout";
import { TaskOverview } from "./components/TaskOverview";
import { TracesView } from "./components/TracesView";
import TransformsManagement from "./components/transforms/TransformsManagement";
import { AuthProvider } from "./contexts/AuthContext";
import { queryClient } from "./lib/queryClient";
import { AppThemeProvider } from "./theme/ThemeProvider";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppThemeProvider>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <NuqsAdapter>
            <SnackbarProvider
              anchorOrigin={{
                vertical: "top",
                horizontal: "center",
              }}
            >
              <>
                <ReactQueryDevtools />
                <AuthProvider>
                  <Router>
                    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
                      <Routes>
                        {/* Public routes */}
                        <Route path="/login" element={<LoginPage />} />

                        {/* Protected routes */}
                        <Route
                          path="/"
                          element={
                            <ProtectedRoute>
                              <AllTasks />
                            </ProtectedRoute>
                          }
                        />

                        {/* Settings routes - global/org-level pages */}
                        <Route
                          path="/settings/model-providers"
                          element={
                            <ProtectedRoute>
                              <SettingsPage>
                                <ModelProviders />
                              </SettingsPage>
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/settings/api-keys"
                          element={
                            <ProtectedRoute>
                              <SettingsPage>
                                <ApiKeysManagement />
                              </SettingsPage>
                            </ProtectedRoute>
                          }
                        />

                        {/* Task layout route: single layout with nested section routes */}
                        <Route
                          path="/tasks/:id"
                          element={
                            <ProtectedRoute>
                              <TaskLayout />
                            </ProtectedRoute>
                          }
                        >
                          <Route index element={<Navigate to="overview" replace />} />
                          <Route path="overview" element={<TaskOverview />} />
                          <Route path="model-providers" element={<Navigate to="/settings/model-providers" replace />} />
                          <Route path="api-keys" element={<Navigate to="/settings/api-keys" replace />} />
                          <Route path="rag-configurations" element={<RagConfigurationsPage />} />
                          <Route path="rag-configurations/:configId" element={<RagConfigurationsPage />} />
                          <Route path="rag-configurations/:configId/versions/:version" element={<RagConfigurationsPage />} />

                          <Route path="test" element={<TestView />} />

                          {/* Legacy redirects: old agent routes → /test */}
                          <Route path="agent-experiments" element={<Navigate to="../test?section=agent-experiments" replace />} />
                          <Route path="agent-experiments/new" element={<NewAgentExperiment />} />
                          <Route path="agent-experiments/:experimentId" element={<AgentExperimentDetail />} />

                          <Route path="agentic-notebooks" element={<Navigate to="../test?section=agentic-notebooks" replace />} />
                          <Route path="agentic-notebooks/:notebookId" element={<AgentNotebookDetail />} />

                          <Route path="datasets" element={<DatasetsView />} />
                          <Route path="datasets/:datasetId" element={<DatasetDetailView />} />
                          <Route path="transforms" element={<TransformsManagement />} />
                          <Route path="datasets/:datasetId/experiments" element={<DatasetExperimentsView />} />

                          <Route path="evaluators" element={<Evaluators />} />

                          <Route path="continuous-evals">
                            <Route index element={<LiveEvals />} />
                            <Route path="new" element={<LiveEvalsNew />} />
                            <Route path=":evalId" element={<LiveEvalDetail />} />
                          </Route>

                          <Route path="evaluators/:evaluatorName" element={<Evaluators />} />
                          <Route path="evaluators/:evaluatorName/versions/:version" element={<Evaluators />} />

                          <Route path="prompts-management" element={<PromptsManagement />} />
                          <Route path="prompts/:promptName" element={<PromptsManagement />} />
                          <Route path="prompts/:promptName/versions/:version" element={<PromptsManagement />} />

                          <Route path="notebooks" element={<Notebooks />} />
                          <Route path="playgrounds/prompts" element={<PromptsPlayground />} />

                          <Route path="prompt-experiments" element={<PromptExperimentsView />} />
                          <Route path="prompt-experiments/:experimentId" element={<ExperimentDetailView />} />

                          <Route path="rag-experiments" element={<RagExperimentsListView />} />
                          <Route path="rag-experiments/:experimentId" element={<RagExperimentDetailView />} />

                          <Route path="rag-notebooks" element={<RagNotebooks />} />
                          <Route path="rag-notebooks/:notebookId" element={<RagExperimentsPage />} />

                          <Route path="traces" element={<TracesView />} />
                        </Route>

                        {/* Redirect root to tasks */}
                        <Route path="*" element={<Navigate to="/" replace />} />
                      </Routes>
                    </div>
                  </Router>
                </AuthProvider>
              </>
            </SnackbarProvider>
          </NuqsAdapter>
        </LocalizationProvider>
      </AppThemeProvider>
    </QueryClientProvider>
  );
}

export default App;

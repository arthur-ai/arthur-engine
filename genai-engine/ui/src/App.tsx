import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { SnackbarProvider } from "notistack";
import { NuqsAdapter } from "nuqs/adapters/react-router/v7";
import { Navigate, Route, BrowserRouter as Router, Routes, useParams } from "react-router-dom";

import "./App.css";
import { AgentExperiments } from "./components/agent-experiments";
import { AgentExperimentDetail } from "./components/agent-experiments/[experimentId]";
import { NewAgentExperiment } from "./components/agent-experiments/new";
import { AgentNotebook } from "./components/agent-notebook";
import { AgentNotebookDetail } from "./components/agent-notebook/[notebookId]";
import { AllTasks } from "./components/AllTasks";
import { ApiKeysManagement } from "./components/ApiKeysManagement";
import { DatasetDetailView } from "./components/datasets/DatasetDetailView";
import { DatasetExperimentsView } from "./components/datasets/DatasetExperimentsView";
import { DatasetsView } from "./components/datasets/DatasetsView";
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
import PromptsPlayground from "./components/prompts-playground/PromptsPlayground";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { RagExperimentsListView, RagExperimentDetailView } from "./components/rag-experiments";
import { RagNotebooks } from "./components/retrievals/notebooks";
import { RagConfigurationsPage } from "./components/retrievals/RagConfigurationsPage";
import { RagExperimentsPage } from "./components/retrievals/RagExperimentsPage";
import { TaskDetailContent } from "./components/TaskDetailContent";
import { TaskLayout } from "./components/TaskLayout";
import { TaskOverview } from "./components/TaskOverview";
import { TracesView } from "./components/TracesView";
import TransformsManagement from "./components/transforms/TransformsManagement";
import { AuthProvider } from "./contexts/AuthContext";
import { queryClient } from "./lib/queryClient";

const TaskRedirect = () => {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/tasks/${id}/overview`} replace />;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
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
                  <div className="min-h-screen bg-gray-50">
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

                      {/* Task routes with layout */}
                      <Route path="/tasks/:id" element={<TaskRedirect />} />

                      <Route
                        path="/tasks/:id/overview"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <TaskOverview />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/task-details"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <TaskDetailContent />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/model-providers"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <ModelProviders />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/api-keys"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <ApiKeysManagement />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/tasks/:id/rag-configurations"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <RagConfigurationsPage />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route path="/tasks/:id/agent-experiments">
                        <Route
                          index
                          element={
                            <ProtectedRoute>
                              <TaskLayout>
                                <AgentExperiments />
                              </TaskLayout>
                            </ProtectedRoute>
                          }
                        />

                        <Route
                          path="new"
                          element={
                            <ProtectedRoute>
                              <TaskLayout>
                                <NewAgentExperiment />
                              </TaskLayout>
                            </ProtectedRoute>
                          }
                        />

                        <Route
                          path=":experimentId"
                          element={
                            <ProtectedRoute>
                              <TaskLayout>
                                <AgentExperimentDetail />
                              </TaskLayout>
                            </ProtectedRoute>
                          }
                        />
                      </Route>

                      <Route path="/tasks/:id/agentic-notebooks">
                        <Route
                          index
                          element={
                            <ProtectedRoute>
                              <TaskLayout>
                                <AgentNotebook />
                              </TaskLayout>
                            </ProtectedRoute>
                          }
                        />

                        <Route
                          path=":notebookId"
                          element={
                            <ProtectedRoute>
                              <TaskLayout>
                                <AgentNotebookDetail />
                              </TaskLayout>
                            </ProtectedRoute>
                          }
                        />
                      </Route>

                      <Route
                        path="/tasks/:id/datasets"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <DatasetsView />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/datasets/:datasetId"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <DatasetDetailView />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/transforms"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <TransformsManagement />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/datasets/:datasetId/experiments"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <DatasetExperimentsView />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/evaluators"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <Evaluators />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route path="/tasks/:id/continuous-evals">
                        <Route
                          index
                          element={
                            <ProtectedRoute>
                              <TaskLayout>
                                <LiveEvals />
                              </TaskLayout>
                            </ProtectedRoute>
                          }
                        />

                        <Route
                          path=":evalId"
                          element={
                            <ProtectedRoute>
                              <TaskLayout>
                                <LiveEvalDetail />
                              </TaskLayout>
                            </ProtectedRoute>
                          }
                        />

                        <Route
                          path="new"
                          element={
                            <ProtectedRoute>
                              <TaskLayout>
                                <LiveEvalsNew />
                              </TaskLayout>
                            </ProtectedRoute>
                          }
                        />
                      </Route>

                      <Route
                        path="/tasks/:id/evaluators/:evaluatorName"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <Evaluators />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/evaluators/:evaluatorName/versions/:version"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <Evaluators />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/prompts-management"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <PromptsManagement />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/prompts/:promptName"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <PromptsManagement />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/prompts/:promptName/versions/:version"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <PromptsManagement />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/notebooks"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <Notebooks />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/playgrounds/prompts"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <PromptsPlayground />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/prompt-experiments"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <PromptExperimentsView />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/prompt-experiments/:experimentId"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <ExperimentDetailView />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      {/* RAG Experiments - List View */}
                      <Route
                        path="/tasks/:id/rag-experiments"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <RagExperimentsListView />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      {/* RAG Experiments - Detail View */}
                      <Route
                        path="/tasks/:id/rag-experiments/:experimentId"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <RagExperimentDetailView />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      {/* RAG Notebooks routes */}
                      <Route
                        path="/tasks/:id/rag-notebooks"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <RagNotebooks />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/rag-notebooks/:notebookId"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <RagExperimentsPage />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

                      <Route
                        path="/tasks/:id/traces"
                        element={
                          <ProtectedRoute>
                            <TaskLayout>
                              <TracesView />
                            </TaskLayout>
                          </ProtectedRoute>
                        }
                      />

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
    </QueryClientProvider>
  );
}

export default App;

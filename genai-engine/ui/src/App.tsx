import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { NuqsAdapter } from "nuqs/adapters/react-router/v7";
import { Navigate, Route, BrowserRouter as Router, Routes, useParams } from "react-router-dom";

import { AllTasks } from "./components/AllTasks";
import { ComingSoon } from "./components/ComingSoon";
import { DatasetDetailView } from "./components/datasets/DatasetDetailView";
import { DatasetExperimentsView } from "./components/datasets/DatasetExperimentsView";
import { DatasetsView } from "./components/datasets/DatasetsView";
import TransformsManagement from "./components/datasets/transforms/TransformsManagement";
import Evaluators from "./components/evaluators/Evaluators";
import { LoginPage } from "./components/LoginPage";
import { ModelProviders } from "./components/ModelProviders";
import { ExperimentDetailView } from "./components/prompt-experiments/ExperimentDetailView";
import { PromptExperimentsView } from "./components/prompt-experiments/PromptExperimentsView";
import PromptsManagement from "./components/prompts-management/PromptsManagement";
import PromptsPlayground from "./components/prompts-playground/PromptsPlayground";
import Notebooks from "./components/notebooks/Notebooks";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { RagRetrievalsPlayground } from "./components/retrievals/RagRetrievalsPlayground";
import { TaskDetailContent } from "./components/TaskDetailContent";
import { TaskLayout } from "./components/TaskLayout";
import "./App.css";
import { TracesView } from "./components/TracesView";
import { AuthProvider } from "./contexts/AuthContext";
import { queryClient } from "./lib/queryClient";

const TaskRedirect = () => {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/tasks/${id}/task-details`} replace />;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <NuqsAdapter>
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
                    path="/tasks/:id/agent-experiments"
                    element={
                      <ProtectedRoute>
                        <TaskLayout>
                          <ComingSoon featureName="Agent Experiments" description="Test and optimize agent-based task execution strategies." />
                        </TaskLayout>
                      </ProtectedRoute>
                    }
                  />

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
                    path="/tasks/:id/datasets/:datasetId/transforms"
                    element={
                      <ProtectedRoute>
                        <TaskLayout>
                          <TransformsManagement />
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
                    path="/tasks/:id/playgrounds/retrievals"
                    element={
                      <ProtectedRoute>
                        <TaskLayout>
                          <RagRetrievalsPlayground />
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

                  <Route
                    path="/tasks/:id/rag-experiments"
                    element={
                      <ProtectedRoute>
                        <TaskLayout>
                          <ComingSoon
                            featureName="RAG Experiments"
                            description="Experiment with different retrieval-augmented generation configurations."
                          />
                        </TaskLayout>
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/tasks/:id/retrievals"
                    element={
                      <ProtectedRoute>
                        <TaskLayout>
                          <ComingSoon featureName="Retrievals" description="Monitor and analyze retrieval operations and their performance." />
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
      </NuqsAdapter>
    </QueryClientProvider>
  );
}

export default App;

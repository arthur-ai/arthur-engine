import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useParams,
} from "react-router-dom";

import { AllTasks } from "./components/AllTasks";
import { ComingSoon } from "./components/ComingSoon";
import { LoginPage } from "./components/LoginPage";
import { ModelProviders } from "./components/ModelProviders";
import PromptsPlayground from "./components/prompts/PromptsPlayground";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { TaskDetailContent } from "./components/TaskDetailContent";
import { TaskLayout } from "./components/TaskLayout";
import { TracesView } from "./components/TracesView";
import { WeaviateRetrievalsPlayground } from "./components/weaviate/WeaviateRetrievalsPlayground";
import { AuthProvider } from "./contexts/AuthContext";
import "./App.css";

// Component to redirect /tasks/:id to /tasks/:id/task-details
const TaskRedirect = () => {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/tasks/${id}/task-details`} replace />;
};

function App() {
  return (
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
                    <ComingSoon
                      featureName="Agent Experiments"
                      description="Test and optimize agent-based task execution strategies."
                    />
                  </TaskLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/datasets"
              element={
                <ProtectedRoute>
                  <TaskLayout>
                    <ComingSoon
                      featureName="Datasets"
                      description="Create and manage datasets for training and evaluation."
                    />
                  </TaskLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/evaluators"
              element={
                <ProtectedRoute>
                  <TaskLayout>
                    <ComingSoon
                      featureName="Evaluators"
                      description="Manage and configure evaluation methods for your tasks."
                    />
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
                    <WeaviateRetrievalsPlayground />
                  </TaskLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/prompt-experiments"
              element={
                <ProtectedRoute>
                  <TaskLayout>
                    <ComingSoon
                      featureName="Prompt Experiments"
                      description="Test and compare different prompt variations and their effectiveness."
                    />
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
                    <ComingSoon
                      featureName="Retrievals"
                      description="Monitor and analyze retrieval operations and their performance."
                    />
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
  );
}

export default App;

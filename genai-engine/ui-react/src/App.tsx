import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { LoginPage } from "./components/LoginPage";
import { AllTasks } from "./components/AllTasks";
import { TaskDetailContent } from "./components/TaskDetailContent";
import { ComingSoon } from "./components/ComingSoon";
import { WeaviateRetrievalsPlayground } from "./components/weaviate/WeaviateRetrievalsPlayground";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { TaskLayout } from "./components/TaskLayout";
import "./App.css";

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
            <Route
              path="/tasks/:id"
              element={
                <ProtectedRoute>
                  <TaskLayout>
                    <TaskDetailContent />
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
                    <ComingSoon
                      featureName="Prompts Playground"
                      description="Experiment with and test different prompts in an interactive playground environment."
                    />
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
                    <ComingSoon
                      featureName="Traces"
                      description="View and analyze execution traces for debugging and optimization."
                    />
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

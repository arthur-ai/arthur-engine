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

            {/* Task routes */}
            <Route
              path="/tasks/:id"
              element={
                <ProtectedRoute>
                  <TaskDetailContent />
                </ProtectedRoute>
              }
            />

            {/* Task sub-routes */}
            <Route
              path="/tasks/:id/agent-experiments"
              element={
                <ProtectedRoute>
                  <ComingSoon
                    featureName="Agent Experiments"
                    description="Test and optimize agent-based task execution strategies."
                  />
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/datasets"
              element={
                <ProtectedRoute>
                  <ComingSoon
                    featureName="Datasets"
                    description="Create and manage datasets for training and evaluation."
                  />
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/evaluators"
              element={
                <ProtectedRoute>
                  <ComingSoon
                    featureName="Evaluators"
                    description="Manage and configure evaluation methods for your tasks."
                  />
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/playgrounds/prompts"
              element={
                <ProtectedRoute>
                  <ComingSoon
                    featureName="Prompts Playground"
                    description="Experiment with and test different prompts in an interactive playground environment."
                  />
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/playgrounds/retrievals"
              element={
                <ProtectedRoute>
                  <WeaviateRetrievalsPlayground />
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/prompt-experiments"
              element={
                <ProtectedRoute>
                  <ComingSoon
                    featureName="Prompt Experiments"
                    description="Test and compare different prompt variations and their effectiveness."
                  />
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/rag-experiments"
              element={
                <ProtectedRoute>
                  <ComingSoon
                    featureName="RAG Experiments"
                    description="Experiment with different retrieval-augmented generation configurations."
                  />
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/retrievals"
              element={
                <ProtectedRoute>
                  <ComingSoon
                    featureName="Retrievals"
                    description="Monitor and analyze retrieval operations and their performance."
                  />
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks/:id/traces"
              element={
                <ProtectedRoute>
                  <ComingSoon
                    featureName="Traces"
                    description="View and analyze execution traces for debugging and optimization."
                  />
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

import React from "react";

interface SidebarNavigationProps {
  onBackToDashboard: () => void;
  onNavigate: (sectionId: string) => void;
  onLogout?: () => void;
  activeSection?: string;
}

interface NavigationSection {
  id: string;
  label: string;
  items: NavigationItem[];
}

interface NavigationItem {
  id: string;
  label: string;
  onClick?: () => void;
}

export const SidebarNavigation: React.FC<SidebarNavigationProps> = ({
  onBackToDashboard,
  onNavigate,
  onLogout,
  activeSection = "task-details",
}) => {
  const navigationSections: NavigationSection[] = [
    {
      id: "observability",
      label: "Observability",
      items: [
        { id: "traces", label: "Traces" },
      ],
    },
    {
      id: "prompts",
      label: "Prompts",
      items: [
        { id: "playgrounds/prompts", label: "Prompts Playground" },
        { id: "prompts-management", label: "Prompts Management" },
        { id: "prompt-experiments", label: "Prompts Experiments" },
      ],
    },
    {
      id: "rag",
      label: "RAG",
      items: [
        { id: "playgrounds/retrievals", label: "RAG Playground" },
        { id: "retrievals", label: "RAG Management" },
        { id: "rag-experiments", label: "RAG Experiments" },
      ],
    },
    {
      id: "evals",
      label: "Evals",
      items: [
        { id: "evaluators", label: "Evals Management" },
        { id: "datasets", label: "Datasets" },
      ],
    },
    {
      id: "agents",
      label: "Agents",
      items: [

        { id: "agent-experiments", label: "Experiments" },
      ],
    },
    {
      id: "settings",
      label: "Settings",
      items: [
        { id: "task-details", label: "Task Details" },
        { id: "model-providers", label: "Model Providers" },
      ],
    },
  ];

  return (
    <nav className="w-64 bg-white shadow-sm border-r border-gray-200 flex flex-col" style={{ height: '100vh' }}>
      <div className="p-4 overflow-y-scroll" style={{ flex: 1 }}>
        <div className="mb-4">
          <button
            onClick={onBackToDashboard}
            className="w-full text-left px-3 py-2 text-sm font-medium text-gray-700 rounded-md hover:bg-gray-100 hover:text-gray-900 transition-colors duration-200"
          >
            ← All Tasks
          </button>
        </div>

        <div className="space-y-1">
          {navigationSections.map((section) => (
            <div key={section.id} className="mb-4">
              <div className="px-3 py-2 text-sm font-semibold text-gray-900">
                {section.label}
              </div>

              <ul className="ml-4 mt-1 space-y-1">
                {section.items.map((item) => {
                  const isActive = item.id === activeSection;

                  return (
                    <li key={item.id}>
                      <button
                        onClick={() => onNavigate(item.id)}
                        className={`w-full text-left px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
                          isActive
                            ? "text-blue-700 bg-blue-50"
                            : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                        }`}
                      >
                        {item.label}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Logout button at the bottom */}
      {onLogout && (
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={onLogout}
            className="w-full text-left px-3 py-2 text-sm font-medium text-gray-700 rounded-md hover:bg-gray-100 hover:text-gray-900 transition-colors duration-200"
          >
            Logout
          </button>
        </div>
      )}
    </nav>
  );
};

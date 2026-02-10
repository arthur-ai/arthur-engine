import {
  TrendingUpOutlined,
  MenuBookOutlined,
  DescriptionOutlined,
  ScienceOutlined,
  BalanceOutlined,
  TableChartOutlined,
  SettingsOutlined,
  AppsOutlined,
  KeyOutlined,
  StorageOutlined,
  ArrowBackOutlined,
  LogoutOutlined,
  LiveTvOutlined,
  InsightsOutlined,
} from "@mui/icons-material";
import Button from "@mui/material/Button";
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
  icon: React.ReactNode;
  onClick?: () => void;
}

export const SidebarNavigation: React.FC<SidebarNavigationProps> = ({ onBackToDashboard, onNavigate, onLogout, activeSection = "overview" }) => {
  const navigationSections: NavigationSection[] = [
    {
      id: "observability",
      label: "Observability",
      items: [{ id: "traces", label: "Traces", icon: <TrendingUpOutlined /> }],
    },
    {
      id: "prompts",
      label: "Prompts",
      items: [
        { id: "notebooks", label: "Prompt Notebooks", icon: <MenuBookOutlined /> },
        { id: "prompts-management", label: "Prompt Management", icon: <DescriptionOutlined /> },
        { id: "prompt-experiments", label: "Prompt Experiments", icon: <ScienceOutlined /> },
      ],
    },
    {
      id: "rag",
      label: "RAG",
      items: [
        { id: "rag-notebooks", label: "RAG Notebooks", icon: <MenuBookOutlined /> },
        { id: "rag-experiments", label: "RAG Experiments", icon: <ScienceOutlined /> },
        { id: "rag-configurations", label: "RAG Configurations", icon: <StorageOutlined /> },
      ],
    },
    {
      id: "evals",
      label: "Evals",
      items: [
        { id: "evaluators", label: "Evals Management", icon: <BalanceOutlined /> },
        { id: "continuous-evals", label: "Continuous Evals", icon: <LiveTvOutlined /> },
        { id: "datasets", label: "Datasets", icon: <TableChartOutlined /> },
        { id: "transforms", label: "Transforms", icon: <StorageOutlined /> },
      ],
    },
    {
      id: "agents",
      label: "Agents",
      items: [
        { id: "agent-experiments", label: "Agentic Experiments", icon: <ScienceOutlined /> },
        { id: "agentic-notebooks", label: "Agentic Notebooks", icon: <MenuBookOutlined /> },
      ],
    },
    {
      id: "settings",
      label: "Settings",
      items: [
        { id: "task-details", label: "Task Details", icon: <SettingsOutlined /> },
        { id: "model-providers", label: "Model Providers", icon: <AppsOutlined /> },
        { id: "api-keys", label: "API Keys", icon: <KeyOutlined /> },
      ],
    },
  ];

  const footerButtonSx = {
    justifyContent: "flex-start",
    textAlign: "left",
    px: 1.5,
    py: 1,
    fontSize: "0.875rem",
    fontWeight: 500,
    color: "text.secondary",
    borderRadius: 1,
    "&:hover": {
      bgcolor: "action.hover",
      color: "text.primary",
    },
  } as const;

  return (
    <nav className="w-64 bg-white shadow-sm border-r border-gray-200 flex flex-col h-full">
      <div className="p-4 overflow-y-auto flex-1 min-h-0">
        <div className="mb-4">
          <button
            onClick={onBackToDashboard}
            className="w-full text-left px-3 py-2 text-sm font-medium text-gray-700 rounded-md hover:bg-gray-100 hover:text-gray-900 transition-colors duration-200 flex items-center gap-2"
          >
            <ArrowBackOutlined fontSize="small" />
            <span>Back to All Tasks</span>
          </button>
        </div>

        <div className="space-y-1">
          {/* Overview item - appears at the top */}
          <div className="mb-4">
            <button
              onClick={() => onNavigate("overview")}
              className={`w-full text-left px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 flex items-center gap-3 ${
                activeSection === "overview" ? "text-blue-700 bg-blue-50" : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <span className="shrink-0">
                <InsightsOutlined />
              </span>
              <span>Overview</span>
              <svg className="ml-auto h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          {navigationSections.map((section) => (
            <div key={section.id} className="mb-4">
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">{section.label}</div>

              <ul className="mt-1 space-y-1">
                {section.items.map((item) => {
                  const isActive = item.id === activeSection;

                  return (
                    <li key={item.id}>
                      <button
                        onClick={() => onNavigate(item.id)}
                        className={`w-full text-left px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 flex items-center gap-3 ${
                          isActive ? "text-blue-700 bg-blue-50" : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                        }`}
                      >
                        <span className="shrink-0">{item.icon}</span>
                        <span>{item.label}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* User Settings and Logout at the bottom */}

      <div className="p-4 border-t border-gray-200 shrink-0 space-y-1">
        <Button variant="text" fullWidth startIcon={<SettingsOutlined fontSize="small" />} sx={footerButtonSx}>
          User Settings
        </Button>
        {onLogout && (
          <Button variant="text" fullWidth startIcon={<LogoutOutlined fontSize="small" />} onClick={onLogout} sx={footerButtonSx}>
            Logout
          </Button>
        )}
      </div>
    </nav>
  );
};

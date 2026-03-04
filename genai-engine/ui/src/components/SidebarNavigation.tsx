import {
  TrendingUpOutlined,
  MenuBookOutlined,
  DescriptionOutlined,
  ScienceOutlined,
  BalanceOutlined,
  TableChartOutlined,
  StorageOutlined,
  ArrowBackOutlined,
  LiveTvOutlined,
  InsightsOutlined,
  ChevronRightOutlined,
} from "@mui/icons-material";
import { Link, Typography } from "@mui/material";
import React from "react";
import { useParams } from "react-router-dom";

interface SidebarNavigationProps {
  onBackToDashboard: () => void;
  onNavigate: (sectionId: string) => void;
  activeSection?: string;
  taskName?: string;
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

const navigationSections: NavigationSection[] = [
  {
    id: "observability",
    label: "Observability",
    items: [{ id: "traces", label: "Observe", icon: <TrendingUpOutlined /> }],
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
];

export const SidebarNavigation: React.FC<SidebarNavigationProps> = ({ onBackToDashboard, onNavigate, activeSection = "overview", taskName }) => {
  const { id } = useParams<{ id: string }>();

  return (
    <nav className="w-64 bg-white dark:bg-gray-900 shadow-sm border-r border-gray-200 dark:border-gray-700 flex flex-col h-full">
      <div className="p-4 overflow-y-auto flex-1 min-h-0">
        <div className="mb-4">
          <button
            onClick={onBackToDashboard}
            className="w-full text-left px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100 transition-colors duration-200 flex items-center gap-2"
          >
            <ArrowBackOutlined fontSize="small" />
            <span>Back to All Tasks</span>
          </button>
          {taskName && (
            <Typography variant="subtitle1" sx={{ fontWeight: "bold", px: 1.5, pt: 2, pb: 1, color: "text.primary" }}>
              {taskName}
            </Typography>
          )}
        </div>

        <div className="space-y-1">
          {/* Overview item - appears at the top */}
          <div className="mb-4">
            <Link
              href={`/tasks/${id}/overview`}
              underline="none"
              onClick={(e) => {
                e.preventDefault();
                onNavigate("overview");
              }}
              className={`w-full text-left px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 flex items-center gap-3 ${
                activeSection === "overview"
                  ? "text-blue-700 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/30"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100"
              }`}
            >
              <span className="shrink-0">
                <InsightsOutlined />
              </span>
              <span>Analyze</span>
              {activeSection === "overview" && <ChevronRightOutlined sx={{ ml: "auto", fontSize: 16 }} />}
            </Link>
          </div>

          {navigationSections.map((section) => (
            <div key={section.id} className="mb-4">
              {section.id !== "observability" && (
                <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">{section.label}</div>
              )}

              <ul className="mt-1 space-y-1">
                {section.items.map((item) => {
                  const isActive = item.id === activeSection;

                  return (
                    <li key={item.id}>
                      <Link
                        href={`/tasks/${id}/${item.id}`}
                        underline="none"
                        onClick={(e) => {
                          e.preventDefault();
                          onNavigate(item.id);
                        }}
                        className={`w-full text-left px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 flex items-center gap-3 ${
                          isActive
                            ? "text-blue-700 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/30"
                            : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100"
                        }`}
                      >
                        <span className="shrink-0">{item.icon}</span>
                        <span>{item.label}</span>
                        {isActive && <ChevronRightOutlined sx={{ ml: "auto", fontSize: 16 }} />}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </nav>
  );
};

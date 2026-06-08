import {
  TrendingUpOutlined,
  DescriptionOutlined,
  ScienceOutlined,
  BalanceOutlined,
  TableChartOutlined,
  StorageOutlined,
  ArrowBackOutlined,
  InsightsOutlined,
  ChevronRightOutlined,
  ChatOutlined,
} from "@mui/icons-material";
import { Link, Typography } from "@mui/material";
import React from "react";
import { useParams } from "react-router-dom";

import { useDemoMode } from "@/contexts/EngineConfigContext";
import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, TASK_TOUR_ACTIONS, type TaskTourEventName } from "@/features/task-tour/tourEvents";

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
  /** Optional `data-tour-id` attribute used by the in-task guided tour. */
  tourId?: string;
  /** Tour events dispatched when this nav item is activated. */
  tourEvents?: TaskTourEventName[];
}

function buildNavigationSections(demoMode: boolean): NavigationSection[] {
  const agentItems: NavigationItem[] = [{ id: "test", label: "Test", icon: <ScienceOutlined />, tourId: TOUR_IDS.navTest }];
  if (demoMode) {
    agentItems.push({
      id: "chatbot",
      label: "Demo Agent",
      icon: <ChatOutlined />,
      tourId: TOUR_IDS.navDemoAgent,
      tourEvents: [TASK_TOUR_ACTIONS.demoAgentOpened],
    });
  }
  return [
    {
      id: "observability",
      label: "Observability",
      items: [
        {
          id: "traces",
          label: "Observe",
          icon: <TrendingUpOutlined />,
          tourId: TOUR_IDS.navObserve,
          tourEvents: [TASK_TOUR_ACTIONS.observeOpened, TASK_TOUR_ACTIONS.deployVerified],
        },
      ],
    },
    {
      id: "prompts",
      label: "Prompts",
      items: [
        {
          id: "prompts",
          label: "Prompt",
          icon: <DescriptionOutlined />,
          tourId: TOUR_IDS.navPrompts,
          tourEvents: [TASK_TOUR_ACTIONS.promptsOpened],
        },
      ],
    },
    {
      id: "rag",
      label: "RAG",
      items: [{ id: "rag", label: "RAG", icon: <StorageOutlined /> }],
    },
    {
      id: "evals",
      label: "Evals",
      items: [
        {
          id: "evaluate",
          label: "Evaluate",
          icon: <BalanceOutlined />,
          tourId: TOUR_IDS.navEvaluate,
          tourEvents: [TASK_TOUR_ACTIONS.evaluateOpened],
        },
        {
          id: "datasets",
          label: "Dataset",
          icon: <TableChartOutlined />,
          tourId: TOUR_IDS.navDatasets,
          tourEvents: [TASK_TOUR_ACTIONS.datasetsOpened, TASK_TOUR_ACTIONS.datasetRowVerified],
        },
        { id: "transforms", label: "Transform", icon: <StorageOutlined /> },
      ],
    },
    {
      id: "agents",
      label: "Agents",
      items: agentItems,
    },
  ];
}

export const SidebarNavigation: React.FC<SidebarNavigationProps> = ({ onBackToDashboard, onNavigate, activeSection = "overview", taskName }) => {
  const { id } = useParams<{ id: string }>();
  const { demoMode } = useDemoMode();
  const navigationSections = buildNavigationSections(demoMode);

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

        <ul className="space-y-3">
          {/* Overview / Analyze */}
          <li>
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
          </li>

          {navigationSections.flatMap((section) =>
            section.items.map((item) => {
              const isActive = item.id === activeSection;
              return (
                <li key={item.id}>
                  <Link
                    href={`/tasks/${id}/${item.id}`}
                    underline="none"
                    data-tour-id={item.tourId}
                    onClick={(e) => {
                      e.preventDefault();
                      item.tourEvents?.forEach((eventName) => dispatchTourEvent(eventName));
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
            })
          )}
        </ul>
      </div>
    </nav>
  );
};

import { TextToSqlToolResult } from "@/mastra/tools";
import Prism from "prismjs";
import "prismjs/components/prism-sql";
import "prismjs/themes/prism-tomorrow.css";

interface SqlCardProps {
  userQuery?: string;
  themeColor: string;
  result: TextToSqlToolResult;
  status: "inProgress" | "executing" | "complete";
}

export function SqlCard({
  userQuery,
  themeColor,
  result,
  status,
}: SqlCardProps) {
  if (status !== "complete") {
    return (
      <div
        className="rounded-xl shadow-xl mt-6 mb-4 max-w-2xl w-full"
        style={{ backgroundColor: themeColor }}
      >
        <div className="bg-white/20 p-4 w-full">
          <p className="text-white animate-pulse">
            Generating SQL for: &ldquo;{userQuery}&rdquo;...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="rounded-xl shadow-xl mt-6 mb-4 max-w-2xl w-full"
    >
      <div className="bg-white/20 p-4 w-full">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-xl font-bold text-white">
              Generated SQL Query
            </h3>
            <p className="text-white/80 text-sm">
              Query: &ldquo;{userQuery}&rdquo;
            </p>
          </div>
          <DatabaseIcon />
        </div>

        <div className="bg-gray-900 rounded-lg p-4 mb-3">
          <pre className="text-sm whitespace-pre-wrap overflow-x-auto">
            <code
              className="language-sql"
              dangerouslySetInnerHTML={{
                __html: Prism.highlight(
                  result.sqlQuery || "",
                  Prism.languages.sql,
                  "sql"
                ),
              }}
            />
          </pre>
        </div>

        <div className="bg-white/10 rounded-lg p-3">
          <p className="text-white text-sm">
            <span className="font-semibold">Explanation:</span>{" "}
            {result.explanation || "No explanation available."}
          </p>
        </div>
      </div>
    </div>
  );
}

// Database icon for the SQL card
function DatabaseIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-8 h-8 text-white/80"
    >
      <path d="M12 2C6.48 2 2 3.79 2 6v12c0 2.21 4.48 4 10 4s10-1.79 10-4V6c0-2.21-4.48-4-10-4zM4 6c0-.55 2.4-2 8-2s8 1.45 8 2v2c0 .55-2.4 2-8 2s-8-1.45-8-2V6zm0 4c0-.55 2.4-2 8-2s8 1.45 8 2v2c0 .55-2.4 2-8 2s-8-1.45-8-2v-2zm0 4c0-.55 2.4-2 8-2s8 1.45 8 2v2c0 .55-2.4 2-8 2s-8-1.45-8-2v-2z" />
    </svg>
  );
}

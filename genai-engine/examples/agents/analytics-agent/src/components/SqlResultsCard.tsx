import { ExecuteSqlToolResult } from "@/mastra/tools";
import Prism from "prismjs";
import "prismjs/components/prism-sql";
import "prismjs/themes/prism-tomorrow.css";

interface SqlResultsCardProps {
  themeColor: string;
  result: ExecuteSqlToolResult;
  status: "inProgress" | "executing" | "complete";
}

export function SqlResultsCard({
  themeColor,
  result,
  status,
}: SqlResultsCardProps) {
  if (status !== "complete") {
    return (
      <div
        className="rounded-xl shadow-xl mt-6 mb-4 max-w-2xl w-full"
        style={{ backgroundColor: themeColor }}
      >
        <div className="bg-white/20 p-4 w-full">
          <p className="text-white animate-pulse">Executing SQL query...</p>
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
            <h3 className="text-xl font-bold text-white">SQL Query Results</h3>
            <p className="text-white/80 text-sm">Query executed successfully</p>
          </div>
          <DatabaseIcon />
        </div>

        <div className="bg-gray-900 rounded-lg p-4 mb-3">
          <pre className="text-sm whitespace-pre-wrap overflow-x-auto">
            <code
              className="language-sql"
              dangerouslySetInnerHTML={{
                __html: Prism.highlight(
                  result.query || "",
                  Prism.languages.sql,
                  "sql"
                ),
              }}
            />
          </pre>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-3">
          <div className="bg-white/10 rounded-lg p-3 text-center">
            <p className="text-white text-sm">Rows Returned</p>
            <p className="text-white font-bold text-lg">{result.rowCount ?? 0}</p>
          </div>
          <div className="bg-white/10 rounded-lg p-3 text-center">
            <p className="text-white text-sm">Execution Time</p>
            <p className="text-white font-bold text-lg">
              {result.executionTime ?? 0}ms
            </p>
          </div>
          <div className="bg-white/10 rounded-lg p-3 text-center">
            <p className="text-white text-sm">Status</p>
            <p className="text-green-400 font-bold text-lg">✓ Success</p>
          </div>
        </div>

        {result.data && result.data.length > 0 && (
          <div className="bg-white/10 rounded-lg p-3">
            <h4 className="text-white font-semibold mb-2">Query Results:</h4>
            <div className="bg-gray-900 rounded overflow-hidden max-h-64 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-800 sticky top-0">
                  <tr>
                    {Object.keys(result.data[0]).map((column, index) => (
                      <th
                        key={index}
                        className="px-3 py-2 text-left text-blue-300 font-semibold border-b border-gray-700"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.data.map((row, rowIndex) => (
                    <tr
                      key={rowIndex}
                      className={`${
                        rowIndex % 2 === 0 ? "bg-gray-900" : "bg-gray-850"
                      } hover:bg-gray-700 transition-colors`}
                    >
                      {Object.values(row).map((value, colIndex) => (
                        <td
                          key={colIndex}
                          className="px-3 py-2 text-white border-b border-gray-700"
                        >
                          {typeof value === "object" && value !== null
                            ? JSON.stringify(value)
                            : String(value)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Database icon for the SQL results card
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

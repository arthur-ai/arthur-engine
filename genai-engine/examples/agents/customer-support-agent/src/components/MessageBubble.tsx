"use client";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

export function MessageBubble({ role, content, sources }: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100"
        }`}
      >
        <div className="whitespace-pre-wrap break-words">{content}</div>
        {sources && sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-300 dark:border-gray-600">
            <div className="text-xs font-semibold mb-1 opacity-70">Sources:</div>
            <div className="text-xs space-y-1">
              {sources.map((source, idx) => (
                <div key={idx}>
                  <a
                    href={source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline opacity-80 hover:opacity-100"
                  >
                    {source}
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

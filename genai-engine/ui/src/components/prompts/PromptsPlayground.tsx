import React from "react";
import PromptComponent from "./PromptComponent";

const PromptsPlayground = () => {
  return (
    <div className="h-full w-full bg-gray-300">
      <div className={`h-full w-full p-1 grid gap-1 grid-rows-[55px_1fr]`}>
        <div className={`bg-red-500`}>
          <div>HEADER</div>
        </div>
        <div className="grid grid-cols-2 gap-1">
          <div className="bg-green-500">
            <PromptComponent />
          </div>
          <div className="bg-blue-500"></div>
        </div>
      </div>
    </div>
  );
};

export default PromptsPlayground;

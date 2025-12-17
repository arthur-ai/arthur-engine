import { ReactNode, createContext, useContext } from "react";

interface PromptProviderProps {
  children: ReactNode;
  handleRunSingleWithConfig?: (promptId: string) => Promise<void>;
}

const PromptContext = createContext<{
  handleRunSingleWithConfig?: (promptId: string) => Promise<void>;
} | null>(null);

export const usePromptContext = () => {
  const context = useContext(PromptContext);
  if (!context) throw new Error("usePromptContext must be used within PromptProvider");
  return context;
};

export const PromptProvider = ({ children, handleRunSingleWithConfig }: PromptProviderProps) => {
  return (
    <PromptContext.Provider
      value={{
        handleRunSingleWithConfig,
      }}
    >
      {children}
    </PromptContext.Provider>
  );
};

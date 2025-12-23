import { useState } from "react";

export const useHasChanged = <T>(value: T, hasher: (value: T) => string) => {
  const [currentHash, setCurrentHash] = useState<string | null>(hasher(value));
  const [prevHash, setPrevHash] = useState<string | null>(null);

  console.log({ currentHash, prevHash, value });

  if (currentHash !== prevHash) {
    setPrevHash(currentHash);
    setCurrentHash(hasher(value));
  }

  return currentHash !== prevHash;
};

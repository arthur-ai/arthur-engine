import { useState } from "react";

export const useDatasetsModalState = () => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const openCreateModal = () => setIsCreateModalOpen(true);
  const closeCreateModal = () => setIsCreateModalOpen(false);

  return {
    isCreateModalOpen,
    openCreateModal,
    closeCreateModal,
  };
};

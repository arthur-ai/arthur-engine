'use client';

import { TaskDetailContent } from '@/components/TaskDetailContent';

export default function TaskDetailsPage() {
  // This will be populated by the layout with task data
  return (
    <div className="py-6 px-6">
      <TaskDetailContent />
    </div>
  );
}

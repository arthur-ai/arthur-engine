import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from "@dnd-kit/sortable";
import Typography from "@mui/material/Typography";
import React from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { PromptType } from "../types";

import SortableMessage from "./SortableMessage";

interface MessagesSectionProps {
  prompt: PromptType;
}

const MessagesSection = ({ prompt }: MessagesSectionProps) => {
  const { dispatch } = usePromptContext();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      const oldIndex = prompt.messages.findIndex((item) => item.id === active.id);
      const newIndex = prompt.messages.findIndex((item) => item.id === over?.id);

      dispatch({
        type: "moveMessage",
        payload: {
          parentId: prompt.id,
          fromIndex: oldIndex,
          toIndex: newIndex,
        },
      });
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-start items-center">
        <span>
          <Typography variant="body1">Messages</Typography>
        </span>
      </div>
      <div className="overflow-y-auto flex-1 min-h-0">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={prompt.messages.map((msg) => msg.id)} strategy={verticalListSortingStrategy}>
            {prompt.messages.map((message) => (
              <SortableMessage
                key={message.id}
                id={message.id}
                parentId={prompt.id}
                role={message.role}
                defaultContent={message.content || ""}
                content={message.content || ""}
              />
            ))}
          </SortableContext>
        </DndContext>
      </div>
    </div>
  );
};

export default MessagesSection;

import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import AddIcon from "@mui/icons-material/Add";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import React, { useState } from "react";

import { usePromptContext } from "./PromptContext";
import SortableMessage from "./SortableMessage";
import { PromptType } from "./types";


interface MessagesSectionProps {
  prompt: PromptType;
}

const MessagesSection: React.FC<MessagesSectionProps> = ({ prompt }) => {
  const [isExpanded, setIsExpanded] = useState(true);
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

  const handleExpand = () => {
    setIsExpanded((prev) => !prev);
  };

  const handleAddMessage = () => {
    dispatch({
      type: "addMessage",
      payload: { parentId: prompt.id },
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      const oldIndex = prompt.messages.findIndex(
        (item) => item.id === active.id
      );
      const newIndex = prompt.messages.findIndex(
        (item) => item.id === over?.id
      );

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
    <div>
      <div
        onClick={handleExpand}
        className="flex justify-between cursor-pointer"
      >
        <div className="flex items-center">
          {isExpanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
          <span>Messages</span>
        </div>
        <div className="flex items-center">
          <Tooltip title="Add Message" placement="top-start" arrow>
            <IconButton
              aria-label="add message"
              onClick={(e) => {
                e.stopPropagation();
                handleAddMessage();
              }}
            >
              <AddIcon />
            </IconButton>
          </Tooltip>
        </div>
      </div>
      <Collapse in={isExpanded}>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={prompt.messages.map((msg) => msg.id)}
            strategy={verticalListSortingStrategy}
          >
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
      </Collapse>
    </div>
  );
};

export default MessagesSection;

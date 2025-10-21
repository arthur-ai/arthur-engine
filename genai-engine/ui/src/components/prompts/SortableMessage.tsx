import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import React from "react";

import MessageComponent from "./MessageComponent";
import { MessageComponentProps } from "./types";

const SortableMessage = (props: MessageComponentProps) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: props.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <MessageComponent
        {...props}
        dragHandleProps={{
          ...attributes,
          ...listeners,
        }}
      />
    </div>
  );
};

export default SortableMessage;

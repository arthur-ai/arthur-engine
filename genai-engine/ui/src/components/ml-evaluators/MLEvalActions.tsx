import { Menu } from "@base-ui/react/menu";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { ListItemButton, ListItemIcon, ListItemText } from "@mui/material";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import Paper from "@mui/material/Paper";

import { useDeleteMlEvalMutation } from "./hooks/useDeleteMlEvalMutation";

type Props = {
  evalName: string;
  onEdit: (evalName: string) => void;
};

export const MLEvalActions = ({ evalName, onEdit }: Props) => {
  const deleteMlEval = useDeleteMlEvalMutation();

  return (
    <Menu.Root>
      <Menu.Trigger
        onClick={(e) => e.stopPropagation()}
        render={<Button variant="outlined" size="small" endIcon={<ArrowDropDownIcon />} loading={deleteMlEval.isPending} className="text-nowrap" />}
      >
        ML Eval
      </Menu.Trigger>
      <Menu.Portal keepMounted>
        <Menu.Positioner sideOffset={8} side="bottom" align="center">
          <Menu.Popup render={<List component={Paper} dense className="outline-none origin-(--transform-origin) min-w-(--anchor-width)" />}>
            <Menu.Item render={<ListItemButton className="gap-4" onClick={() => onEdit(evalName)} />}>
              <ListItemText primary="Edit" />
              <ListItemIcon sx={{ minWidth: "min-content" }}>
                <EditIcon color="action" fontSize="small" />
              </ListItemIcon>
            </Menu.Item>
            <Menu.Separator render={<Divider sx={{ my: 1 }} />} />
            <Menu.Item render={<ListItemButton sx={{ color: "error.main" }} className="gap-4" onClick={() => deleteMlEval.mutate(evalName)} />}>
              <ListItemText primary="Delete" />
              <ListItemIcon sx={{ minWidth: "min-content" }}>
                <DeleteIcon color="error" fontSize="small" />
              </ListItemIcon>
            </Menu.Item>
            <Menu.Separator />
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
};

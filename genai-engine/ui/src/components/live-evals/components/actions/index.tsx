import { Menu } from "@base-ui/react/menu";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import LaunchIcon from "@mui/icons-material/Launch";
import { ListItemButton, ListItemIcon, ListItemText } from "@mui/material";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import Paper from "@mui/material/Paper";
// link external icon
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { useDeleteContinuousEval } from "../../hooks/useDeleteContinuousEval";

import { ContinuousEvalResponse } from "@/lib/api-client/api-client";

type Props = {
  config: ContinuousEvalResponse;
  onEdit: (id: string) => void;
};

export const LiveEvalActions = ({ config, onEdit }: Props) => {
  const { transform_id, task_id, llm_eval_name, llm_eval_version } = config;

  const evalUrl = useMemo(() => {
    return `/tasks/${task_id}/evaluators/${encodeURIComponent(llm_eval_name)}/versions/${encodeURIComponent(llm_eval_version)}` as const;
  }, [llm_eval_name, llm_eval_version, task_id]);

  const deleteContinuousEval = useDeleteContinuousEval();

  return (
    <Menu.Root>
      <Menu.Trigger
        onClick={(e) => e.stopPropagation()}
        render={
          <Button variant="outlined" size="small" endIcon={<ArrowDropDownIcon />} loading={deleteContinuousEval.isPending} className="text-nowrap" />
        }
      >
        Continuous Eval
      </Menu.Trigger>
      <Menu.Portal keepMounted>
        <Menu.Positioner sideOffset={8} side="bottom" align="center">
          <Menu.Popup render={<List component={Paper} dense className="outline-none origin-(--transform-origin) min-w-(--anchor-width)" />}>
            <Menu.Item render={<ListItemButton component={Link} to={`/tasks/${task_id}/transforms?id=${transform_id}`} className="gap-4" />}>
              <ListItemText primary="View Transform" />
              <ListItemIcon sx={{ minWidth: "min-content" }}>
                <LaunchIcon color="action" fontSize="small" />
              </ListItemIcon>
            </Menu.Item>
            <Menu.Item render={<ListItemButton component={Link} to={evalUrl} className="gap-4" />}>
              <ListItemText primary="View Eval" />
              <ListItemIcon sx={{ minWidth: "min-content" }}>
                <LaunchIcon color="action" fontSize="small" />
              </ListItemIcon>
            </Menu.Item>
            <Menu.Separator render={<Divider sx={{ my: 1 }} />} />
            <Menu.Item render={<ListItemButton className="gap-4" onClick={() => onEdit(config.id)} />}>
              <ListItemText primary="Edit" />
              <ListItemIcon sx={{ minWidth: "min-content" }}>
                <EditIcon color="action" fontSize="small" />
              </ListItemIcon>
            </Menu.Item>
            <Menu.Separator render={<Divider sx={{ my: 1 }} />} />
            <Menu.Item
              render={<ListItemButton sx={{ color: "error.main" }} className="gap-4" onClick={() => deleteContinuousEval.mutate(config.id)} />}
            >
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

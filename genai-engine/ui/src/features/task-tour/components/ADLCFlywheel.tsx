import { useTheme } from "@mui/material";

/**
 * Small inline SVG diagram for the welcome modal. Renders five stages around a
 * dashed circular guide, each connected with an arrowed arc, and a labelled
 * hub in the centre.
 */
export function ADLCFlywheel() {
  const theme = useTheme();

  const stages = [
    { label: "Build", angle: -90, color: theme.palette.secondary.main },
    { label: "Evaluate", angle: -18, color: theme.palette.info.main },
    { label: "Trace", angle: 54, color: theme.palette.primary.main },
    { label: "Refine", angle: 126, color: theme.palette.secondary.light },
    { label: "Deploy", angle: 198, color: theme.palette.success.main },
  ];

  const r = 58;
  const cx = 85;
  const cy = 85;
  const arrowColor = theme.palette.secondary.light;
  const arcColor = theme.palette.secondary.light;

  return (
    <svg width="170" height="170" viewBox="0 0 170 170" style={{ overflow: "visible" }} aria-hidden="true">
      <defs>
        <marker id="task-tour-adlc-arrow" markerWidth="8" markerHeight="8" refX="5" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill={arrowColor} />
        </marker>
      </defs>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={arcColor} strokeWidth={1.5} strokeDasharray="4 4" />
      {stages.map((_, i) => {
        const start = (stages[i].angle + 14) * (Math.PI / 180);
        const end = (stages[(i + 1) % stages.length].angle - 14) * (Math.PI / 180);
        const x1 = cx + r * Math.cos(start);
        const y1 = cy + r * Math.sin(start);
        const x2 = cx + r * Math.cos(end);
        const y2 = cy + r * Math.sin(end);
        return (
          <path
            key={i}
            d={`M${x1},${y1} A${r},${r} 0 0 1 ${x2},${y2}`}
            fill="none"
            stroke={arrowColor}
            strokeWidth={1.5}
            markerEnd="url(#task-tour-adlc-arrow)"
          />
        );
      })}
      <circle cx={cx} cy={cy} r={24} fill={theme.palette.background.paper} stroke={theme.palette.secondary.main} strokeWidth={1.5} />
      <text
        x={cx}
        y={cy - 1}
        textAnchor="middle"
        fontSize="10"
        fontWeight={700}
        fill={theme.palette.secondary.main}
        style={{ fontFamily: theme.typography.fontFamily }}
      >
        ADLC
      </text>
      <text
        x={cx}
        y={cy + 11}
        textAnchor="middle"
        fontSize="7.5"
        fill={theme.palette.text.secondary}
        style={{ fontFamily: theme.typography.fontFamily }}
      >
        flywheel
      </text>
      {stages.map((s) => {
        const a = s.angle * (Math.PI / 180);
        const x = cx + r * Math.cos(a);
        const y = cy + r * Math.sin(a);
        return (
          <g key={s.label}>
            <circle cx={x} cy={y} r={9} fill={theme.palette.background.paper} stroke={s.color} strokeWidth={2} />
            <text
              x={x}
              y={y + 22}
              textAnchor="middle"
              fontSize="10"
              fontWeight={600}
              fill={theme.palette.text.primary}
              style={{ fontFamily: theme.typography.fontFamily }}
            >
              {s.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

import { useId } from "react";

export interface ArthurSealProps {
  /** Rendered width/height in px. The medallion is square. */
  size?: number;
  /** Visual treatment. `gold` is the classic-diploma seal; `purple` the brand seal. */
  variant?: "gold" | "purple";
  /** Curved label text wrapped around the upper ring. Upper-cased on render. */
  label?: string;
  /** Short established/date line set in the lower disc. */
  establishedText?: string;
}

interface SealPalette {
  ringInner: string;
  ringHi: string;
  ringLo: string;
  discHi: string;
  discLo: string;
  mark: string;
  text: string;
}

const PALETTES: Record<NonNullable<ArthurSealProps["variant"]>, SealPalette> = {
  gold: {
    ringInner: "#C9A24C",
    ringHi: "#F4DE9C",
    ringLo: "#5E4612",
    discHi: "#FFF6DD",
    discLo: "#E9C76A",
    mark: "#3A2A0A",
    text: "#3A2A0A",
  },
  purple: {
    ringInner: "#7C3AED",
    ringHi: "#C4B5FD",
    ringLo: "#2E1065",
    discHi: "#A78BFA",
    discLo: "#5B21B6",
    mark: "#FFFFFF",
    text: "#FFFFFF",
  },
};

// Geometry in the 220×220 viewBox.
const CX = 110;
const CY = 110;
const R = 100; // outer ring radius
const TEXT_R = 74; // radius the curved label rides on

/** Ten-point star polygon, used as separators on the ring. */
function starPoints(cx: number, cy: number, radius: number): string {
  const pts: string[] = [];
  for (let i = 0; i < 10; i++) {
    const ang = (Math.PI / 5) * i - Math.PI / 2;
    const rad = i % 2 === 0 ? radius : radius * 0.45;
    pts.push(`${cx + Math.cos(ang) * rad},${cy + Math.sin(ang) * rad}`);
  }
  return pts.join(" ");
}

/**
 * Embossed circular medallion carrying the Arthur triangle mark. Pure SVG so it
 * captures cleanly when the certificate is exported to PNG. Mirrors the
 * `ArthurSeal` from the certificate design exploration (classic gold variant).
 */
export function ArthurSeal({
  size = 108,
  variant = "gold",
  label = "Arthur AI · Intro to Evals",
  establishedText = "EST · MMXXVI",
}: ArthurSealProps) {
  const palette = PALETTES[variant];
  // Unique gradient/filter/path ids so multiple seals never collide.
  const uid = useId().replace(/:/g, "");
  const bevelId = `seal-bevel-${uid}`;
  const discId = `seal-disc-${uid}`;
  const embossId = `seal-emboss-${uid}`;
  const textPathId = `seal-textpath-${uid}`;

  return (
    <svg width={size} height={size} viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" style={{ display: "block" }} aria-hidden="true">
      <defs>
        {/* Beveled ring fill — light catches the upper-left. */}
        <radialGradient id={bevelId} cx="35%" cy="30%" r="80%">
          <stop offset="0%" stopColor={palette.ringHi} />
          <stop offset="45%" stopColor={palette.ringInner} />
          <stop offset="100%" stopColor={palette.ringLo} />
        </radialGradient>
        {/* Inner disc fill. */}
        <radialGradient id={discId} cx="50%" cy="40%" r="70%">
          <stop offset="0%" stopColor={palette.discHi} />
          <stop offset="100%" stopColor={palette.discLo} />
        </radialGradient>
        {/* Subtle inner shadow to seat the disc into the ring. */}
        <filter id={embossId} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="2" />
          <feOffset dx="0" dy="1.5" result="off" />
          <feComposite in="off" in2="SourceAlpha" operator="arithmetic" k2="-1" k3="1" result="inner" />
          <feFlood floodColor="#000" floodOpacity="0.35" />
          <feComposite in2="inner" operator="in" />
          <feMerge>
            <feMergeNode />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        {/* Upper-arc path the curved label rides on. */}
        <path id={textPathId} d={`M ${CX - TEXT_R},${CY} a ${TEXT_R},${TEXT_R} 0 1,1 ${TEXT_R * 2},0`} fill="none" />
      </defs>

      {/* Outer beveled ring. */}
      <circle cx={CX} cy={CY} r={R} fill={`url(#${bevelId})`} />
      <circle cx={CX} cy={CY} r={R - 2} fill="none" stroke={palette.ringLo} strokeWidth="0.6" opacity="0.5" />
      {/* Inner embossed disc. */}
      <circle cx={CX} cy={CY} r={R - 14} fill={`url(#${discId})`} filter={`url(#${embossId})`} />
      <circle cx={CX} cy={CY} r={R - 14} fill="none" stroke={palette.ringLo} strokeWidth="0.8" opacity="0.55" />

      {/* Curved label on the outer ring. */}
      <text fill={palette.text} fontFamily="Geist, sans-serif" fontSize="9.5" fontWeight="600" letterSpacing="2.4">
        <textPath href={`#${textPathId}`} startOffset="50%" textAnchor="middle">
          {label.toUpperCase()}
        </textPath>
      </text>

      {/* Star separators at the ring's 3 and 9 o'clock. */}
      {[0, 180].map((deg) => {
        const rad = (deg * Math.PI) / 180;
        return <polygon key={deg} points={starPoints(CX + Math.cos(rad) * (R - 6), CY + Math.sin(rad) * (R - 6), 3.5)} fill={palette.text} />;
      })}

      {/* Arthur triangle mark, centered. */}
      <g transform={`translate(${CX - 22}, ${CY - 24}) scale(1.4)`}>
        <path
          d="M18.9714 0H13.1048L0 21.3226C0 21.3226 4.95238 30.4989 16 30.4989C27.0476 30.4989 32 21.3226 32 21.3226L18.9714 0ZM7.88572 21.2083L16 7.88173L24.1905 21.2083H7.88572Z"
          fill={palette.mark}
        />
      </g>

      {/* Established line beneath the mark. */}
      <text
        x={CX}
        y={CY + 50}
        textAnchor="middle"
        fill={palette.text}
        fontFamily="Geist Mono, monospace"
        fontSize="7"
        letterSpacing="1.6"
        fontWeight="500"
      >
        {establishedText}
      </text>
    </svg>
  );
}

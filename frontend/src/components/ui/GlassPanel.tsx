import React from "react";
import { cn } from "@/lib/utils";

interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  /** Show decorative corner brackets */
  corners?: boolean;
  /** Extra glow on hover */
  interactive?: boolean;
  /** Delay for entrance animation (in ms) */
  animationDelay?: number;
  /** No padding — let children handle it */
  noPadding?: boolean;
}

export function GlassPanel({
  children,
  corners = false,
  interactive = false,
  animationDelay = 0,
  noPadding = false,
  className,
  style,
  ...props
}: GlassPanelProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl transition-all duration-500",
        !noPadding && "p-5",
        interactive && "cursor-pointer",
        className
      )}
      style={{
        background: "var(--glass-bg)",
        backdropFilter: `blur(var(--glass-blur))`,
        WebkitBackdropFilter: `blur(var(--glass-blur))`,
        border: "1px solid var(--glass-border)",
        boxShadow: "var(--glass-shadow)",
        animation:
          animationDelay > 0
            ? `panelSlideIn 0.6s ease-out ${animationDelay}ms both`
            : "panelSlideIn 0.6s ease-out both",
        ...style,
      }}
      {...props}
    >
      {/* Inner soft glow */}
      <div
        className="absolute inset-0 pointer-events-none rounded-[inherit]"
        style={{
          boxShadow: "var(--glass-inner-glow)",
        }}
      />

      {/* Ambient green edge glow */}
      <div
        className="absolute inset-0 pointer-events-none rounded-[inherit] opacity-0 transition-opacity duration-500"
        style={{
          boxShadow:
            "inset 0 0 40px rgba(52, 211, 153, 0.06), 0 0 20px rgba(52, 211, 153, 0.03)",
          ...(interactive ? {} : {}),
        }}
      />

      {/* Corner brackets decoration */}
      {corners && (
        <>
          <CornerBracket position="top-left" />
          <CornerBracket position="top-right" />
          <CornerBracket position="bottom-left" />
          <CornerBracket position="bottom-right" />
        </>
      )}

      {/* Content */}
      <div className="relative z-10">{children}</div>

      {/* Hover glow overlay for interactive */}
      {interactive && (
        <div
          className="absolute inset-0 pointer-events-none rounded-[inherit] opacity-0 hover-glow transition-opacity duration-300"
          style={{
            background:
              "radial-gradient(circle at center, rgba(52, 211, 153, 0.08) 0%, transparent 70%)",
          }}
        />
      )}

      <style>{`
        div:hover > .hover-glow {
          opacity: 1 !important;
        }
      `}</style>
    </div>
  );
}

function CornerBracket({
  position,
}: {
  position: "top-left" | "top-right" | "bottom-left" | "bottom-right";
}) {
  const size = 12;
  const thickness = 1.5;
  const color = "rgba(52, 211, 153, 0.4)";

  const posStyles: React.CSSProperties = {
    position: "absolute",
    width: size,
    height: size,
    zIndex: 20,
    animation: "cornerPulse 4s ease-in-out infinite",
  };

  switch (position) {
    case "top-left":
      posStyles.top = 8;
      posStyles.left = 8;
      posStyles.borderTop = `${thickness}px solid ${color}`;
      posStyles.borderLeft = `${thickness}px solid ${color}`;
      break;
    case "top-right":
      posStyles.top = 8;
      posStyles.right = 8;
      posStyles.borderTop = `${thickness}px solid ${color}`;
      posStyles.borderRight = `${thickness}px solid ${color}`;
      break;
    case "bottom-left":
      posStyles.bottom = 8;
      posStyles.left = 8;
      posStyles.borderBottom = `${thickness}px solid ${color}`;
      posStyles.borderLeft = `${thickness}px solid ${color}`;
      break;
    case "bottom-right":
      posStyles.bottom = 8;
      posStyles.right = 8;
      posStyles.borderBottom = `${thickness}px solid ${color}`;
      posStyles.borderRight = `${thickness}px solid ${color}`;
      break;
  }

  return <div style={posStyles} />;
}

/** Smaller variant for inline stats, badges, etc. */
export function GlassBadge({
  children,
  className,
  style,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold",
        className
      )}
      style={{
        background: "rgba(8, 20, 12, 0.6)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(52, 211, 153, 0.15)",
        color: "#d4e4d9",
        ...style,
      }}
    >
      {children}
    </span>
  );
}

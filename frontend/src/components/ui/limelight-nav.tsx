import React, { useRef, useState, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface NavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}

interface LimelightNavProps {
  items: NavItem[];
  className?: string;
  /** Called when hovering over an item (for external state like label display) */
  onHoverItem?: (item: NavItem | null) => void;
}

// ─── LimelightNav Component ──────────────────────────────────────────────────

export function LimelightNav({
  items,
  className,
  onHoverItem,
}: LimelightNavProps) {
  const navRef = useRef<HTMLDivElement>(null);
  const [spotlightStyle, setSpotlightStyle] = useState<React.CSSProperties>({
    opacity: 0,
    transform: "translateX(0px)",
    width: 0,
  });
  const [isHovering, setIsHovering] = useState(false);
  const itemRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  const updateSpotlight = useCallback(
    (el: HTMLButtonElement | null) => {
      if (!el || !navRef.current) {
        setSpotlightStyle((prev) => ({ ...prev, opacity: 0 }));
        return;
      }

      const navRect = navRef.current.getBoundingClientRect();
      const elRect = el.getBoundingClientRect();

      const offsetX = elRect.left - navRect.left;

      setSpotlightStyle({
        opacity: 1,
        transform: `translateX(${offsetX}px)`,
        width: elRect.width,
        height: elRect.height,
      });
    },
    []
  );

  const handleMouseEnter = useCallback(
    (item: NavItem, el: HTMLButtonElement) => {
      setIsHovering(true);
      updateSpotlight(el);
      onHoverItem?.(item);
    },
    [updateSpotlight, onHoverItem]
  );

  const handleMouseLeave = useCallback(() => {
    setIsHovering(false);
    setSpotlightStyle((prev) => ({ ...prev, opacity: 0 }));
    onHoverItem?.(null);
  }, [onHoverItem]);

  // Update spotlight position on window resize
  useEffect(() => {
    const handleResize = () => {
      if (!isHovering) return;
      // Recalculate if actively hovering
      setSpotlightStyle((prev) => ({ ...prev, opacity: 0 }));
      setIsHovering(false);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [isHovering]);

  return (
    <div
      ref={navRef}
      className={cn(
        "relative inline-flex items-center gap-1 rounded-2xl p-2",
        "border border-white/[0.08]",
        "bg-white/[0.04]",
        "backdrop-blur-xl",
        "shadow-[0_8px_32px_rgba(0,0,0,0.4),inset_0_1px_0_rgba(255,255,255,0.06)]",
        className
      )}
      onMouseLeave={handleMouseLeave}
    >
      {/* Spotlight indicator */}
      <div
        className="absolute top-2 left-0 z-0 rounded-xl pointer-events-none"
        style={{
          ...spotlightStyle,
          transition: isHovering
            ? "transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), width 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), opacity 0.2s ease"
            : "opacity 0.25s ease",
          background:
            "radial-gradient(ellipse at center, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.04) 70%, transparent 100%)",
          boxShadow:
            "0 0 20px rgba(255,255,255,0.06), inset 0 1px 0 rgba(255,255,255,0.1), inset 0 -1px 0 rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.1)",
        }}
      />

      {/* Glow effect behind spotlight */}
      <div
        className="absolute top-2 left-0 z-0 rounded-xl pointer-events-none blur-xl"
        style={{
          ...spotlightStyle,
          transition: isHovering
            ? "transform 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94), width 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94), opacity 0.25s ease"
            : "opacity 0.3s ease",
          background:
            "radial-gradient(ellipse at center, rgba(255,255,255,0.08) 0%, transparent 70%)",
        }}
      />

      {/* Nav items */}
      {items.map((item) => (
        <button
          key={item.id}
          ref={(el) => {
            if (el) itemRefs.current.set(item.id, el);
          }}
          className={cn(
            "relative z-10 flex flex-col items-center justify-center",
            "w-[72px] h-[72px] rounded-xl",
            "cursor-pointer select-none",
            "transition-all duration-300 ease-out",
            "text-white/50 hover:text-white",
            "group"
          )}
          onMouseEnter={(e) =>
            handleMouseEnter(item, e.currentTarget as HTMLButtonElement)
          }
          onClick={(e) => {
            e.stopPropagation();
            item.onClick?.();
          }}
          title={item.label}
        >
          {/* Icon */}
          <div className="transition-transform duration-300 ease-out group-hover:scale-110">
            {item.icon}
          </div>

          {/* Tooltip label that appears on hover */}
          <span
            className={cn(
              "absolute -bottom-8 left-1/2 -translate-x-1/2",
              "text-[0.65rem] font-medium tracking-wide text-white/70",
              "whitespace-nowrap",
              "opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0",
              "transition-all duration-200 ease-out",
              "pointer-events-none"
            )}
            style={{ fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif" }}
          >
            {item.label}
          </span>
        </button>
      ))}
    </div>
  );
}

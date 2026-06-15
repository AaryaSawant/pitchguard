import React, { useRef, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { initSharedShader, sharedCanvas, activeSharedCards } from "./shared-shader";

interface LiquidMetalCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  borderRadius?: number;
  interactive?: boolean;
  onClick?: () => void;
}

export const LiquidMetalCard: React.FC<LiquidMetalCardProps> = ({
  children,
  borderRadius = 16,
  interactive = false,
  className,
  onClick,
  style,
  ...props
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    initSharedShader();

    const canvas = canvasRef.current;
    if (!canvas) return;

    const updateSize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
    };

    updateSize();

    const resizeObserver = new ResizeObserver(() => {
      updateSize();
    });
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    const draw = () => {
      if (!canvas || !sharedCanvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(sharedCanvas, 0, 0, canvas.width, canvas.height);
    };

    activeSharedCards.add(draw);

    return () => {
      activeSharedCards.delete(draw);
      resizeObserver.disconnect();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      onClick={onClick}
      onMouseEnter={() => interactive && setIsHovered(true)}
      onMouseLeave={() => interactive && setIsHovered(false)}
      className={cn(
        "relative overflow-hidden transition-all duration-500",
        interactive && "cursor-pointer hover:shadow-[0_0_30px_rgba(255,255,255,0.08)]",
        className
      )}
      style={{
        borderRadius: borderRadius !== undefined ? `${borderRadius}px` : undefined,
        border: "1px solid rgba(255, 255, 255, 0.08)",
        ...style,
      }}
      {...props}
    >
      {/* Liquid Metal Canvas Background */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none z-0"
        style={{
          opacity: isHovered ? 0.35 : 0.2,
          mixBlendMode: "screen",
          transition: "opacity 0.5s ease",
        }}
      />

      {/* Dark overlay for readability and premium feel */}
      <div
        className="absolute inset-0 z-10 pointer-events-none transition-colors duration-500"
        style={{
          background: isHovered
            ? "radial-gradient(circle at center, rgba(13, 20, 35, 0.75) 0%, rgba(5, 8, 16, 0.85) 100%)"
            : "radial-gradient(circle at center, rgba(10, 15, 30, 0.85) 0%, rgba(3, 5, 10, 0.95) 100%)",
        }}
      />

      {/* Border glow */}
      <div
        className="absolute inset-0 z-20 pointer-events-none rounded-[inherit] transition-opacity duration-500"
        style={{
          boxShadow: isHovered
            ? "inset 0 0 15px rgba(255, 255, 255, 0.15), inset 0 0 0 1px rgba(255, 255, 255, 0.2)"
            : "inset 0 0 5px rgba(255, 255, 255, 0.05), inset 0 0 0 1px rgba(255, 255, 255, 0.05)",
          opacity: 1,
        }}
      />

      {/* Content */}
      <div className="relative z-30 w-full h-full">{children}</div>
    </div>
  );
};

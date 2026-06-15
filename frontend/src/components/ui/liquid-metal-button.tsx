import React, { useRef, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { initSharedShader, sharedCanvas, activeSharedCards } from "./shared-shader";
import { X, MoreHorizontal } from "lucide-react";

interface LiquidMetalButtonProps {
  label?: string;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  viewMode?: "icon" | "normal";
  className?: string;
}

export const LiquidMetalButton: React.FC<LiquidMetalButtonProps> = ({
  label,
  onClick,
  viewMode = "normal",
  className,
}) => {
  const buttonRef = useRef<HTMLButtonElement>(null);
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
    if (buttonRef.current) {
      resizeObserver.observe(buttonRef.current);
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

  const isCloseButton =
    onClick &&
    (onClick.name === "onClose" ||
      onClick.name === "handleClose" ||
      onClick.toString().includes("null") ||
      onClick.toString().includes("close"));

  return (
    <button
      ref={buttonRef}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn(
        "relative overflow-hidden font-bold transition-all duration-300 active:scale-95 cursor-pointer flex items-center justify-center group",
        viewMode === "icon"
          ? "w-10 h-10 rounded-full p-0"
          : "px-5 py-2.5 rounded-lg text-sm tracking-wide",
        className
      )}
      style={{
        border: isHovered ? "1px solid rgba(255, 255, 255, 0.4)" : "1px solid rgba(255, 255, 255, 0.15)",
        background: isHovered ? "rgba(255, 255, 255, 0.08)" : "rgba(255, 255, 255, 0.02)",
        color: isHovered ? "#ffffff" : "#e2e8f0",
        fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif",
        boxShadow: isHovered ? "0 0 15px rgba(255, 255, 255, 0.05)" : "none",
      }}
    >
      {/* Liquid Metal Canvas Background */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none z-0"
        style={{
          opacity: isHovered ? 0.45 : 0.15,
          mixBlendMode: "screen",
          transition: "opacity 0.3s ease",
        }}
      />

      {/* Content */}
      <span className="relative z-10 flex items-center justify-center">
        {viewMode === "icon" ? (
          isCloseButton ? (
            <X size={16} className="text-gray-300 group-hover:text-white" />
          ) : (
            <MoreHorizontal size={16} className="text-gray-300 group-hover:text-white" />
          )
        ) : (
          label
        )}
      </span>
    </button>
  );
};

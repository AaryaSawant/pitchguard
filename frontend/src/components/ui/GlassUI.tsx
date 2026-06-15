import React from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface GlassEffectProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  href?: string;
  target?: string;
  onClick?: () => void;
}

export interface DockItem {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}

// ─── SVG Filter (rendered once) ──────────────────────────────────────────────

export const GlassFilter: React.FC = () => (
  <svg style={{ display: "none" }}>
    <filter
      id="glass-distortion"
      x="0%"
      y="0%"
      width="100%"
      height="100%"
      filterUnits="objectBoundingBox"
    >
      <feTurbulence
        type="fractalNoise"
        baseFrequency="0.001 0.005"
        numOctaves={1}
        seed={17}
        result="turbulence"
      />
      <feComponentTransfer in="turbulence" result="mapped">
        <feFuncR type="gamma" amplitude={1} exponent={10} offset={0.5} />
        <feFuncG type="gamma" amplitude={0} exponent={1} offset={0} />
        <feFuncB type="gamma" amplitude={0} exponent={1} offset={0.5} />
      </feComponentTransfer>
      <feGaussianBlur in="turbulence" stdDeviation={3} result="softMap" />
      <feSpecularLighting
        in="softMap"
        surfaceScale={5}
        specularConstant={1}
        specularExponent={100}
        lightingColor="white"
        result="specLight"
      >
        <fePointLight x={-200} y={-200} z={300} />
      </feSpecularLighting>
      <feComposite
        in="specLight"
        operator="arithmetic"
        k1={0}
        k2={1}
        k3={1}
        k4={0}
        result="litImage"
      />
      <feDisplacementMap
        in="SourceGraphic"
        in2="softMap"
        scale={200}
        xChannelSelector="R"
        yChannelSelector="G"
      />
    </filter>
  </svg>
);

// ─── Base Glass Effect Wrapper ───────────────────────────────────────────────
// Matches the reference "Liquid Glass" design exactly:
// - Backdrop blur for frosted effect
// - SVG distortion filter for refraction
// - Very subtle white tint (background shows through)
// - Inner specular highlight borders

export const GlassEffect: React.FC<GlassEffectProps> = ({
  children,
  className = "",
  style = {},
  onClick,
}) => {
  const glassStyle: React.CSSProperties = {
    boxShadow: "0 6px 6px rgba(0, 0, 0, 0.2), 0 0 20px rgba(0, 0, 0, 0.1)",
    transitionTimingFunction: "cubic-bezier(0.175, 0.885, 0.32, 2.2)",
    ...style,
  };

  return (
    <div
      className={`relative flex font-semibold overflow-hidden text-white cursor-pointer transition-all duration-700 ${className}`}
      style={glassStyle}
      onClick={onClick}
    >
      {/* Layer 1: Backdrop blur + SVG distortion filter */}
      <div
        className="absolute inset-0 z-0 overflow-hidden rounded-[inherit] rounded-3xl"
        style={{
          backdropFilter: "blur(3px)",
          filter: "url(#glass-distortion)",
          isolation: "isolate",
        }}
      />
      {/* Layer 2: Subtle white tint — keep low opacity so background shows through */}
      <div
        className="absolute inset-0 z-10 rounded-[inherit]"
        style={{ background: "rgba(255, 255, 255, 0.25)" }}
      />
      {/* Layer 3: Inner specular highlight borders */}
      <div
        className="absolute inset-0 z-20 rounded-[inherit] rounded-3xl overflow-hidden"
        style={{
          boxShadow:
            "inset 2px 2px 1px 0 rgba(255, 255, 255, 0.5), inset -1px -1px 1px 1px rgba(255, 255, 255, 0.5)",
        }}
      />
      {/* Content */}
      <div className="relative z-30">{children}</div>
    </div>
  );
};

// ─── Dock Component ──────────────────────────────────────────────────────────

export const GlassDock: React.FC<{ items: DockItem[] }> = ({ items }) => (
  <GlassEffect className="rounded-3xl p-3 hover:p-4 hover:rounded-[2rem]">
    <div className="flex items-center justify-center gap-2 rounded-3xl p-3 py-0 px-0.5 overflow-hidden">
      {items.map((item, index) => (
        <div
          key={index}
          className="w-16 h-16 flex items-center justify-center transition-all duration-700 hover:scale-110 cursor-pointer select-none"
          style={{
            transformOrigin: "center center",
            transitionTimingFunction: "cubic-bezier(0.175, 0.885, 0.32, 2.2)",
          }}
          onClick={(e) => {
            e.stopPropagation();
            item.onClick?.();
          }}
          title={item.label}
        >
          {item.icon}
        </div>
      ))}
    </div>
  </GlassEffect>
);

// ─── Button Component ────────────────────────────────────────────────────────

export const GlassButton: React.FC<{
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}> = ({ children, onClick, className = "" }) => (
  <GlassEffect
    onClick={onClick}
    className={`rounded-3xl px-10 py-6 hover:px-11 hover:py-7 hover:rounded-[2rem] overflow-hidden ${className}`}
  >
    <div
      className="transition-all duration-700 hover:scale-95"
      style={{
        transitionTimingFunction: "cubic-bezier(0.175, 0.885, 0.32, 2.2)",
      }}
    >
      {children}
    </div>
  </GlassEffect>
);

// ─── Glass Card (for club picker) ────────────────────────────────────────────

export const GlassCard: React.FC<{
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}> = ({ children, onClick, className = "" }) => (
  <GlassEffect
    onClick={onClick}
    className={`rounded-2xl p-6 hover:p-7 hover:rounded-3xl overflow-hidden ${className}`}
  >
    <div
      className="transition-all duration-500 hover:scale-[0.97]"
      style={{
        transitionTimingFunction: "cubic-bezier(0.175, 0.885, 0.32, 2.2)",
      }}
    >
      {children}
    </div>
  </GlassEffect>
);

import { cn } from "@/lib/utils";
import { ShaderAnimation } from "./shader-lines";

export const StadiumBackground: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <div className="min-h-screen h-full font-light relative overflow-hidden w-full bg-black text-white">
    <GlassFilter />
    <div className="absolute inset-0 z-0 pointer-events-none">
      <ShaderAnimation />
    </div>
    
    <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
      <div
        aria-hidden="true"
        className={cn(
          'absolute -top-10 left-1/2 size-full -translate-x-1/2 rounded-full',
          'bg-[radial-gradient(ellipse_at_center,rgba(255,255,255,0.05),transparent_50%)]',
          'blur-[30px]',
        )}
      />
    </div>

    {/* Content Layer (must be interactive) */}
    <div className="relative z-20 w-full h-full min-h-screen flex items-center justify-center pointer-events-auto">
      {children}
    </div>
  </div>
);

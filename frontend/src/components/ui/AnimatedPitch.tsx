import { useState, useEffect } from "react";
import { GlassPanel } from "./GlassPanel";

// ── Circular Gauge ─────────────────────────────────────────────────────────
function CircularGauge({ value, label, size = 120 }: { value: number; label: string; size?: number }) {
  const [animatedValue, setAnimatedValue] = useState(0);
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (animatedValue / 100) * circumference;
  const center = size / 2;

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedValue(value), 200);
    return () => clearTimeout(timer);
  }, [value]);

  const getColor = (v: number) =>
    v < 40 ? "#22c55e" : v < 70 ? "#f59e0b" : "#ef4444";
  const color = getColor(value);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Track */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={6}
          />
          {/* Value */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={6}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{
              transition: "stroke-dashoffset 1.2s ease-out",
              filter: `drop-shadow(0 0 6px ${color}80)`,
            }}
          />
        </svg>
        {/* Center text */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center"
          style={{ fontFamily: "'Inter', sans-serif" }}
        >
          <span
            className="font-bold leading-none"
            style={{ fontSize: size * 0.28, color }}
          >
            {value}%
          </span>
        </div>
      </div>
      <span
        className="text-[0.6rem] tracking-[0.15em] uppercase font-semibold"
        style={{ color: "var(--color-muted-foreground)" }}
      >
        {label}
      </span>
    </div>
  );
}

// ── Dot Risk Scatter ───────────────────────────────────────────────────────
function DotRiskScatter() {
  const dots = [
    { x: 20, y: 30, color: "#22c55e", size: 6 },
    { x: 45, y: 55, color: "#f59e0b", size: 7 },
    { x: 70, y: 25, color: "#ef4444", size: 8, pulse: true },
    { x: 35, y: 70, color: "#22c55e", size: 5 },
    { x: 60, y: 45, color: "#f59e0b", size: 6, pulse: true },
    { x: 80, y: 65, color: "#ef4444", size: 7 },
    { x: 25, y: 50, color: "#22c55e", size: 5 },
    { x: 50, y: 80, color: "#f59e0b", size: 6 },
    { x: 15, y: 75, color: "#22c55e", size: 5 },
    { x: 75, y: 40, color: "#ef4444", size: 6, pulse: true },
    { x: 40, y: 35, color: "#f59e0b", size: 5 },
    { x: 55, y: 60, color: "#22c55e", size: 6 },
    { x: 85, y: 30, color: "#ef4444", size: 7 },
    { x: 30, y: 85, color: "#22c55e", size: 5 },
    { x: 65, y: 70, color: "#f59e0b", size: 6 },
  ];

  return (
    <div className="relative w-full" style={{ height: 140 }}>
      {/* Grid lines */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(52, 211, 153,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(52, 211, 153,0.05) 1px, transparent 1px)",
          backgroundSize: "20% 20%",
        }}
      />
      {/* Dots */}
      {dots.map((dot, i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            left: `${dot.x}%`,
            top: `${dot.y}%`,
            width: dot.size,
            height: dot.size,
            backgroundColor: dot.color,
            boxShadow: `0 0 ${dot.pulse ? 8 : 3}px ${dot.color}60`,
            animation: dot.pulse ? "dotPulse 3s ease-in-out infinite" : undefined,
            animationDelay: `${i * 0.3}s`,
            transition: "all 0.3s ease",
          }}
        />
      ))}
      {/* Axis labels */}
      <span
        className="absolute bottom-0 left-0 text-[0.5rem]"
        style={{ color: "var(--color-muted)" }}
      >
        Low
      </span>
      <span
        className="absolute bottom-0 right-0 text-[0.5rem]"
        style={{ color: "var(--color-muted)" }}
      >
        High
      </span>
    </div>
  );
}

// ── Risk Stats Row ─────────────────────────────────────────────────────────
function RiskStat({
  value,
  label,
  color,
  suffix,
}: {
  value: string;
  label: string;
  color: string;
  suffix?: string;
}) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="text-xl font-bold" style={{ color, fontFamily: "'Inter', sans-serif" }}>
        {value}
      </span>
      {suffix && (
        <span className="text-sm font-semibold" style={{ color: `${color}aa` }}>
          {suffix}
        </span>
      )}
      <span
        className="text-[0.6rem] ml-1"
        style={{ color: "var(--color-muted-foreground)" }}
      >
        {label}
      </span>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────
export function AnimatedPitch() {
  const avgRisk = 60;
  return (
    <div className="relative w-full max-w-[400px] flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{
              background: "#34d399",
              boxShadow: "0 0 8px rgba(52, 211, 153, 0.6)",
              animation: "pulseGreen 2s ease-in-out infinite",
            }}
          />
          <span
            className="text-[0.7rem] font-bold tracking-[0.15em] uppercase"
            style={{ color: "var(--color-accent)" }}
          >
            Live Telemetry
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            className="w-6 h-6 rounded-md flex items-center justify-center text-xs border transition-colors"
            style={{
              borderColor: "var(--glass-border)",
              color: "var(--color-muted-foreground)",
              background: "transparent",
            }}
          >
            ‹
          </button>
          <button
            className="w-6 h-6 rounded-md flex items-center justify-center text-xs border transition-colors"
            style={{
              borderColor: "var(--glass-border)",
              color: "var(--color-muted-foreground)",
              background: "transparent",
            }}
          >
            ›
          </button>
        </div>
      </div>

      {/* Gauge panel */}
      <GlassPanel corners animationDelay={200}>
        <div className="flex items-center justify-around py-2">
          <CircularGauge value={avgRisk} label="Squad Average" size={130} />
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-risk-high" />
              <span className="text-xs" style={{ color: "var(--color-muted-foreground)" }}>
                3 High Risk
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-risk-medium" />
              <span className="text-xs" style={{ color: "var(--color-muted-foreground)" }}>
                5 Medium
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-risk-low" />
              <span className="text-xs" style={{ color: "var(--color-muted-foreground)" }}>
                10 Low Risk
              </span>
            </div>
          </div>
        </div>
      </GlassPanel>

      {/* Dot Risk panel */}
      <GlassPanel corners animationDelay={400}>
        <div className="flex items-center justify-between mb-3">
          <span
            className="text-[0.65rem] font-bold tracking-[0.12em] uppercase"
            style={{ color: "var(--color-muted-foreground)" }}
          >
            Dot Risk
          </span>
          <div className="flex items-center gap-3">
            <RiskStat value="39%" label="" color="#f59e0b" />
            <RiskStat value="355%" label="Downgrade" color="#ef4444" />
          </div>
        </div>
        <DotRiskScatter />
      </GlassPanel>

      {/* Risk donuts */}
      <div className="flex gap-4">
        <GlassPanel className="flex-1" animationDelay={600}>
          <div className="flex items-center gap-3">
            <CircularGauge value={49} label="" size={60} />
            <div>
              <span
                className="text-[0.6rem] block uppercase tracking-wider font-semibold"
                style={{ color: "var(--color-muted-foreground)" }}
              >
                Playability
              </span>
              <span className="text-sm font-bold text-[#f59e0b]">At Risk</span>
            </div>
          </div>
        </GlassPanel>
        <GlassPanel className="flex-1" animationDelay={700}>
          <div className="flex items-center gap-3">
            <CircularGauge value={53} label="" size={60} />
            <div>
              <span
                className="text-[0.6rem] block uppercase tracking-wider font-semibold"
                style={{ color: "var(--color-muted-foreground)" }}
              >
                Fitness
              </span>
              <span className="text-sm font-bold text-[#22c55e]">Moderate</span>
            </div>
          </div>
        </GlassPanel>
      </div>
    </div>
  );
}

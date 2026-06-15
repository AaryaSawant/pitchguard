import { useEffect, useState, useRef } from "react"
import { ShaderAnimation } from "@/components/ui/shader-animation"

interface SplashScreenProps {
  onComplete: () => void
  duration?: number
}

export default function SplashScreen({ onComplete, duration = 5000 }: SplashScreenProps) {
  const [phase, setPhase] = useState<"visible" | "exiting" | "done">("visible")
  const hasTriggered = useRef(false)

  useEffect(() => {
    // After `duration` ms, begin the exit animation
    const timer = setTimeout(() => {
      setPhase("exiting")
    }, duration)

    return () => clearTimeout(timer)
  }, [duration])

  useEffect(() => {
    if (phase === "exiting" && !hasTriggered.current) {
      hasTriggered.current = true
      // Wait for exit animation to finish, then notify parent
      const exitTimer = setTimeout(() => {
        setPhase("done")
        onComplete()
      }, 1000) // matches CSS transition duration
      return () => clearTimeout(exitTimer)
    }
  }, [phase, onComplete])

  if (phase === "done") return null

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center"
      style={{
        opacity: phase === "exiting" ? 0 : 1,
        transform: phase === "exiting" ? "translateY(-100%)" : "translateY(0)",
        transition: "opacity 0.8s ease, transform 1s ease",
      }}
    >
      {/* Shader background */}
      <ShaderAnimation />

      {/* Overlaid content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10">
        {/* Main title */}
        <h1
          className="text-7xl md:text-8xl lg:text-9xl font-extrabold tracking-tighter text-white text-center"
          style={{
            fontFamily: "'Syne', sans-serif",
            textShadow: "0 0 60px rgba(14, 165, 233, 0.4), 0 0 120px rgba(14, 165, 233, 0.15)",
            animation: "fadeInUp 1.2s ease-out forwards",
          }}
        >
          PitchGuard
        </h1>

        {/* Subtitle */}
        <p
          className="mt-4 text-base md:text-lg tracking-widest uppercase text-white/60"
          style={{
            fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif",
            animation: "fadeInUp 1.2s ease-out 0.4s forwards",
            opacity: 0,
          }}
        >
          Injury Risk Intelligence
        </p>

        {/* Scroll indicator */}
        <div
          className="absolute bottom-12 flex flex-col items-center gap-2"
          style={{
            animation: "fadeInUp 1.2s ease-out 1.5s forwards, bounce 2s ease-in-out 2.5s infinite",
            opacity: 0,
          }}
        >
          <span
            className="text-xs tracking-[0.2em] uppercase text-white/40"
            style={{ fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, sans-serif" }}
          >
            Loading Dashboard
          </span>
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-white/30"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </div>

      {/* Keyframe animations */}
      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(8px); }
        }
      `}</style>
    </div>
  )
}

import { useEffect, useRef, useState, useCallback } from "react";

interface SplashScreenProps {
  onComplete: () => void;
}

// Frame ranges per section
const SECTIONS = [
  {
    id: "hero",
    start: 1, end: 22,
    tag: null,
    headline: ["The ground", "beneath them", "is never", "neutral."],
    body: "Every pitch has a memory. PitchGuard reads it.",
    align: "left",
    accentStat: null,
  },
  {
    id: "surface",
    start: 23, end: 42,
    tag: "The Unseen Risk",
    headline: ["They train.", "They prepare.", "The surface", "decides."],
    body: "Artificial turf. Waterlogged grass. A pitch shared with an NFL franchise. The variables clubs ignore are the ones that end seasons.",
    align: "right",
    accentStat: { number: "40%", label: "of non-contact injuries linked to surface variables" },
  },
  {
    id: "grass",
    start: 43, end: 61,
    tag: null,
    headline: ["Every blade", "of grass", "is a variable", "they ignore."],
    body: "Compaction. Moisture. Fibre length. What looks like a pitch is a minefield of microscopic risk — untracked, unmonitored, unseen.",
    align: "left",
    accentStat: null,
  },
  {
    id: "acl",
    start: 62, end: 81,
    tag: "London · Madrid · Turin · 2024–25",
    headline: ["Van Dijk.", "Maddison.", "Carvajal.", "The list grows."],
    body: "Virgil van Dijk. James Maddison. Dani Carvajal. Xavi Simons. Rodrigo. Each injury — a career-defining moment. Each surface — a silent accomplice.",
    align: "right",
    accentStat: { number: "6+", label: "first-team ACL and ligament injuries across Europe's elite, one autumn" },
  },
  {
    id: "header",
    start: 82, end: 98,
    tag: "The Dataset",
    headline: ["16,088", "moments", "before it", "went wrong."],
    body: "Every injury event. Every surface report. Every match minute. Across 100 clubs, 5 leagues, 8 seasons. This is what pattern recognition looks like at scale.",
    align: "left",
    accentStat: { number: "100", label: "clubs tracked across Europe's top five leagues" },
  },
  {
    id: "celebration",
    start: 99, end: 116,
    tag: "The Intelligence",
    headline: ["Your squad.", "Their history.", "One number", "that matters."],
    body: "XGBoost trained on 20 physiological and environmental features. Not a generic risk model — a player-specific, surface-aware score. Explained, not just predicted.",
    align: "right",
    accentStat: null,
  },
  {
    id: "cta",
    start: 116, end: 129,
    tag: null,
    headline: ["Know before", "they step", "onto it."],
    body: "Select your league. See your squad's risk profile.",
    align: "center",
    accentStat: null,
    isCta: true,
  },
] as const;

type SectionType = typeof SECTIONS[number];

const TOTAL_FRAMES = 129;
const SCROLL_HEIGHT = 700; // vh units total scroll

function padFrame(n: number): string {
  return `ezgif-frame-${String(n).padStart(3, "0")}.jpg`;
}

export default function SplashScreen({ onComplete }: SplashScreenProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const imagesRef = useRef<HTMLImageElement[]>([]);
  const [currentFrame, setCurrentFrame] = useState(1);
  const [loadedCount, setLoadedCount] = useState(0);
  const [activeSection, setActiveSection] = useState(0);
  const [revealedSections, setRevealedSections] = useState<Set<number>>(new Set([0]));
  const [exiting, setExiting] = useState(false);
  const rafRef = useRef<number | undefined>(undefined);
  const lastFrameRef = useRef(1);

  // Preload all frames
  useEffect(() => {
    const imgs: HTMLImageElement[] = [];
    let loaded = 0;
    for (let i = 1; i <= TOTAL_FRAMES; i++) {
      const img = new Image();
      img.src = `/src/assets/pitchguardimages/${padFrame(i)}`;
      img.onload = () => {
        loaded++;
        setLoadedCount(loaded);
      };
      img.onerror = () => {
        loaded++; 
        setLoadedCount(loaded); // Forces the progress bar forward even if an image is missing
      };
      imgs.push(img);
    }
    imagesRef.current = imgs;
  }, []);

  // Draw frame to canvas
  const drawFrame = useCallback((frameIndex: number) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const img = imagesRef.current[frameIndex - 1];
    if (!canvas || !ctx || !img?.complete) return;

    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";

    const dpr = window.devicePixelRatio || 1;
    // Logical size (CSS pixels)
    const cw = canvas.width / dpr;
    const ch = canvas.height / dpr;
    const iw = img.naturalWidth;
    const ih = img.naturalHeight;

    // Cover fit in logical pixels
    const scale = Math.max(cw / iw, ch / ih);
    const dw = iw * scale;
    const dh = ih * scale;
    const dx = (cw - dw) / 2;
    const dy = (ch - dh) / 2;

    ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr);
    ctx.drawImage(img, dx, dy, dw, dh);
  }, []);

  // Resize canvas to viewport — DPR-aware for sharp rendering
  useEffect(() => {
    const resize = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      // Physical pixels
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      // CSS size stays viewport-sized
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      // Scale context so all draws use logical pixels
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.scale(dpr, dpr);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
      }
      drawFrame(lastFrameRef.current);
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [drawFrame]);

  // Scroll handler
  useEffect(() => {
    const handleScroll = () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const scrollY = window.scrollY;
        const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
        const progress = Math.min(scrollY / maxScroll, 1);

        // Map scroll progress to frame
        const frameIndex = Math.max(1, Math.min(TOTAL_FRAMES, Math.round(progress * (TOTAL_FRAMES - 1)) + 1));
        if (frameIndex !== lastFrameRef.current) {
          lastFrameRef.current = frameIndex;
          setCurrentFrame(frameIndex);
          drawFrame(frameIndex);
        }

        // Detect active section
        const sectionIndex = SECTIONS.findIndex((s, i) => {
          const next = SECTIONS[i + 1];
          const sProgress = (s.start - 1) / (TOTAL_FRAMES - 1);
          const eProgress = next ? (next.start - 1) / (TOTAL_FRAMES - 1) : 1;
          return progress >= sProgress && progress < eProgress;
        });
        const idx = sectionIndex === -1 ? SECTIONS.length - 1 : sectionIndex;
        setActiveSection(idx);
        setRevealedSections(prev => new Set([...prev, idx]));
      });
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", handleScroll);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [drawFrame]);

  // Draw initial frame when loaded
  useEffect(() => {
    if (loadedCount >= 1) drawFrame(1);
  }, [loadedCount, drawFrame]);

  const handleEnter = () => {
    setExiting(true);
    setTimeout(onComplete, 900);
  };

  const loadProgress = loadedCount / TOTAL_FRAMES;
  const isLoaded = loadedCount >= TOTAL_FRAMES;

  return (
    <>
      {/* Scroll spacer — creates scroll height */}
      <div style={{ height: `${SCROLL_HEIGHT}vh`, position: "relative" }}>

        {/* Sticky canvas wrapper */}
        <div
          ref={containerRef}
          style={{
            position: "sticky",
            top: 0,
            height: "100vh",
            width: "100vw",
            overflow: "hidden",
            background: "#040a05",
          }}
        >
          {/* Canvas */}
          <canvas
            ref={canvasRef}
            style={{
              position: "absolute", inset: 0,
              width: "100%", height: "100%",
              opacity: exiting ? 0 : 1,
              transition: "opacity 0.9s ease",
            }}
          />

          {/* Dark vignette overlay */}
          <div style={{
            position: "absolute", inset: 0, pointerEvents: "none",
            background: "radial-gradient(ellipse at center, transparent 35%, rgba(4,10,5,0.75) 100%)",
          }} />

          {/* Bottom gradient for text readability */}
          <div style={{
            position: "absolute", bottom: 0, left: 0, right: 0,
            height: "45%", pointerEvents: "none",
            background: "linear-gradient(to top, rgba(4,10,5,0.92) 0%, transparent 100%)",
          }} />

          {/* Top gradient */}
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0,
            height: "20%", pointerEvents: "none",
            background: "linear-gradient(to bottom, rgba(4,10,5,0.7) 0%, transparent 100%)",
          }} />

          {/* Loading screen */}
          {!isLoaded && (
            <div style={{
              position: "absolute", inset: 0, zIndex: 200,
              background: "#040a05",
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", gap: 24,
            }}>
              <p style={{ fontSize: "0.6rem", letterSpacing: "0.4em", color: "rgba(74,222,128,0.6)", textTransform: "uppercase", fontFamily: "'Satoshi', sans-serif" }}>
                PitchGuard
              </p>
              <div style={{ width: 180, height: 1, background: "rgba(74,222,128,0.15)", position: "relative" }}>
                <div style={{
                  position: "absolute", left: 0, top: 0, height: "100%",
                  width: `${loadProgress * 100}%`,
                  background: "#4ade80",
                  transition: "width 0.2s ease",
                }} />
              </div>
              <p style={{ fontSize: "0.52rem", letterSpacing: "0.3em", color: "rgba(255,255,255,0.25)", textTransform: "uppercase", fontFamily: "'Satoshi', sans-serif" }}>
                {Math.round(loadProgress * 100)}%
              </p>
            </div>
          )}

          {/* PitchGuard wordmark */}
          <div style={{
            position: "absolute", top: 28, left: 36, zIndex: 50,
            opacity: isLoaded ? 1 : 0, transition: "opacity 0.5s ease 0.5s",
          }}>
            <span style={{ fontSize: "0.62rem", letterSpacing: "0.32em", textTransform: "uppercase", color: "rgba(74,222,128,0.65)", fontWeight: 700, fontFamily: "'Bricolage Grotesque', sans-serif" }}>
              PitchGuard
            </span>
          </div>

          {/* Section text overlays */}
          {SECTIONS.map((section, i) => {
            const isActive = activeSection === i;
            const wasRevealed = revealedSections.has(i);
            const isCta = "isCta" in section && section.isCta;
            const align = section.align;

            return (
              <div
                key={section.id}
                style={{
                  position: "absolute", inset: 0, zIndex: 10,
                  display: "flex", alignItems: "center",
                  justifyContent: align === "right" ? "flex-end" : align === "center" ? "center" : "flex-start",
                  padding: isCta ? "0" : "0 6vw",
                  opacity: isActive ? 1 : 0,
                  transition: "opacity 0.6s cubic-bezier(0.25,0.46,0.45,0.94)",
                  pointerEvents: isActive ? "auto" : "none",
                }}
              >
                {isCta ? (
                  // CTA — centered full overlay
                  <div style={{
                    textAlign: "center", maxWidth: 800, padding: "0 8vw",
                    opacity: wasRevealed ? 1 : 0,
                    transform: wasRevealed ? "translateY(0)" : "translateY(32px)",
                    transition: "opacity 0.9s ease 0.1s, transform 0.9s ease 0.1s",
                  }}>
                    <p style={{ fontSize: "0.58rem", letterSpacing: "0.42em", color: "rgba(74,222,128,0.55)", marginBottom: 36, textTransform: "uppercase", fontFamily: "'Satoshi', sans-serif" }}>
                      PitchGuard — Injury Risk Intelligence
                    </p>
                    <h2 style={{
                      fontSize: "clamp(4rem, 10vw, 8.5rem)", fontWeight: 800,
                      lineHeight: 0.93, letterSpacing: "-0.038em",
                      color: "#e8f5ea", whiteSpace: "pre-line", marginBottom: 32,
                      fontFamily: "'Bricolage Grotesque', sans-serif",
                    }}>
                      {section.headline.join("\n")}
                    </h2>
                    <div style={{ width: 52, height: 1, background: "rgba(74,222,128,0.35)", margin: "0 auto 32px" }} />
                    <p style={{ fontSize: "1rem", color: "rgba(200,235,205,0.7)", lineHeight: 1.75, fontFamily: "'Satoshi', sans-serif", maxWidth: 400, margin: "0 auto 56px" }}>
                      {section.body}
                    </p>
                    <button
                      onClick={handleEnter}
                      style={{
                        padding: "20px 62px", background: "#4ade80", color: "#040a05",
                        border: "none", borderRadius: 3, fontSize: "0.72rem", fontWeight: 700,
                        letterSpacing: "0.24em", textTransform: "uppercase", cursor: "pointer",
                        transition: "all 0.28s cubic-bezier(0.34,1.56,0.64,1)",
                        fontFamily: "'Satoshi', sans-serif",
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.background = "#86efac";
                        e.currentTarget.style.transform = "translateY(-4px) scale(1.03)";
                        e.currentTarget.style.boxShadow = "0 14px 44px rgba(74,222,128,0.3)";
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.background = "#4ade80";
                        e.currentTarget.style.transform = "translateY(0) scale(1)";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    >
                      Select your league →
                    </button>
                  </div>
                ) : (
                  // Editorial text block
                  <div style={{
                    maxWidth: 520,
                    opacity: wasRevealed ? 1 : 0,
                    transform: wasRevealed ? "translateY(0)" : "translateY(28px)",
                    transition: "opacity 0.8s ease 0.05s, transform 0.8s cubic-bezier(0.25,0.46,0.45,0.94) 0.05s",
                  }}>
                    {section.tag && (
                      <p style={{
                        fontSize: "0.58rem", letterSpacing: "0.36em", textTransform: "uppercase",
                        color: "#4ade80", fontWeight: 700, marginBottom: 28, opacity: 0.85,
                        fontFamily: "'Satoshi', sans-serif",
                        animation: isActive ? "tagIn 0.6s ease forwards" : "none",
                      }}>
                        — {section.tag}
                      </p>
                    )}
                    <h2 style={{
                      fontSize: "clamp(2.8rem, 5vw, 5rem)", fontWeight: 800,
                      lineHeight: 1.02, letterSpacing: "-0.032em",
                      color: "#e8f5ea", marginBottom: 28,
                      fontFamily: "'Bricolage Grotesque', sans-serif",
                    }}>
                      {section.headline.map((line, li) => (
                        <span key={li} style={{ display: "block", overflow: "hidden" }}>
                          {line.split(" ").map((word, wi) => (
                            <span
                              key={wi}
                              style={{
                                display: "inline-block",
                                marginRight: "0.24em",
                                opacity: 0,
                                animation: wasRevealed
                                  ? `wordDrop 0.65s cubic-bezier(0.22,1,0.36,1) ${(li * 3 + wi) * 0.07 + 0.08}s forwards`
                                  : "none",
                              }}
                            >
                              {word}
                            </span>
                          ))}
                        </span>
                      ))}
                    </h2>
                    <div style={{
                      height: 1, background: "#4ade80", marginBottom: 24, opacity: 0.4025,
                      width: 0,
                      animation: wasRevealed ? "ruleGrow 0.5s ease 0.5s forwards" : "none",
                    }} />
                    <p style={{
                      fontSize: "clamp(0.85rem, 1.2vw, 0.98rem)",
                      color: "rgba(200,230,205,0.7)", lineHeight: 1.8, fontWeight: 400,
                      fontFamily: "'Satoshi', sans-serif", maxWidth: 420,
                      opacity: 0,
                      animation: wasRevealed ? "fadeUp 0.7s ease 0.55s forwards" : "none",
                    }}>
                      {section.body}
                    </p>
                    {"accentStat" in section && section.accentStat && (
                      <div style={{
                        marginTop: 36, display: "flex", alignItems: "baseline", gap: 14,
                        opacity: 0,
                        animation: wasRevealed ? "statPop 0.7s cubic-bezier(0.34,1.56,0.64,1) 0.7s forwards" : "none",
                      }}>
                        <span style={{ fontSize: "clamp(2.4rem, 4.5vw, 3.8rem)", fontWeight: 800, color: "#4ade80", letterSpacing: "-0.04em", lineHeight: 1, fontFamily: "'Bricolage Grotesque', sans-serif" }}>
                          {section.accentStat.number}
                        </span>
                        <span style={{ fontSize: "0.64rem", color: "rgba(180,215,185,0.6)", maxWidth: 180, lineHeight: 1.55, fontFamily: "'Satoshi', sans-serif", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 500 }}>
                          {section.accentStat.label}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Section nav dots */}
          <div style={{
            position: "absolute", right: 24, top: "50%", transform: "translateY(-50%)",
            display: "flex", flexDirection: "column", gap: 10, zIndex: 50,
          }}>
            {SECTIONS.map((_, i) => (
              <div
                key={i}
                style={{
                  width: activeSection === i ? 3 : 2,
                  height: activeSection === i ? 30 : 8,
                  borderRadius: 2,
                  background: activeSection === i ? "#4ade80" : "rgba(74,222,128,0.2)",
                  transition: "all 0.4s cubic-bezier(0.34,1.56,0.64,1)",
                  cursor: "pointer",
                }}
              />
            ))}
          </div>

          {/* Scroll nudge */}
          <div style={{
            position: "absolute", bottom: 32, left: "50%", transform: "translateX(-50%)",
            opacity: activeSection === 0 && isLoaded ? 1 : 0,
            transition: "opacity 0.6s ease",
            pointerEvents: "none", zIndex: 50,
            display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
          }}>
            <span style={{ fontSize: "0.52rem", letterSpacing: "0.4em", color: "rgba(74,222,128,0.45)", textTransform: "uppercase", fontFamily: "'Satoshi', sans-serif" }}>
              Scroll
            </span>
            <div style={{ width: 1, height: 40, background: "linear-gradient(to bottom, rgba(74,222,128,0.5), transparent)", animation: "pulse 2.2s ease-in-out infinite" }} />
          </div>

          {/* Frame counter — dev only, remove for prod */}
          {/* <div style={{ position: "absolute", bottom: 20, right: 60, color: "rgba(255,255,255,0.2)", fontSize: "0.6rem", fontFamily: "monospace", zIndex: 100 }}>
            {currentFrame}/{TOTAL_FRAMES}
          </div> */}
        </div>
      </div>

      <style>{`
        @import url('https://api.fontshare.com/v2/css?f[]=bricolage-grotesque@800,700&f[]=satoshi@400,500&display=swap');

        @keyframes wordDrop {
          from { opacity: 0; transform: translateY(-22px); filter: blur(3px); }
          to   { opacity: 1; transform: translateY(0);     filter: blur(0); }
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes tagIn {
          from { opacity: 0; transform: translateX(-10px); }
          to   { opacity: 0.8; transform: translateX(0); }
        }
        @keyframes ruleGrow {
          from { width: 0; opacity: 0; }
          to   { width: 44px; opacity: 0.35; }
        }
        @keyframes statPop {
          from { opacity: 0; transform: scale(0.88) translateY(10px); }
          to   { opacity: 1; transform: scale(1) translateY(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scaleY(0.85); }
          50%       { opacity: 1;   transform: scaleY(1.1); }
        }

        html { scroll-behavior: auto !important; }
        body { margin: 0; background: #040a05; }
      `}</style>
    </>
  );
}
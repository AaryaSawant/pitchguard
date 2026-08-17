import React, { useState, useRef, useEffect } from "react";
import { fetchClubsGrouped } from "@/lib/api";

// Club TM IDs for badge logos via Transfermarkt CDN
const CLUB_TM_ID: Record<string, string> = {
  "1. FC Heidenheim": "2036",
  "1. FC Union Berlin": "89",
  "AC Milan": "5",
  "AS Monaco": "162",
  "AS Roma": "12",
  "Angers SCO": "1023",
  "Arsenal": "11",
  "Aston Villa": "405",
  "Atalanta": "800",
  "Athletic Bilbao": "621",
  "Atletico Madrid": "13",
  "Auxerre": "69",
  "Bayer Leverkusen": "15",
  "Bayern Munich": "27",
  "Besiktas": "114",
  "Bologna": "1025",
  "Borussia Dortmund": "16",
  "Borussia Monchengladbach": "23",
  "Bournemouth": "989",
  "Brentford": "1148",
  "Brighton & Hove Albion": "1237",
  "Cagliari": "1390",
  "Celta Vigo": "940",
  "Chelsea": "631",
  "Como": "2324",
  "Crystal Palace": "873",
  "Deportivo Alaves": "1108",
  "Eintracht Frankfurt": "24",
  "Empoli": "749",
  "Espanyol": "714",
  "Everton": "29",
  "FC Augsburg": "167",
  "FC Barcelona": "131",
  "FC Nantes": "995",
  "FC St. Pauli": "35",
  "Fenerbahce": "36",
  "Fiorentina": "430",
  "Fulham": "931",
  "Galatasaray": "141",
  "Genoa": "252",
  "Getafe CF": "3709",
  "Girona FC": "12321",
  "Hellas Verona": "276",
  "Inter Milan": "46",
  "Ipswich Town": "677",
  "Juventus": "506",
  "Lazio": "398",
  "Le Havre AC": "738",
  "Lecce": "4884",
  "Leicester City": "1003",
  "Lille OSC": "1082",
  "Liverpool": "31",
  "Manchester City": "281",
  "Manchester United": "985",
  "Montpellier HSC": "969",
  "Monza": "9462",
  "Newcastle United": "762",
  "Nottingham Forest": "703",
  "OGC Nice": "417",
  "Olympique Lyonnais": "1041",
  "Olympique de Marseille": "244",
  "Osasuna": "331",
  "Paris Saint-Germain": "583",
  "Parma": "130",
  "RB Leipzig": "23826",
  "RC Lens": "826",
  "RCD Mallorca": "237",
  "Rayo Vallecano": "367",
  "Real Betis": "150",
  "Real Madrid": "418",
  "Real Sociedad": "681",
  "Real Valladolid": "366",
  "SC Freiburg": "60",
  "SSC Napoli": "6195",
  "SV Darmstadt 98": "105",
  "Saint-Etienne": "618",
  "Sevilla FC": "368",
  "Southampton": "180",
  "Stade Brestois": "3911",
  "Stade Rennais": "273",
  "Strasbourg": "667",
  "TSG Hoffenheim": "533",
  "Torino": "416",
  "Tottenham Hotspur": "148",
  "Toulouse FC": "415",
  "Trabzonspor": "449",
  "UD Las Palmas": "472",
  "Udinese": "410",
  "Valencia CF": "1049",
  "Venezia": "685",
  "VfB Stuttgart": "79",
  "VfL Bochum": "80",
  "VfL Wolfsburg": "82",
  "Villarreal CF": "383",
  "Werder Bremen": "86",
  "West Ham United": "379",
  "Wolverhampton Wanderers": "543",
};

function clubLogoUrl(club: string): string | null {
  const id = CLUB_TM_ID[club];
  if (!id) return null;

  return `https://tmssl.akamaized.net/images/wappen/normquad/${id}.png`;
}

// Fallback: deterministic color + short code
const PALETTE_HUES = [
  4, 24, 48, 96, 152, 176, 200, 224, 260, 288, 320, 340,
];

function hashString(str: string): number {
  let hash = 0;

  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }

  return Math.abs(hash);
}

function clubColor(club: string): string {
  const hue =
    PALETTE_HUES[hashString(club) % PALETTE_HUES.length];

  return `hsl(${hue}, 70%, 55%)`;
}

function clubShortCode(club: string): string {
  const words = club
    .replace(/[^a-zA-Z\s]/g, "")
    .split(/\s+/)
    .filter(Boolean);

  if (words.length >= 2) {
    return (
      words[0][0] +
      words[1][0] +
      (words[1][1] || words[0][1] || "")
    )
      .toUpperCase()
      .slice(0, 3);
  }

  return club
    .replace(/[^a-zA-Z]/g, "")
    .slice(0, 3)
    .toUpperCase();
}

interface ClubPickerProps {
  league: string;
  onSelectClub: (club: string) => void;
  onBack: () => void;
}

export default function ClubPicker({
  league,
  onSelectClub,
  onBack,
}: ClubPickerProps) {
  const [clubs, setClubs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logoErrors, setLogoErrors] = useState<Record<string, boolean>>(
    {}
  );

  const carouselRef = useRef<HTMLDivElement>(null);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [clickedIdx, setClickedIdx] = useState<number | null>(null);
  const [tilts, setTilts] = useState<
    Record<number, { rx: number; ry: number }>
  >({});

  useEffect(() => {
    setLoading(true);
    setError(null);

    fetchClubsGrouped()
      .then((grouped) => setClubs(grouped[league] || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [league]);

  const handleMouseMove = (
    e: React.MouseEvent<HTMLDivElement>,
    idx: number
  ) => {
    const rect = e.currentTarget.getBoundingClientRect();

    const rx =
      (rect.height / 2 - (e.clientY - rect.top)) / 14;

    const ry =
      (e.clientX - rect.left - rect.width / 2) / 14;

    setTilts((prev) => ({
      ...prev,
      [idx]: { rx, ry },
    }));
  };

  const handleMouseLeave = (idx: number) => {
    setTilts((prev) => {
      const c = { ...prev };
      delete c[idx];
      return c;
    });

    setHoveredIdx(null);
  };

  const scroll = (dir: "left" | "right") => {
    carouselRef.current?.scrollBy({
      left: dir === "left" ? -260 : 260,
      behavior: "smooth",
    });
  };

  const handleClubClick = (club: string, idx: number) => {
    setClickedIdx(idx);

    setTimeout(() => onSelectClub(club), 400);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#040a05",
        fontFamily: "'Bricolage Grotesque', 'Inter', sans-serif",
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <video
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: 0.345,
          filter: "brightness(0.6) saturate(0.75)",
        }}
        src="/assets/vid2.mp4"
      />

      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          background:
            "radial-gradient(ellipse at center, rgba(4,10,5,0.2) 0%, rgba(4,10,5,0.88) 100%)",
        }}
      />

      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "35%",
          background:
            "linear-gradient(to bottom, rgba(4,10,5,0.95), transparent)",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "25%",
          background:
            "linear-gradient(to top, rgba(4,10,5,0.95), transparent)",
          pointerEvents: "none",
        }}
      />

      <button
        onClick={onBack}
        style={{
          position: "absolute",
          top: 28,
          left: 36,
          zIndex: 50,
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 16px",
          borderRadius: 8,
          cursor: "pointer",
          background: "rgba(0,0,0,0.4)",
          border: "1px solid rgba(74,222,128,0.2)",
          color: "rgba(232,245,234,0.7)",
          fontSize: "0.72rem",
          fontWeight: 600,
          letterSpacing: "0.05em",
          fontFamily: "'Satoshi', sans-serif",
          transition: "all 0.2s ease",
          backdropFilter: "blur(12px)",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor =
            "rgba(74,222,128,0.5)";
          e.currentTarget.style.color = "#e8f5ea";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor =
            "rgba(74,222,128,0.2)";
          e.currentTarget.style.color =
            "rgba(232,245,234,0.7)";
        }}
      >
        ← Back to Leagues
      </button>

      <div
        style={{
          position: "absolute",
          top: 28,
          right: 36,
          zIndex: 50,
        }}
      >
        <span
          style={{
            fontSize: "0.58rem",
            letterSpacing: "0.32em",
            textTransform: "uppercase",
            color: "rgba(74,222,128,0.5)",
            fontWeight: 700,
            fontFamily: "'Satoshi', sans-serif",
          }}
        >
          PitchGuard / {league}
        </span>
      </div>

      <div
        style={{
          position: "relative",
          zIndex: 10,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 40,
          width: "100%",
        }}
      >
        <div
          style={{
            textAlign: "center",
            animation: "fadeUp 0.7s ease forwards",
          }}
        >
          <p
            style={{
              fontSize: "0.58rem",
              letterSpacing: "0.38em",
              color: "rgba(74,222,128,0.55)",
              textTransform: "uppercase",
              marginBottom: 14,
              fontFamily: "'Satoshi', sans-serif",
            }}
          >
            — {league}
          </p>

          <h1
            style={{
              fontSize: "clamp(2rem, 4.5vw, 3.4rem)",
              fontWeight: 800,
              color: "#e8f5ea",
              letterSpacing: "-0.025em",
              lineHeight: 1,
            }}
          >
            Select Your Club
          </h1>

          <div
            style={{
              width: 40,
              height: 1,
              background: "rgba(74,222,128,0.4)",
              margin: "16px auto 0",
            }}
          />
        </div>

        {loading && (
          <span
            style={{
              color: "#4ade80",
              fontSize: "0.8rem",
              fontFamily: "'Satoshi', sans-serif",
              letterSpacing: "0.1em",
            }}
          >
            LOADING CLUBS...
          </span>
        )}

        {error && (
          <span
            style={{
              color: "#ef4444",
              fontSize: "0.8rem",
              fontFamily: "'Satoshi', sans-serif",
            }}
          >
            Failed to load clubs: {error}
          </span>
        )}

        {!loading && !error && clubs.length === 0 && (
          <span
            style={{
              color: "rgba(232,245,234,0.5)",
              fontSize: "0.8rem",
              fontFamily: "'Satoshi', sans-serif",
            }}
          >
            No clubs found for {league}.
          </span>
        )}

        {!loading && !error && clubs.length > 0 && (
          <div
            style={{
              position: "relative",
              width: "100%",
              display: "flex",
              alignItems: "center",
            }}
          >
            <button
              onClick={() => scroll("left")}
              style={{
                position: "absolute",
                left: 24,
                zIndex: 40,
                width: 44,
                height: 44,
                borderRadius: "50%",
                cursor: "pointer",
                background: "rgba(0,0,0,0.6)",
                border: "1px solid rgba(74,222,128,0.2)",
                color: "#4ade80",
                fontSize: "1rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backdropFilter: "blur(12px)",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor =
                  "rgba(74,222,128,0.5)";
                e.currentTarget.style.background =
                  "rgba(74,222,128,0.1)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor =
                  "rgba(74,222,128,0.2)";
                e.currentTarget.style.background =
                  "rgba(0,0,0,0.6)";
              }}
            >
              ←
            </button>

            <div
              ref={carouselRef}
              style={{
                display: "flex",
                gap: 20,
                overflowX: "auto",
                padding: "32px 80px",
                scrollSnapType: "x mandatory",
                width: "100%",
                scrollbarWidth: "none",
              }}
            >
              {clubs.map((club, idx) => {
                const isClicked = clickedIdx === idx;
                const isHovered = hoveredIdx === idx;
                const tilt = tilts[idx] || { rx: 0, ry: 0 };
                const color = clubColor(club);
                const logoUrl = clubLogoUrl(club);
                const logoFailed = logoErrors[club];

                return (
                  <div
                    key={club}
                    onClick={() => handleClubClick(club, idx)}
                    onMouseMove={(e) => {
                      handleMouseMove(e, idx);
                      setHoveredIdx(idx);
                    }}
                    onMouseLeave={() => handleMouseLeave(idx)}
                    style={{
                      flexShrink: 0,
                      width: 210,
                      height: 290,
                      scrollSnapAlign: "center",
                      cursor: "pointer",
                      borderRadius: 16,
                      position: "relative",
                      transform: isClicked
                        ? "scale(1.05)"
                        : `rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg) translateZ(0)`,
                      transformStyle: "preserve-3d",
                      transition: isClicked
                        ? "transform 0.3s ease"
                        : "transform 0.15s ease",
                      animation: `fadeUp 0.6s ease ${idx * 0.05}s both`,
                      opacity: 0,
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        borderRadius: 16,
                        background: isHovered
                          ? "rgba(8,22,14,0.8)"
                          : "rgba(5,16,9,0.6)",
                        backdropFilter: "blur(20px)",
                        border: `1px solid ${
                          isClicked || isHovered
                            ? color + "60"
                            : "rgba(74,222,128,0.12)"
                        }`,
                        boxShadow: isClicked
                          ? `0 24px 48px rgba(0,0,0,0.8), 0 0 32px ${color}30`
                          : isHovered
                          ? `0 12px 32px rgba(0,0,0,0.6), 0 0 16px ${color}20`
                          : "0 4px 20px rgba(0,0,0,0.4)",
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "space-between",
                        padding: "24px 20px",
                        overflow: "hidden",
                        transition: "all 0.25s ease",
                      }}
                    >
                      <div
                        style={{
                          position: "absolute",
                          top: 0,
                          left: 0,
                          right: 0,
                          height: 3,
                          background: `linear-gradient(90deg, ${color}, transparent)`,
                          borderRadius: "16px 16px 0 0",
                        }}
                      />

                      <div
                        style={{
                          textAlign: "center",
                          marginTop: 12,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          height: 80,
                        }}
                      >
                        {logoUrl && !logoFailed ? (
                          <img
                            src={logoUrl}
                            alt={club}
                            style={{
                              height: 72,
                              width: "auto",
                              maxWidth: 90,
                              objectFit: "contain",
                              filter: isHovered
                                ? "drop-shadow(0 0 8px rgba(255,255,255,0.3))"
                                : "none",
                              transition: "filter 0.2s ease",
                            }}
                            onError={() =>
                              setLogoErrors((prev) => ({
                                ...prev,
                                [club]: true,
                              }))
                            }
                          />
                        ) : (
                          <span
                            style={{
                              fontSize: "3.2rem",
                              fontWeight: 800,
                              letterSpacing: "-0.02em",
                              color,
                              textShadow: `0 0 20px ${color}30`,
                              lineHeight: 1,
                            }}
                          >
                            {clubShortCode(club)}
                          </span>
                        )}
                      </div>

                      <div style={{ textAlign: "center" }}>
                        <h3
                          style={{
                            fontSize: "0.95rem",
                            fontWeight: 700,
                            color: "#e8f5ea",
                            lineHeight: 1.3,
                            marginBottom: 12,
                          }}
                        >
                          {club}
                        </h3>

                        <div
                          style={{
                            width: "100%",
                            height: 1,
                            background:
                              "rgba(74,222,128,0.1)",
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <button
              onClick={() => scroll("right")}
              style={{
                position: "absolute",
                right: 24,
                zIndex: 40,
                width: 44,
                height: 44,
                borderRadius: "50%",
                cursor: "pointer",
                background: "rgba(0,0,0,0.6)",
                border: "1px solid rgba(74,222,128,0.2)",
                color: "#4ade80",
                fontSize: "1rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backdropFilter: "blur(12px)",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor =
                  "rgba(74,222,128,0.5)";
                e.currentTarget.style.background =
                  "rgba(74,222,128,0.1)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor =
                  "rgba(74,222,128,0.2)";
                e.currentTarget.style.background =
                  "rgba(0,0,0,0.6)";
              }}
            >
              →
            </button>
          </div>
        )}

        <p
          style={{
            fontSize: "0.52rem",
            letterSpacing: "0.3em",
            color: "rgba(255,255,255,0.18)",
            textTransform: "uppercase",
            fontFamily: "'Satoshi', sans-serif",
            animation: "fadeUp 0.8s ease 0.4s both",
          }}
        >
          Select squad for advanced AI prediction analysis
        </p>
      </div>

      <style>{`
        @import url('https://api.fontshare.com/v2/css?f[]=bricolage-grotesque@800,700&f[]=satoshi@400,500&display=swap');

        @keyframes fadeUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }

          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        div::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
}
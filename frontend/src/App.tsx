import { useState } from "react"
import SplashScreen from "./components/SplashScreen"
import LeagueDock from "./components/LeagueDock"
import ClubPicker from "./components/ClubPicker"
import PitchGuard from "./components/PitchGuard"
import CustomCursor from "./components/ui/CustomCursor"

type Phase = "splash" | "leagueDock" | "clubPicker" | "dashboard"

export default function App() {
  const [phase, setPhase] = useState<Phase>("splash")
  const [league, setLeague] = useState("")
  const [club, setClub] = useState("")

  const handleSplashComplete = () => setPhase("leagueDock")

  const handleSelectLeague = (l: string) => {
    setLeague(l)
    setPhase("clubPicker")
  }

  const handleSelectClub = (c: string) => {
    setClub(c)
    setPhase("dashboard")
  }

  const handleBackToLeagues = () => {
    setLeague("")
    setClub("")
    setPhase("leagueDock")
  }

  const handleBackToClubs = () => {
    setClub("")
    setPhase("clubPicker")
  }

  return (
    <>
      <link
        href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&family=Inter:wght@400;500;600;700&display=swap"
        rel="stylesheet"
      />
      <CustomCursor />

      {phase === "splash" && (
        <SplashScreen onComplete={handleSplashComplete} duration={5000} />
      )}

      {phase === "leagueDock" && (
        <div
          style={{
            animation: "phaseIn 0.6s ease-out forwards",
          }}
        >
          <LeagueDock onSelectLeague={handleSelectLeague} />
        </div>
      )}

      {phase === "clubPicker" && (
        <div
          style={{
            animation: "phaseIn 0.6s ease-out forwards",
          }}
        >
          <ClubPicker
            league={league}
            onSelectClub={handleSelectClub}
            onBack={handleBackToLeagues}
          />
        </div>
      )}

      {phase === "dashboard" && (
        <div
          style={{
            animation: "phaseIn 0.5s ease-out forwards",
          }}
        >
          <PitchGuard
            league={league}
            club={club}
            onBack={handleBackToClubs}
          />
        </div>
      )}
    </>
  )
}

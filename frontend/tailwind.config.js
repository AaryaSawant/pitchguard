/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#030d1a",
        "background-elevated": "#071525",
        foreground: "#e8f0f8",
        accent: {
          DEFAULT: "#00e87b",
          bright: "#39ff14",
          dim: "#00b862",
          glow: "rgba(0, 232, 123, 0.35)",
        },
        glass: {
          bg: "rgba(7, 21, 37, 0.5)",
          border: "rgba(0, 232, 123, 0.25)",
        },
        risk: {
          low: "#00e87b",
          medium: "#ff9500",
          high: "#ff2d55",
        },
        muted: {
          DEFAULT: "#3a5070",
          foreground: "#7a9ab8",
        },
        card: {
          DEFAULT: "#0b1e33",
          foreground: "#e8f0f8",
        },
        border: "#112240",
      },
      fontFamily: {
        sans: ["Inter", "Syne", "sans-serif"],
        mono: ["Space Mono", "monospace"],
      },
    },
  },
  plugins: [],
}

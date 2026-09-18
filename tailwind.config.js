/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cad: {
          bg: "#0b0c10",
          panel: "#12141c",
          surface: "#1a1d28",
          card: "#1e2230",
          border: "#2a2f42",
          borderLight: "#39405a",
          accent: "#7c3aed",
          accentHover: "#6d28d9",
          cyan: "#06b6d4",
          amber: "#f59e0b",
          green: "#10b981",
          red: "#ef4444",
          textMuted: "#8b949e",
          textMain: "#e6edf3",
          textHeader: "#ffffff"
        }
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      }
    },
  },
  plugins: [],
}

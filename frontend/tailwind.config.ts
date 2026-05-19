import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        // Semantic aliases on top of zinc for consistency.
        surface: {
          DEFAULT: "#0a0a0a",
          raised: "#101010",
          subtle: "#141414",
        },
        line: "#1f1f22",
        // Accents
        profit: "#4ade80",     // emerald-400
        danger:  "#f87171",    // red-400
        jit:     "#a78bfa",    // violet-400
        sandwich:"#fbbf24",    // amber-400
      },
      fontSize: {
        xs: ["11px", { lineHeight: "14px" }],
        sm: ["12.5px", { lineHeight: "16px" }],
        base: ["13.5px", { lineHeight: "18px" }],
      },
      letterSpacing: {
        tightish: "-0.01em",
      },
    },
  },
  plugins: [],
};
export default config;

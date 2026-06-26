import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "-apple-system",
          "SF Pro Text",
          "SF Pro Display",
          "system-ui",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      colors: {
        accent: {
          DEFAULT: "#0071e3",
          dark: "#0a84ff",
        },
      },
      maxWidth: {
        prose: "680px",
      },
      spacing: {
        "grid": "8px",
      },
      transitionDuration: {
        DEFAULT: "250ms",
      },
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0.25, 0.1, 0.25, 1)",
      },
    },
  },
  plugins: [],
};

export default config;

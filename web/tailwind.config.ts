import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "media",
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "-apple-system",
          "SF Pro Text",
          "SF Pro Display",
          "system-ui",
          "sans-serif",
        ],
      },
      colors: {
        accent: "#007AFF",
        "accent-dark": "#0A84FF",
      },
      spacing: {
        // 8-pt grid base multiples
        "18": "4.5rem",
        "22": "5.5rem",
      },
      maxWidth: {
        reading: "44rem",  // ~704px — constrained reading width (§16)
      },
      transitionDuration: {
        DEFAULT: "200ms",
      },
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0.0, 0.0, 0.2, 1)",
      },
    },
  },
  plugins: [],
};

export default config;

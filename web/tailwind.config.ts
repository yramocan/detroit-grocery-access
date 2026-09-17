import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#12202b",
        paper: "#eef3f6",
        mist: "#d5e0e8",
        canopy: "#1f6b4f",
        canopySoft: "#cfe6db",
        gap: "#b85a2a",
        gapSoft: "#f0d5c4",
        lake: "#2a5f7a",
        highlight: "#e8c468",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        panel: "0 18px 50px rgba(18, 32, 43, 0.12)",
      },
    },
  },
  plugins: [],
};
export default config;

import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#06A04A",
          dark: "#04863f",
          light: "#21CA73",
        },
        accent: {
          DEFAULT: "#F6A623",
          dark: "#EFA73F",
        },
        surface: "#10131a",
      },
      fontFamily: {
        sans: ["Inter", ...defaultTheme.fontFamily.sans],
      },
      boxShadow: {
        glow: "0 10px 60px rgba(42,179,184,0.25)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;

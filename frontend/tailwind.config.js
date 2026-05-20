/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        serif: ["Noto Serif KR", "serif"],
        sans: ["Noto Sans KR", "sans-serif"],
      },
      colors: {
        ink: {
          DEFAULT: "#1a1a2e",
          light: "#2d2d4a",
        },
        gold: {
          DEFAULT: "#c9a84c",
          light: "#e8cc7a",
          dark: "#9b7a2e",
        },
        cream: {
          DEFAULT: "#f5f0e8",
          dark: "#ede5d0",
        },
        verdict: {
          win: "#2d6a4f",
          lose: "#9b2335",
          draw: "#4a4a6a",
        },
      },
      animation: {
        "fade-in": "fadeIn 0.6s ease forwards",
        "slide-up": "slideUp 0.5s ease forwards",
        "gavel": "gavel 0.4s ease-in-out",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: 0 },
          to: { opacity: 1 },
        },
        slideUp: {
          from: { opacity: 0, transform: "translateY(20px)" },
          to: { opacity: 1, transform: "translateY(0)" },
        },
        gavel: {
          "0%": { transform: "rotate(0deg)" },
          "50%": { transform: "rotate(-30deg)" },
          "100%": { transform: "rotate(0deg)" },
        },
      },
    },
  },
  plugins: [],
};

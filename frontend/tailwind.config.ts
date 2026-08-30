import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{vue,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17233a",
        navy: "#183f63",
        accent: "#b44236",
      },
    },
  },
  plugins: [],
} satisfies Config;

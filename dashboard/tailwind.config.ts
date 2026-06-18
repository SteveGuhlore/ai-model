import type { Config } from "tailwindcss";

// "Studio console" direction (see DESIGN.md): near-black surfaces, one accent,
// imagery is the hero. Status colors are reserved for status only.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          950: "#0a0a0b",
          900: "#121214",
          800: "#1b1b1f",
          700: "#26262c",
        },
        accent: {
          DEFAULT: "#6366f1",
          hover: "#4f46e5",
        },
        ok: "#22c55e",
        warn: "#f59e0b",
        danger: "#ef4444",
      },
      borderRadius: { card: "10px" },
    },
  },
  plugins: [],
};

export default config;

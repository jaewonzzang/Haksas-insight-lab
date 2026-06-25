import type { Config } from "tailwindcss";

import { colors } from "./src/styles/tokens";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sogang: colors.sogangRed,
        recstrong: colors.rec강추,
        graduate: colors.graduate,
        warning: colors.warning,
      },
    },
  },
  plugins: [],
};

export default config;

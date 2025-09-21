import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
      screens: {
        "2xl": {
          max: "1535px",
        },
        largeScreen: {
          min: "1500px",
          max: "1799px",
        },
        popup: {
          min: "1070px",
        },
        scrollabledemo: {
          max: "500px",
        },
        partTwoScreen: {
          max: "1200px",
        },
        midScreen: {
          min: "1200px",
          max: "1499px",
        },
        partTwoScreenTwo: {
          max: "1000px",
        },
        macBook: {
          max: "1550px",
          min: "1250px",
        },
        macBookTwo: {
          max: "1250px",
          min: "710px",
        },
        macBookFin: {
          max: "709px",
        },
        partTwoScreenThree: {
          max: "900px",
        },
        laptop: {
          min: "1000px",
        },
        questionScreen: {
          max: "800px",
        },
        tablet: {
          min: "638px",
          max: "900px",
        },
        homeScreenOne: {
          min: "800px",
          max: "1021px",
        },
        marginOne: {
          min: "800px",
          max: "1263px",
        },
        smtablet: {
          min: "600px",
          max: "799px",
        },
        phone: {
          max: "637px",
        },
        smphone: {
          max: "575px",
        },
        registrationScreen: {
          max: "750px",
        },
        smallScreen: {
          max: "410px",
        },
        smScreen: {
          max: "991px",
        },
        regScreen: {
          min: "992px",
        },
        profileNavScreen: {
          max: "822px",
        },
        buttonScreen: {
          max: "767px",
        },
        notif: {
          max: "1082px",
          min: "901px",
        },
        almostphone: {
          max: "390px",
        },
        monitor: {
          min: "1800px",
        },
      },
      fontFamily: {
        satoshi: ["Satoshi", "sans-serif"],
        figtree: ["Figtree", "sans-serif"],
      },
      colors: {
        blackGood: "#0F172A",
        silverBord: "#5E5E5F",
        greyGood: "#E8EAEC",
        highlightCol: "#38BDF9",
        sheetsGreen: "#1FA463",
        formPurp: "#7248B9",
        youtubeRed: "#FF0000",
        darkPurple: "#7F8AF5",
        lightPurple: "#A5B4FB",
        ieeeGreen: "#27C2A0",
        lightRed: "#E55D76",
        niceBlack: "#2B2B2C",
        selectBlue: "#257AFD",
        dockerBlue: "#193655",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        chart: {
          "1": "hsl(var(--chart-1))",
          "2": "hsl(var(--chart-2))",
          "3": "hsl(var(--chart-3))",
          "4": "hsl(var(--chart-4))",
          "5": "hsl(var(--chart-5))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: {
            height: "0",
          },
          to: {
            height: "var(--radix-accordion-content-height)",
          },
        },
        "accordion-up": {
          from: {
            height: "var(--radix-accordion-content-height)",
          },
          to: {
            height: "0",
          },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
};
export default config;

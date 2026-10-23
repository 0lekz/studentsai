import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";
import typography from "@tailwindcss/typography";

const token = (name: string) => `hsl(var(--${name}) / <alpha-value>)`;

export default {
  future: {
    hoverOnlyWhenSupported: true,
  },
  darkMode: ["variant", "&:is(.dark *):not(.light *)"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: token("background"),
        foreground: token("foreground"),
        surface: {
          DEFAULT: token("surface"),
          raised: token("surface-raised"),
        },
        muted: {
          DEFAULT: token("muted"),
          foreground: token("muted-foreground"),
        },
        border: token("border"),
        input: token("input"),
        ring: token("ring"),
        primary: {
          DEFAULT: token("primary"),
          hover: token("primary-hover"),
          foreground: token("primary-foreground"),
        },
        brand: {
          DEFAULT: token("brand"),
          soft: token("brand-soft"),
          "soft-foreground": token("brand-soft-foreground"),
        },
        accent: {
          DEFAULT: token("accent"),
          foreground: token("accent-foreground"),
        },
        popover: {
          DEFAULT: token("popover"),
          foreground: token("popover-foreground"),
        },
        destructive: {
          DEFAULT: token("destructive"),
          foreground: token("destructive-foreground"),
          soft: token("destructive-soft"),
          "soft-foreground": token("destructive-soft-foreground"),
        },
        success: {
          DEFAULT: token("success"),
          soft: token("success-soft"),
          "soft-foreground": token("success-soft-foreground"),
        },
        warning: {
          DEFAULT: token("warning"),
          soft: token("warning-soft"),
          "soft-foreground": token("warning-soft-foreground"),
        },
        mastery: {
          low: token("mastery-low"),
          mid: token("mastery-mid"),
          high: token("mastery-high"),
        },
        orange: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
        },
        purple: {
          50: "#faf5ff",
          100: "#f3e8ff",
          200: "#e9d5ff",
          300: "#d8b4fe",
          400: "#c084fc",
          500: "#a855f7",
          600: "#9333ea",
          700: "#7c3aed",
          800: "#6b21a8",
          900: "#581c87",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
      },
      fontSize: {
        caption: ["var(--text-caption)", { lineHeight: "var(--text-caption-leading)" }],
        body: ["var(--text-body)", { lineHeight: "var(--text-body-leading)" }],
        "body-lg": ["var(--text-body-lg)", { lineHeight: "var(--text-body-lg-leading)" }],
        title: ["var(--text-title)", { lineHeight: "var(--text-title-leading)" }],
        headline: ["var(--text-headline)", { lineHeight: "var(--text-headline-leading)" }],
        display: ["var(--text-display)", { lineHeight: "var(--text-display-leading)" }],
      },
      spacing: {
        gutter: "var(--space-gutter)",
        section: "var(--space-section)",
        rail: "var(--rail-width)",
        topbar: "var(--topbar-height)",
        bottombar: "var(--bottombar-height)",
      },
      borderRadius: {
        control: "var(--radius-control)",
        card: "var(--radius-card)",
      },
      maxWidth: {
        content: "var(--content-max-width)",
        prose: "var(--prose-max-width)",
      },
      keyframes: {
        indeterminate: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(300%)" },
        },
      },
      animation: {
        indeterminate: "indeterminate 1.4s ease-in-out infinite",
      },
      typography: {
        app: {
          css: {
            "--tw-prose-body": "hsl(var(--foreground))",
            "--tw-prose-headings": "hsl(var(--foreground))",
            "--tw-prose-lead": "hsl(var(--muted-foreground))",
            "--tw-prose-links": "hsl(var(--primary))",
            "--tw-prose-bold": "hsl(var(--foreground))",
            "--tw-prose-counters": "hsl(var(--muted-foreground))",
            "--tw-prose-bullets": "hsl(var(--muted-foreground))",
            "--tw-prose-hr": "hsl(var(--border))",
            "--tw-prose-quotes": "hsl(var(--foreground))",
            "--tw-prose-quote-borders": "hsl(var(--brand))",
            "--tw-prose-captions": "hsl(var(--muted-foreground))",
            "--tw-prose-code": "hsl(var(--foreground))",
            "--tw-prose-pre-code": "hsl(var(--foreground))",
            "--tw-prose-pre-bg": "hsl(var(--muted))",
            "--tw-prose-th-borders": "hsl(var(--border))",
            "--tw-prose-td-borders": "hsl(var(--border))",
          },
        },
      },
    },
  },
  plugins: [tailwindcssAnimate, typography],
} satisfies Config;

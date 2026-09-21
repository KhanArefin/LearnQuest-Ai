/** @type {import('tailwindcss').Config} */
// SHARED FILE - change by agreement (plan.md 2.4). Design tokens: plan.md 4.5.
//
// LearnQuest uses a professional, information-dense design language modelled on
// HackerRank: flat surfaces, 1px hairline borders, small radii, restrained
// colour, and normal-weight type. Colour marks status and nothing else.
// Full rules: docs/DESIGN_GUIDELINES.md
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Brand. Used for primary actions, active nav and focus - not decoration.
        primary: {
          50: '#F5F3FF',
          100: '#EDE9FE',
          200: '#DDD6FE',
          300: '#C4B5FD',
          400: '#A78BFA',
          500: '#8B5CF6',
          600: '#7C3AED', // primary action
          700: '#6D28D9', // hover / pressed
          800: '#5B21B6',
          900: '#4C1D95',
        },

        // Difficulty + status. These are the only other colours allowed to carry
        // meaning, and they map 1:1 to the labels users read.
        easy: { DEFAULT: '#00AF54', bg: '#E8F8EF', fg: '#00713A' },
        medium: { DEFAULT: '#FFB300', bg: '#FFF6E0', fg: '#8A6100' },
        hard: { DEFAULT: '#E5384B', bg: '#FDECEE', fg: '#A31D2C' },
        info: { DEFAULT: '#2D7FF9', bg: '#EAF2FE', fg: '#1A5BB8' },

        // Neutral ramp - the workhorse of a dense UI.
        ink: '#1F2933', // headings
        body: '#39424E', // body copy (HackerRank's text colour)
        muted: '#6B7885', // secondary text, table headers
        faint: '#9AA5B1', // placeholders, disabled
        line: '#E4E7EB', // 1px hairline border
        'line-strong': '#CBD2D9', // input borders, dividers that must read
        surface: '#FFFFFF', // cards, tables, panels
        canvas: '#F5F7FA', // page background
      },

      fontFamily: {
        // A neutral UI face, not a personality face.
        sans: ['Inter', 'Roboto', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },

      fontSize: {
        // Dense scale: 13px is the default body size in this system.
        '2xs': ['11px', { lineHeight: '16px' }],
        xs: ['12px', { lineHeight: '18px' }],
        sm: ['13px', { lineHeight: '20px' }],
        base: ['14px', { lineHeight: '22px' }],
        lg: ['16px', { lineHeight: '24px' }],
        xl: ['18px', { lineHeight: '26px' }],
        '2xl': ['22px', { lineHeight: '30px' }],
        '3xl': ['28px', { lineHeight: '36px' }],
      },

      borderRadius: {
        DEFAULT: '4px',
        md: '4px',
        lg: '6px',
        xl: '8px',
        '2xl': '8px', // deliberately capped - nothing in this UI is pill-shaped
        pill: '9999px', // except status chips
      },

      boxShadow: {
        // Shadows are for things that float above the page, not for depth on
        // every card. Cards use a border.
        card: '0 1px 2px rgba(31, 41, 51, 0.04)',
        dropdown: '0 4px 12px rgba(31, 41, 51, 0.12)',
        modal: '0 12px 32px rgba(31, 41, 51, 0.18)',
      },

      keyframes: {
        'fade-in': { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        shimmer: { '100%': { transform: 'translateX(100%)' } },
      },
      animation: {
        'fade-in': 'fade-in 0.15s ease-out',
        shimmer: 'shimmer 1.4s infinite',
      },
    },
  },
  plugins: [],
};

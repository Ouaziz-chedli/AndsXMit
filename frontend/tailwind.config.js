/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B0F19', // Deep dark blue background
        card: '#161B28', // Slightly lighter dark for cards
        border: '#232B3E',
        primary: {
          DEFAULT: '#3B82F6', // Blue 500
          hover: '#2563EB',
        },
        secondary: {
          DEFAULT: '#10B981', // Emerald 500
          hover: '#059669',
        },
        accent: {
          DEFAULT: '#8B5CF6', // Violet 500
          hover: '#7C3AED',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'hero-glow': 'conic-gradient(from 180deg at 50% 50%, #2a8af6 0deg, #a853ba 180deg, #e92a67 360deg)',
      }
    },
  },
  darkMode: 'class',
  plugins: [],
}

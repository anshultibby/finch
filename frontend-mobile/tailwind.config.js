/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
  ],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        finch: {
          bg: '#fafaf9',
          surface: '#ffffff',
          border: 'rgba(0, 0, 0, 0.06)',
          'border-strong': 'rgba(0, 0, 0, 0.1)',
        },
        platform: {
          kalshi: '#7c3aed',
          alpaca: '#059669',
          research: '#2563eb',
        },
      },
      fontFamily: {
        body: ['DMSans'],
        'body-medium': ['DMSans-Medium'],
        'body-bold': ['DMSans-Bold'],
      },
    },
  },
  plugins: [],
};

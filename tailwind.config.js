/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.{html,js}",    // HTML templates
    "./static/src/**/*.{html,js,css}" // Tailwind input files
  ],
  theme: {
    extend: {
          flexGrow: {
        1: '1',
        2: '2',
        3: '3',
        4: '4',
        5: '5',
        6: '6',
        7: '7',
        8: '8',
      },
    },
  },
  plugins: [],
}


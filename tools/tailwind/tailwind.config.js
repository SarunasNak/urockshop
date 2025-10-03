// tools/tailwind/tailwind.config.js
module.exports = {
  content: [
    "../../templates/**/*.html",              // visi Django šablonai
    "../../static/fe/assets/js/**/*.js",      // jei klasės atsiranda JS'e
  ],
  theme: {
    container: {
      center: true,
      padding: "5px",
      screens: {
        sm: "600px",
        md: "728px",
        lg: "984px",
        xl: "1200px",
        "2xl": "1440px",
      },
    },
    extend: {
      colors: {
        "brand-beige": "#9E9288",
        "brand-maroon": "#6D1F36",
        "brand-gray-light": "#D9D9D9",
        "brand-gray-medium": "#B7B1B1",
      },
      fontFamily: {
        mont: ["Montserrat", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["Playfair Display", "ui-serif", "Georgia", "serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
}

// tools/tailwind/tailwind.config.js
const path = require("path");

module.exports = {
  content: [
    path.join(__dirname, "../../templates/**/*.html"),
    path.join(__dirname, "../../**/templates/**/*.html"),
    path.join(__dirname, "../../shop/static/fe/assets/js/**/*.js"),
  ],

  // ← PRIDĖTA: kad neišmestų aspect ratio klasių
  safelist: [
    // katalogo kortelė
    'aspect-[308/460]',
    // detalės slideris
    'aspect-[203/305]',
    'md:aspect-[640/964]',
  ],

  theme: {
    container: {
      center: true,
      padding: "5px",
      screens: { sm:"600px", md:"728px", lg:"984px", xl:"1200px", "2xl":"1440px" }
    },
    extend: {
      colors: {
        "brand-beige":"#9E9288",
        "brand-maroon":"#6D1F36",
        "brand-gray-light":"#D9D9D9",
        "brand-gray-medium":"#B7B1B1",
      },
      fontFamily: {
        mont:["Montserrat","ui-sans-serif","system-ui","sans-serif"],
        serif:["Playfair Display","ui-serif","Georgia","serif"],
        sans:["Inter","ui-sans-serif","system-ui","sans-serif"],
      },
    },
  },
  plugins: [], // Tailwind v3 aspect-[…] veikia be papildomo plugino
};

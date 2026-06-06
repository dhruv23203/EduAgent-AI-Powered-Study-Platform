/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}", "./lib/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17212b",
        mist: "#eef4f1",
        paper: "#fbfcfb",
        fern: "#1f7a5f",
        coral: "#f26b5e",
        amber: "#f5b84b",
        skydeep: "#276678",
        graphite: "#25313b"
      },
      boxShadow: {
        soft: "0 18px 50px rgba(23, 33, 43, 0.08)",
        panel: "0 24px 70px rgba(23, 33, 43, 0.12)"
      }
    }
  },
  plugins: []
};

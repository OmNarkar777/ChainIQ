export default {
  content: ["./index.html","./src/**/*.{js,jsx}"],
  theme: { extend: {
    fontFamily: { display: ["DM Mono","monospace"], sans: ["IBM Plex Sans","sans-serif"] },
    colors: { acid: { DEFAULT:"#b5f23d" } },
    animation: { "fade-in":"fadeIn 0.4s ease forwards", "pulse-slow":"pulse 3s cubic-bezier(0.4,0,0.6,1) infinite" },
    keyframes: { fadeIn:{ from:{opacity:0}, to:{opacity:1} } },
  }},
  plugins: [],
};
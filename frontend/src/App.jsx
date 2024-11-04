import { Routes, Route, NavLink } from "react-router-dom";
import { LayoutDashboard, PlayCircle, Package, TrendingUp, Zap } from "lucide-react";
import Dashboard  from "./pages/Dashboard.jsx";
import Analysis   from "./pages/Analysis.jsx";
import Inventory  from "./pages/Inventory.jsx";
import Forecast   from "./pages/Forecast.jsx";
const NAV = [
  { to:"/",          icon:LayoutDashboard, label:"Dashboard"  },
  { to:"/analysis",  icon:PlayCircle,      label:"Analysis"   },
  { to:"/inventory", icon:Package,         label:"Inventory"  },
  { to:"/forecast",  icon:TrendingUp,      label:"Forecast"   },
];
export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
          <div className="flex items-center gap-2.5 shrink-0">
            <div className="w-6 h-6 bg-[#b5f23d] rounded flex items-center justify-center">
              <Zap size={13} className="text-zinc-950" fill="currentColor"/>
            </div>
            <span className="font-mono font-semibold text-zinc-100 text-sm">ChainIQ</span>
            <span className="font-mono text-xs text-zinc-700 hidden sm:block">supply chain intelligence</span>
          </div>
          <nav className="flex items-center gap-1 ml-4">
            {NAV.map(({to,icon:Icon,label})=>(
              <NavLink key={to} to={to} end={to==="/"}
                className={({isActive})=>`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all ${isActive?"bg-[#b5f23d]/10 text-[#b5f23d] border border-[#b5f23d]/20":"text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"}`}>
                <Icon size={12}/><span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs font-mono text-zinc-700 hidden md:block">v2.0.0</span>
            <div className="w-1.5 h-1.5 rounded-full bg-[#b5f23d]"/>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8">
        <Routes>
          <Route path="/"          element={<Dashboard/>}/>
          <Route path="/analysis"  element={<Analysis/>}/>
          <Route path="/inventory" element={<Inventory/>}/>
          <Route path="/forecast"  element={<Forecast/>}/>
        </Routes>
      </main>
      <footer className="border-t border-zinc-900 py-3 px-4">
        <p className="text-center text-xs font-mono text-zinc-800">ChainIQ - XGBoost + LangGraph + ChromaDB + Groq</p>
      </footer>
    </div>
  );
}
import { ReactNode, useState } from "react";
import { Link, useLocation } from "wouter";
import {
  Baby,
  Activity,
  Camera,
  Stethoscope,
  LineChart,
  Bell,
  AlertTriangle,
  Users,
  Menu,
  X
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: Baby },
  { href: "/cry-analyzer", label: "Cry Analyzer", icon: Activity },
  { href: "/photo-analysis", label: "Photo Analysis", icon: Camera },
  { href: "/diagnosis", label: "Smart Diagnosis", icon: Stethoscope },
  { href: "/growth", label: "Growth Tracker", icon: LineChart },
  { href: "/reminders", label: "Reminders", icon: Bell },
  { href: "/emergency", label: "Emergency", icon: AlertTriangle, danger: true },
  { href: "/community", label: "Community", icon: Users },
];

export function Layout({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-72 flex-col bg-white/60 backdrop-blur-xl border-r border-white/40 shadow-xl shadow-primary/5 z-10">
        <div className="p-6">
          <Link href="/" className="flex items-center gap-3 cursor-pointer group">
            <div className="bg-gradient-to-tr from-primary to-secondary p-2.5 rounded-2xl shadow-sm group-hover:scale-105 transition-transform">
              <Baby className="w-6 h-6 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-display font-bold bg-gradient-to-r from-primary-foreground to-secondary-foreground bg-clip-text text-transparent">
              BabyCare AI
            </h1>
          </Link>
        </div>
        
        <nav className="flex-1 px-4 space-y-1.5 overflow-y-auto pb-6">
          {NAV_ITEMS.map((item) => {
            const isActive = location === item.href;
            return (
              <Link key={item.href} href={item.href}>
                <div className={`
                  flex items-center gap-3 px-4 py-3.5 rounded-2xl cursor-pointer transition-all duration-300 font-medium
                  ${isActive 
                    ? item.danger 
                      ? "bg-destructive text-destructive-foreground shadow-lg shadow-destructive/20" 
                      : "bg-white text-primary-foreground shadow-md shadow-primary/10 border border-white"
                    : item.danger
                      ? "text-destructive hover:bg-destructive/10"
                      : "text-muted-foreground hover:bg-white/50 hover:text-foreground"
                  }
                `}>
                  <item.icon className={`w-5 h-5 ${isActive && !item.danger ? "text-primary" : ""}`} />
                  {item.label}
                </div>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Mobile Header & Nav */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="md:hidden flex items-center justify-between p-4 bg-white/80 backdrop-blur-md border-b border-white/40 z-20">
          <Link href="/" className="flex items-center gap-2">
            <Baby className="w-6 h-6 text-primary" />
            <h1 className="text-xl font-display font-bold text-foreground">BabyCare AI</h1>
          </Link>
          <button 
            onClick={() => setIsMobileOpen(true)}
            className="p-2 bg-primary/10 text-primary rounded-full"
          >
            <Menu className="w-5 h-5" />
          </button>
        </header>

        <AnimatePresence>
          {isMobileOpen && (
            <>
              <motion.div 
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="fixed inset-0 bg-foreground/20 backdrop-blur-sm z-40 md:hidden"
                onClick={() => setIsMobileOpen(false)}
              />
              <motion.aside 
                initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
                transition={{ type: "spring", damping: 25, stiffness: 20 }}
                className="fixed top-0 right-0 bottom-0 w-3/4 max-w-sm bg-white shadow-2xl z-50 flex flex-col md:hidden"
              >
                <div className="p-4 flex justify-end">
                  <button onClick={() => setIsMobileOpen(false)} className="p-2 bg-muted rounded-full">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <nav className="flex-1 px-4 space-y-2 overflow-y-auto pb-6">
                  {NAV_ITEMS.map((item) => {
                    const isActive = location === item.href;
                    return (
                      <Link key={item.href} href={item.href}>
                        <div 
                          onClick={() => setIsMobileOpen(false)}
                          className={`
                            flex items-center gap-4 px-4 py-4 rounded-2xl transition-all font-medium text-lg
                            ${isActive 
                              ? item.danger 
                                ? "bg-destructive text-destructive-foreground" 
                                : "bg-primary/10 text-primary-foreground"
                              : item.danger
                                ? "text-destructive"
                                : "text-muted-foreground"
                            }
                          `}
                        >
                          <item.icon className="w-6 h-6" />
                          {item.label}
                        </div>
                      </Link>
                    );
                  })}
                </nav>
              </motion.aside>
            </>
          )}
        </AnimatePresence>

        <main className="flex-1 overflow-y-auto relative scroll-smooth">
          <div className="max-w-5xl mx-auto w-full min-h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

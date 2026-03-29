import { Link } from "wouter";
import { Activity, Camera, Stethoscope, LineChart, Bell, Users } from "lucide-react";
import { motion } from "framer-motion";

const FEATURES = [
  { title: "Cry Analyzer", desc: "Understand why your baby is crying.", icon: Activity, href: "/cry-analyzer", color: "from-blue-400 to-primary" },
  { title: "Photo Analysis", desc: "Check rashes or conditions safely.", icon: Camera, href: "/photo-analysis", color: "from-purple-400 to-pink-400" },
  { title: "Smart Diagnosis", desc: "Symptom checker & medical advice.", icon: Stethoscope, href: "/diagnosis", color: "from-emerald-400 to-teal-500" },
  { title: "Growth Tracker", desc: "Track percentiles vs WHO standards.", icon: LineChart, href: "/growth", color: "from-amber-400 to-orange-400" },
  { title: "Smart Reminders", desc: "Never miss a feeding or vaccine.", icon: Bell, href: "/reminders", color: "from-indigo-400 to-indigo-500" },
  { title: "Community", desc: "Connect with other mothers.", icon: Users, href: "/community", color: "from-rose-400 to-rose-500" },
];

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};
const itemAnim = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring" } }
};

export default function Dashboard() {
  return (
    <div className="p-6 md:p-10 pb-20">
      <div className="relative rounded-3xl overflow-hidden mb-12 shadow-2xl shadow-primary/10">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/80 to-secondary/80 mix-blend-multiply" />
        <img 
          src={`${import.meta.env.BASE_URL}images/nursery-bg.png`} 
          alt="Nursery background" 
          className="w-full h-64 object-cover object-center"
        />
        <div className="absolute inset-0 flex items-center p-8 md:p-12">
          <div className="max-w-xl text-white">
            <h1 className="text-4xl md:text-5xl font-display font-bold mb-4 drop-shadow-md">
              Welcome to BabyCare AI
            </h1>
            <p className="text-lg md:text-xl text-white/90 drop-shadow-sm font-medium">
              Your AI-powered pediatrician assistant and daily companion for early motherhood.
            </p>
          </div>
        </div>
      </div>

      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-2xl font-display font-bold text-foreground">How can we help today?</h2>
      </div>

      <motion.div 
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        {FEATURES.map((feature) => (
          <motion.div key={feature.title} variants={itemAnim}>
            <Link href={feature.href}>
              <div className="bg-white rounded-3xl p-6 shadow-xl shadow-black/5 border border-white/40 hover:-translate-y-1 hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 cursor-pointer h-full flex flex-col group">
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 shadow-inner group-hover:scale-110 transition-transform`}>
                  <feature.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-foreground mb-2">{feature.title}</h3>
                <p className="text-muted-foreground font-medium">{feature.desc}</p>
              </div>
            </Link>
          </motion.div>
        ))}
      </motion.div>

      <div className="mt-12 bg-destructive/10 rounded-3xl p-8 border border-destructive/20 flex flex-col md:flex-row items-center justify-between gap-6">
        <div>
          <h3 className="text-2xl font-display font-bold text-destructive mb-2">Emergency Assistant</h3>
          <p className="text-destructive-foreground/80">Quick access to medical triage and CPR guides.</p>
        </div>
        <Link href="/emergency">
          <div className="px-8 py-4 bg-destructive text-destructive-foreground rounded-2xl font-bold shadow-lg shadow-destructive/30 hover:shadow-xl hover:-translate-y-0.5 transition-all text-center">
            Open Emergency Mode
          </div>
        </Link>
      </div>
    </div>
  );
}

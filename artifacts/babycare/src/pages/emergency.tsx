import { useState } from "react";
import { AlertTriangle, Phone, MapPin, Activity } from "lucide-react";
import { motion } from "framer-motion";
import { useAssessEmergency, useGetNearbyHospitals } from "@workspace/api-client-react";
import { useGeolocation } from "@/hooks/use-geolocation";

export default function Emergency() {
  const [age, setAge] = useState<number>(6);
  const [symptoms, setSymptoms] = useState<string[]>([]);
  
  const geo = useGeolocation();
  const assessMut = useAssessEmergency();
  
  const hospitalsQuery = useGetNearbyHospitals(
    { lat: geo.lat!, lng: geo.lng! },
    { query: { enabled: !!geo.lat && !!geo.lng } }
  );

  const toggleSymptom = (s: string) => {
    setSymptoms(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);
  };

  const handleAssess = () => {
    assessMut.mutate({
      data: {
        age_months: age,
        symptoms: symptoms,
        is_breathing: !symptoms.includes("Not Breathing"),
        is_conscious: !symptoms.includes("Unconscious"),
      }
    });
  };

  return (
    <div className="min-h-screen bg-rose-50 p-6 md:p-10">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-4 bg-red-600 rounded-full animate-pulse shadow-lg shadow-red-600/50">
              <AlertTriangle className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-display font-bold text-red-950">Emergency Mode</h1>
          </div>
          <a href="tel:911" className="hidden md:flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-xl font-bold shadow-xl shadow-red-600/30 hover:bg-red-700 transition-colors">
            <Phone className="w-5 h-5" />
            CALL 911
          </a>
        </header>

        <a href="tel:911" className="md:hidden w-full flex items-center justify-center gap-2 px-6 py-4 bg-red-600 text-white rounded-2xl font-bold text-xl shadow-xl shadow-red-600/30 mb-8 active:scale-95 transition-transform">
          <Phone className="w-6 h-6" />
          CALL 911 NOW
        </a>

        <div className="bg-white rounded-3xl p-6 md:p-8 shadow-2xl border-4 border-red-100 mb-8">
          <h2 className="text-2xl font-bold mb-6 text-red-950">Quick Triage</h2>
          
          <div className="mb-6">
            <label className="block font-bold mb-3">Critical Signs (Select all that apply)</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {["Not Breathing", "Unconscious", "Seizure", "Choking", "Blue/Pale Lips", "Severe Bleeding", "High Fever (>40C)", "Stiff Neck"].map(s => (
                <button
                  key={s}
                  onClick={() => toggleSymptom(s)}
                  className={`
                    px-4 py-4 rounded-xl font-bold text-left border-2 transition-all flex items-center justify-between
                    ${symptoms.includes(s) 
                      ? "bg-red-100 border-red-500 text-red-900" 
                      : "bg-muted/50 border-transparent text-muted-foreground hover:bg-red-50"
                    }
                  `}
                >
                  {s}
                  {symptoms.includes(s) && <AlertTriangle className="w-5 h-5" />}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4 mb-8">
            <div className="w-32">
              <label className="block font-bold mb-2">Age (Mo)</label>
              <input 
                type="number" value={age} onChange={e => setAge(Number(e.target.value))}
                className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-red-400 outline-none font-bold text-lg" 
              />
            </div>
          </div>

          <button
            onClick={handleAssess}
            disabled={symptoms.length === 0 || assessMut.isPending}
            className="w-full py-4 bg-red-600 text-white rounded-xl font-bold text-xl shadow-lg hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            {assessMut.isPending ? "Assessing..." : "Assess Emergency Level"}
          </button>
        </div>

        {assessMut.data && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
            className={`
              rounded-3xl p-8 shadow-2xl mb-8 border-4
              ${assessMut.data.level === 'call_911' ? 'bg-red-600 border-red-700 text-white' : 
                assessMut.data.level === 'urgent_er' ? 'bg-orange-500 border-orange-600 text-white' : 
                'bg-yellow-400 border-yellow-500 text-yellow-950'}
            `}
          >
            <h2 className="text-3xl font-display font-black uppercase tracking-widest mb-4 flex items-center gap-3">
              <Activity className="w-8 h-8" />
              {assessMut.data.level.replace('_', ' ')}
            </h2>
            <p className="text-xl font-medium opacity-90 mb-8">{assessMut.data.message}</p>
            
            <div className="bg-white/20 rounded-2xl p-6 backdrop-blur-sm">
              <h3 className="font-bold text-lg mb-4">Immediate Actions:</h3>
              <ul className="space-y-3">
                {assessMut.data.immediate_actions.map((action, i) => (
                  <li key={i} className="flex gap-3 text-lg font-medium">
                    <span className="font-black opacity-50">{i+1}.</span>
                    {action}
                  </li>
                ))}
              </ul>
            </div>

            {assessMut.data.cpr_needed && (
              <div className="mt-8 bg-black/80 text-white p-6 rounded-2xl border border-white/20">
                <h3 className="font-black text-2xl text-red-500 mb-4 animate-pulse">START INFANT CPR</h3>
                <ol className="space-y-4 font-medium text-lg">
                  <li>1. Place baby on flat, firm surface.</li>
                  <li>2. Give 30 gentle chest compressions using 2 fingers in center of chest (push 1.5 inches deep, 100-120 per min).</li>
                  <li>3. Open airway (tilt head past neutral).</li>
                  <li>4. Give 2 gentle rescue breaths (cover nose and mouth with your mouth).</li>
                  <li>5. Repeat cycle of 30 compressions and 2 breaths until help arrives.</li>
                </ol>
              </div>
            )}
          </motion.div>
        )}

        {hospitalsQuery.data && hospitalsQuery.data.length > 0 && (
          <div className="bg-white rounded-3xl p-6 md:p-8 shadow-xl border border-border">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
              <MapPin className="text-red-500" />
              Nearby Hospitals
            </h2>
            <div className="grid gap-4">
              {hospitalsQuery.data.map((h, i) => (
                <div key={i} className="flex items-center justify-between p-4 border rounded-2xl hover:border-red-200 transition-colors">
                  <div>
                    <h4 className="font-bold text-lg">{h.name}</h4>
                    <p className="text-muted-foreground text-sm">{h.address}</p>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-red-600 text-lg">{h.distance_km.toFixed(1)} km</div>
                    {h.phone && <a href={`tel:${h.phone}`} className="text-sm text-primary hover:underline">{h.phone}</a>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

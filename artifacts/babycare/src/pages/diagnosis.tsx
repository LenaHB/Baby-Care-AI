import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Stethoscope, AlertTriangle, CheckCircle } from "lucide-react";
import { motion } from "framer-motion";
import { useDiagnose } from "@workspace/api-client-react";

const COMMON_SYMPTOMS = [
  "Fever", "Crying excessively", "Rash", "Vomiting", 
  "Diarrhea", "Cough", "Difficulty breathing", 
  "Poor feeding", "Lethargy", "Unusual skin color"
];

const formSchema = z.object({
  age_months: z.coerce.number().min(0).max(120),
  weight_kg: z.coerce.number().optional().or(z.literal('')),
  temperature: z.coerce.number().optional().or(z.literal('')),
  duration_hours: z.coerce.number().optional().or(z.literal('')),
  notes: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

export default function Diagnosis() {
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(formSchema),
  });
  
  const diagnoseMut = useDiagnose();

  const toggleSymptom = (s: string) => {
    setSelectedSymptoms(prev => 
      prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
    );
  };

  const onSubmit = (data: FormData) => {
    if (selectedSymptoms.length === 0) {
      alert("Please select at least one symptom.");
      return;
    }
    diagnoseMut.mutate({
      data: {
        age_months: data.age_months,
        weight_kg: data.weight_kg === '' ? null : data.weight_kg as number,
        temperature: data.temperature === '' ? null : data.temperature as number,
        duration_hours: data.duration_hours === '' ? null : data.duration_hours as number,
        notes: data.notes || null,
        symptoms: selectedSymptoms,
      }
    });
  };

  return (
    <div className="p-6 md:p-10 max-w-5xl mx-auto pb-20">
      <header className="mb-8">
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 bg-emerald-100 rounded-2xl">
            <Stethoscope className="w-8 h-8 text-emerald-600" />
          </div>
          <h1 className="text-4xl font-display font-bold text-foreground">Smart Diagnosis</h1>
        </div>
        <p className="text-lg text-muted-foreground">
          Enter your baby's symptoms for AI-powered medical triage and home care advice.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-7 bg-white rounded-3xl p-6 md:p-8 shadow-xl shadow-black/5 border border-border">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-bold text-foreground mb-2">Age (Months) *</label>
                <input 
                  type="number" step="0.1"
                  {...register("age_months")}
                  className="w-full px-4 py-3 rounded-xl bg-background border-2 border-border focus:border-emerald-400 focus:ring-4 focus:ring-emerald-400/10 outline-none transition-all"
                  placeholder="e.g. 6"
                />
                {errors.age_months && <p className="text-destructive text-sm mt-1">{errors.age_months.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-bold text-foreground mb-2">Weight (kg)</label>
                <input 
                  type="number" step="0.1"
                  {...register("weight_kg")}
                  className="w-full px-4 py-3 rounded-xl bg-background border-2 border-border focus:border-emerald-400 focus:ring-4 focus:ring-emerald-400/10 outline-none transition-all"
                  placeholder="Optional"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-foreground mb-2">Temp (°C)</label>
                <input 
                  type="number" step="0.1"
                  {...register("temperature")}
                  className="w-full px-4 py-3 rounded-xl bg-background border-2 border-border focus:border-emerald-400 focus:ring-4 focus:ring-emerald-400/10 outline-none transition-all"
                  placeholder="Optional"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-foreground mb-2">Duration (Hours)</label>
                <input 
                  type="number"
                  {...register("duration_hours")}
                  className="w-full px-4 py-3 rounded-xl bg-background border-2 border-border focus:border-emerald-400 focus:ring-4 focus:ring-emerald-400/10 outline-none transition-all"
                  placeholder="Optional"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-foreground mb-4">Symptoms *</label>
              <div className="flex flex-wrap gap-2">
                {COMMON_SYMPTOMS.map(s => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleSymptom(s)}
                    className={`
                      px-4 py-2 rounded-full border-2 text-sm font-bold transition-all
                      ${selectedSymptoms.includes(s)
                        ? "bg-emerald-100 border-emerald-400 text-emerald-800"
                        : "bg-white border-border text-muted-foreground hover:border-emerald-200 hover:bg-emerald-50"
                      }
                    `}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-foreground mb-2">Additional Notes</label>
              <textarea 
                {...register("notes")}
                className="w-full px-4 py-3 rounded-xl bg-background border-2 border-border focus:border-emerald-400 focus:ring-4 focus:ring-emerald-400/10 outline-none transition-all min-h-24"
                placeholder="Describe any other details..."
              />
            </div>

            <button
              type="submit"
              disabled={diagnoseMut.isPending}
              className="w-full py-4 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-2xl font-bold text-lg shadow-lg shadow-emerald-500/25 hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50"
            >
              {diagnoseMut.isPending ? "Generating Diagnosis..." : "Get Medical Advice"}
            </button>
          </form>
        </div>

        <div className="lg:col-span-5">
          {diagnoseMut.data && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              className={`
                rounded-3xl p-8 shadow-xl border-2
                ${diagnoseMut.data.severity === 'red' ? 'bg-red-50 border-red-200' :
                  diagnoseMut.data.severity === 'orange' ? 'bg-orange-50 border-orange-200' :
                  diagnoseMut.data.severity === 'yellow' ? 'bg-yellow-50 border-yellow-200' :
                  'bg-green-50 border-green-200'
                }
              `}
            >
              <div className="flex items-center gap-3 mb-6">
                <AlertTriangle className={`w-8 h-8 
                  ${diagnoseMut.data.severity === 'red' ? 'text-red-600' :
                    diagnoseMut.data.severity === 'orange' ? 'text-orange-600' :
                    diagnoseMut.data.severity === 'yellow' ? 'text-yellow-600' :
                    'text-green-600'}
                `} />
                <h3 className="text-2xl font-display font-bold">{diagnoseMut.data.severity_label}</h3>
              </div>

              <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-5 mb-6 shadow-sm">
                <p className="font-medium text-foreground/90">{diagnoseMut.data.advice}</p>
              </div>

              <h4 className="font-bold text-lg mb-3">When to see a doctor:</h4>
              <p className="mb-6 text-foreground/80">{diagnoseMut.data.when_to_see_doctor}</p>

              {diagnoseMut.data.home_care.length > 0 && (
                <>
                  <h4 className="font-bold text-lg mb-3">Home Care:</h4>
                  <ul className="space-y-2 mb-6">
                    {diagnoseMut.data.home_care.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-foreground/80">
                        <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              <div className="text-xs text-muted-foreground mt-8 pt-4 border-t border-black/5 italic">
                Disclaimer: {diagnoseMut.data.disclaimer}
              </div>
            </motion.div>
          )}

          {!diagnoseMut.data && !diagnoseMut.isPending && (
            <div className="h-full flex items-center justify-center bg-primary/5 rounded-3xl border border-primary/10 p-8 text-center">
              <div>
                <Stethoscope className="w-16 h-16 text-primary/30 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-primary/60 mb-2">Awaiting Symptoms</h3>
                <p className="text-muted-foreground">Fill out the form to receive an AI-powered triage assessment.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

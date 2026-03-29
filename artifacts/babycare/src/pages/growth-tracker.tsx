import { useState } from "react";
import { LineChart as Chart, Line, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, ResponsiveContainer } from "recharts";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { LineChart, Plus, User } from "lucide-react";
import { useGetGrowthHistory, useAddGrowthRecord, useGetGrowthPercentile } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";

const schema = z.object({
  baby_name: z.string().min(1, "Name required"),
  age_months: z.coerce.number().min(0),
  gender: z.enum(["male", "female"]),
  weight_kg: z.coerce.number().min(0),
  height_cm: z.coerce.number().optional().or(z.literal('')),
  head_circumference_cm: z.coerce.number().optional().or(z.literal('')),
  notes: z.string().optional()
});

export default function GrowthTracker() {
  const [tab, setTab] = useState<"history" | "add">("history");
  const queryClient = useQueryClient();
  
  const historyQuery = useGetGrowthHistory({});
  const addMut = useAddGrowthRecord({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["/api/growth/history"] });
        setTab("history");
      }
    }
  });

  const { register, handleSubmit, formState: { errors }, watch } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { gender: "female" }
  });

  const watchAge = watch("age_months");
  const watchWeight = watch("weight_kg");
  const watchGender = watch("gender");

  // Only query percentile if we have the minimum required values
  const percentileQuery = useGetGrowthPercentile(
    { age_months: Number(watchAge), weight_kg: Number(watchWeight), gender: watchGender },
    { query: { enabled: !!watchAge && !!watchWeight && tab === "add" } }
  );

  const onSubmit = (data: z.infer<typeof schema>) => {
    addMut.mutate({
      data: {
        ...data,
        height_cm: data.height_cm === '' ? null : data.height_cm as number,
        head_circumference_cm: data.head_circumference_cm === '' ? null : data.head_circumference_cm as number,
        notes: data.notes || null
      }
    });
  };

  const chartData = historyQuery.data?.map(record => ({
    age: `Month ${record.age_months}`,
    weight: record.weight_kg,
    percentile: record.weight_percentile
  })).sort((a, b) => {
    // sort by age ascending roughly
    const valA = parseFloat(a.age.replace("Month ", ""));
    const valB = parseFloat(b.age.replace("Month ", ""));
    return valA - valB;
  }) || [];

  return (
    <div className="p-6 md:p-10 max-w-5xl mx-auto pb-20">
      <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-amber-100 rounded-2xl">
              <LineChart className="w-8 h-8 text-amber-600" />
            </div>
            <h1 className="text-4xl font-display font-bold text-foreground">Growth Tracker</h1>
          </div>
          <p className="text-lg text-muted-foreground">
            Track weight and height against WHO growth standards.
          </p>
        </div>
        
        <div className="flex bg-muted p-1 rounded-xl">
          <button 
            onClick={() => setTab("history")}
            className={`px-6 py-2.5 rounded-lg font-bold transition-all ${tab === 'history' ? 'bg-white shadow-sm text-foreground' : 'text-muted-foreground'}`}
          >
            History & Chart
          </button>
          <button 
            onClick={() => setTab("add")}
            className={`px-6 py-2.5 rounded-lg font-bold transition-all ${tab === 'add' ? 'bg-white shadow-sm text-foreground' : 'text-muted-foreground'}`}
          >
            Add Record
          </button>
        </div>
      </header>

      {tab === "history" && (
        <div className="space-y-8 animate-in fade-in zoom-in-95 duration-300">
          <div className="bg-white rounded-3xl p-6 md:p-8 shadow-xl shadow-black/5 border border-border h-[400px]">
            <h3 className="font-bold text-xl mb-6">Weight over Age</h3>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <Chart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                  <XAxis dataKey="age" tick={{fill: '#6B7280', fontSize: 12}} axisLine={false} tickLine={false} />
                  <YAxis tick={{fill: '#6B7280', fontSize: 12}} axisLine={false} tickLine={false} unit=" kg" />
                  <ChartTooltip 
                    contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)' }}
                  />
                  <Line type="monotone" dataKey="weight" stroke="#f59e0b" strokeWidth={4} dot={{r: 6, fill: '#f59e0b', strokeWidth: 2, stroke: '#fff'}} activeDot={{r: 8}} />
                </Chart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground font-medium">
                No growth records yet. Add one to see the chart!
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {historyQuery.data?.map(record => (
              <div key={record.id} className="bg-white rounded-2xl p-6 border border-border shadow-sm hover:shadow-md transition-all">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-2">
                    <User className="w-5 h-5 text-amber-500" />
                    <h4 className="font-bold">{record.baby_name}</h4>
                  </div>
                  <span className="text-xs font-bold text-muted-foreground bg-muted px-2 py-1 rounded-md">
                    {format(new Date(record.recorded_at), "MMM d, yyyy")}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-muted-foreground block">Age</span>
                    <span className="font-bold text-lg">{record.age_months} mo</span>
                  </div>
                  <div>
                    <span className="text-xs text-muted-foreground block">Weight</span>
                    <span className="font-bold text-lg text-amber-600">{record.weight_kg} kg</span>
                  </div>
                  {record.weight_percentile && (
                    <div className="col-span-2">
                      <span className="text-xs text-muted-foreground block">Percentile</span>
                      <div className="flex items-center gap-2 mt-1">
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-amber-400" style={{ width: `${record.weight_percentile}%` }} />
                        </div>
                        <span className="font-bold text-sm">{record.weight_percentile.toFixed(0)}th</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "add" && (
        <div className="bg-white rounded-3xl p-6 md:p-8 shadow-xl shadow-black/5 border border-border animate-in fade-in zoom-in-95 duration-300">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-bold mb-2">Baby Name *</label>
                <input {...register("baby_name")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-amber-400 outline-none" />
                {errors.baby_name && <p className="text-destructive text-sm mt-1">{errors.baby_name.message}</p>}
              </div>
              
              <div>
                <label className="block text-sm font-bold mb-2">Gender *</label>
                <select {...register("gender")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-amber-400 outline-none bg-white">
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-bold mb-2">Age (Months) *</label>
                <input type="number" step="0.1" {...register("age_months")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-amber-400 outline-none" />
              </div>

              <div>
                <label className="block text-sm font-bold mb-2">Weight (kg) *</label>
                <input type="number" step="0.01" {...register("weight_kg")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-amber-400 outline-none" />
              </div>

              <div>
                <label className="block text-sm font-bold mb-2">Height (cm)</label>
                <input type="number" step="0.1" {...register("height_cm")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-amber-400 outline-none" />
              </div>

              <div>
                <label className="block text-sm font-bold mb-2">Head Circumference (cm)</label>
                <input type="number" step="0.1" {...register("head_circumference_cm")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-amber-400 outline-none" />
              </div>
            </div>

            {percentileQuery.data && (
              <div className="bg-amber-50 rounded-2xl p-4 border border-amber-200">
                <h4 className="font-bold text-amber-800 mb-1">Live Percentile Preview</h4>
                <p className="text-amber-700">{percentileQuery.data.interpretation}</p>
                {percentileQuery.data.weight_percentile && (
                   <p className="font-bold text-amber-900 mt-2">Weight is in the {percentileQuery.data.weight_percentile.toFixed(1)}th percentile.</p>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={addMut.isPending}
              className="w-full md:w-auto px-8 py-4 bg-gradient-to-r from-amber-400 to-orange-400 text-white rounded-2xl font-bold text-lg shadow-lg shadow-amber-400/25 hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50"
            >
              {addMut.isPending ? "Saving..." : "Save Growth Record"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

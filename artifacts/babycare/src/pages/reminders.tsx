import { useState } from "react";
import { Bell, Plus, Check, Trash2, Calendar, Pill, Syringe, Moon, Utensils } from "lucide-react";
import { format, isPast } from "date-fns";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useListReminders, useCreateReminder, useUpdateReminder, useDeleteReminder } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

const TYPE_ICONS: Record<string, any> = {
  feeding: Utensils,
  sleep: Moon,
  vaccine: Syringe,
  medication: Pill,
  appointment: Calendar,
  other: Bell
};

const TYPE_COLORS: Record<string, string> = {
  feeding: "bg-orange-100 text-orange-600",
  sleep: "bg-indigo-100 text-indigo-600",
  vaccine: "bg-rose-100 text-rose-600",
  medication: "bg-emerald-100 text-emerald-600",
  appointment: "bg-blue-100 text-blue-600",
  other: "bg-gray-100 text-gray-600"
};

const schema = z.object({
  title: z.string().min(1),
  type: z.enum(["feeding", "sleep", "vaccine", "appointment", "medication", "other"]),
  due_at: z.string().min(1),
  notes: z.string().optional()
});

export default function Reminders() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const queryClient = useQueryClient();
  
  const { data: reminders, isLoading } = useListReminders();
  const createMut = useCreateReminder({ onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["/api/reminder/list"] }); setIsModalOpen(false); } });
  const updateMut = useUpdateReminder({ onSuccess: () => queryClient.invalidateQueries({ queryKey: ["/api/reminder/list"] }) });
  const deleteMut = useDeleteReminder({ onSuccess: () => queryClient.invalidateQueries({ queryKey: ["/api/reminder/list"] }) });

  const { register, handleSubmit, reset } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { type: "feeding" }
  });

  const onSubmit = (data: z.infer<typeof schema>) => {
    // format date for backend requirement
    createMut.mutate({ data: { ...data, due_at: new Date(data.due_at).toISOString() } });
    reset();
  };

  return (
    <div className="p-6 md:p-10 max-w-4xl mx-auto pb-20">
      <header className="mb-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-indigo-100 rounded-2xl">
            <Bell className="w-8 h-8 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-4xl font-display font-bold text-foreground">Reminders</h1>
            <p className="text-lg text-muted-foreground">Keep track of your baby's schedule.</p>
          </div>
        </div>
        
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-6 py-3 bg-indigo-500 text-white rounded-xl font-bold shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:-translate-y-0.5 transition-all"
        >
          <Plus className="w-5 h-5" />
          Add Reminder
        </button>
      </header>

      {isLoading ? (
        <div className="flex justify-center p-12"><div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {reminders?.length === 0 && (
            <div className="text-center py-20 bg-white rounded-3xl border border-border">
              <Bell className="w-16 h-16 text-muted-foreground/30 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-foreground mb-2">No Reminders Yet</h3>
              <p className="text-muted-foreground">Add your first reminder to get started.</p>
            </div>
          )}
          
          {reminders?.sort((a, b) => new Date(a.due_at).getTime() - new Date(b.due_at).getTime()).map(reminder => {
            const Icon = TYPE_ICONS[reminder.type] || Bell;
            const isOverdue = !reminder.completed && isPast(new Date(reminder.due_at));
            
            return (
              <div 
                key={reminder.id} 
                className={`
                  bg-white rounded-2xl p-5 border flex items-center gap-5 transition-all
                  ${reminder.completed ? 'opacity-60 bg-muted/50 border-transparent' : 
                    isOverdue ? 'border-destructive shadow-sm shadow-destructive/10' : 'border-border shadow-sm hover:shadow-md'
                  }
                `}
              >
                <button
                  onClick={() => updateMut.mutate({ id: reminder.id, data: { completed: !reminder.completed } })}
                  className={`
                    w-8 h-8 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors
                    ${reminder.completed ? 'bg-indigo-500 border-indigo-500 text-white' : 'border-border hover:border-indigo-400 text-transparent'}
                  `}
                >
                  <Check className="w-4 h-4" />
                </button>
                
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${TYPE_COLORS[reminder.type]}`}>
                  <Icon className="w-6 h-6" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <h3 className={`font-bold text-lg truncate ${reminder.completed ? 'line-through text-muted-foreground' : ''}`}>
                    {reminder.title}
                  </h3>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1">
                    <span className={`text-sm font-medium ${isOverdue ? 'text-destructive' : 'text-muted-foreground'}`}>
                      {format(new Date(reminder.due_at), "MMM d, yyyy 'at' h:mm a")}
                    </span>
                    {reminder.notes && (
                      <span className="text-sm text-muted-foreground truncate max-w-xs block">
                        • {reminder.notes}
                      </span>
                    )}
                  </div>
                </div>
                
                <button
                  onClick={() => { if(confirm('Delete reminder?')) deleteMut.mutate({ id: reminder.id }) }}
                  className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors shrink-0"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 bg-foreground/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl animate-in fade-in zoom-in-95">
            <h2 className="text-2xl font-display font-bold mb-6">Create Reminder</h2>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-bold mb-1">Title</label>
                <input {...register("title")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-indigo-400 outline-none" required />
              </div>
              
              <div>
                <label className="block text-sm font-bold mb-1">Type</label>
                <select {...register("type")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-indigo-400 outline-none bg-white">
                  <option value="feeding">Feeding</option>
                  <option value="sleep">Sleep</option>
                  <option value="vaccine">Vaccine</option>
                  <option value="medication">Medication</option>
                  <option value="appointment">Appointment</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-bold mb-1">Date & Time</label>
                <input type="datetime-local" {...register("due_at")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-indigo-400 outline-none bg-white" required />
              </div>

              <div>
                <label className="block text-sm font-bold mb-1">Notes</label>
                <input {...register("notes")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-indigo-400 outline-none" />
              </div>

              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => setIsModalOpen(false)} className="flex-1 py-3 bg-muted text-muted-foreground rounded-xl font-bold hover:bg-muted/80">Cancel</button>
                <button type="submit" disabled={createMut.isPending} className="flex-1 py-3 bg-indigo-500 text-white rounded-xl font-bold shadow-lg shadow-indigo-500/25">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

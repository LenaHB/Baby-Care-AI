import { useState } from "react";
import { Mic, Square, Activity, AlertCircle, CheckCircle2 } from "lucide-react";
import { motion } from "framer-motion";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";
import { useAnalyzeCry } from "@workspace/api-client-react";

export default function CryAnalyzer() {
  const { isRecording, recordingTime, startRecording, stopRecording, audioBlob, clearAudio } = useAudioRecorder();
  const analyzeMut = useAnalyzeCry();

  const handleAnalyze = () => {
    if (!audioBlob) return;
    analyzeMut.mutate({ data: { audio: audioBlob } });
  };

  return (
    <div className="p-6 md:p-10 max-w-4xl mx-auto">
      <header className="mb-10 text-center">
        <div className="w-20 h-20 bg-primary/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <Activity className="w-10 h-10 text-primary" />
        </div>
        <h1 className="text-4xl font-display font-bold text-foreground mb-4">Cry Analyzer</h1>
        <p className="text-lg text-muted-foreground">
          Record your baby's cry to understand what they might be feeling using AI sound analysis.
        </p>
      </header>

      <div className="bg-white rounded-3xl p-8 md:p-12 shadow-xl shadow-primary/5 border border-border/50 mb-8 text-center">
        {!audioBlob ? (
          <div className="flex flex-col items-center">
            {isRecording && (
              <div className="flex items-center gap-1 mb-10 h-16">
                {[...Array(12)].map((_, i) => (
                  <div 
                    key={i} 
                    className="w-2 bg-primary rounded-full wave-bar" 
                    style={{ animationDelay: `${i * 0.1}s` }}
                  />
                ))}
              </div>
            )}
            
            <button
              onClick={isRecording ? stopRecording : startRecording}
              className={`
                w-32 h-32 rounded-full flex flex-col items-center justify-center transition-all duration-300 shadow-2xl
                ${isRecording 
                  ? 'bg-destructive text-white shadow-destructive/40 scale-105 animate-pulse' 
                  : 'bg-gradient-to-tr from-primary to-primary/80 text-white shadow-primary/30 hover:scale-105 hover:shadow-primary/40'
                }
              `}
            >
              {isRecording ? <Square className="w-10 h-10 fill-current mb-2" /> : <Mic className="w-12 h-12 mb-2" />}
              <span className="font-bold">{isRecording ? "Stop" : "Record"}</span>
            </button>
            
            {isRecording && (
              <p className="mt-6 text-2xl font-mono text-destructive font-bold">
                00:{recordingTime.toString().padStart(2, '0')}
              </p>
            )}
            <p className="mt-6 text-muted-foreground">
              {isRecording ? "Listening carefully..." : "Tap to record for 5-10 seconds"}
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="w-24 h-24 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-6">
              <CheckCircle2 className="w-12 h-12" />
            </div>
            <h3 className="text-2xl font-bold mb-8">Recording Captured</h3>
            
            <div className="flex gap-4">
              <button
                onClick={clearAudio}
                className="px-6 py-3 rounded-xl font-bold text-muted-foreground hover:bg-muted transition-colors"
                disabled={analyzeMut.isPending}
              >
                Discard
              </button>
              <button
                onClick={handleAnalyze}
                disabled={analyzeMut.isPending}
                className="px-8 py-3 bg-primary text-primary-foreground rounded-xl font-bold shadow-lg shadow-primary/30 hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {analyzeMut.isPending ? "Analyzing..." : "Analyze Cry"}
              </button>
            </div>
          </div>
        )}
      </div>

      {analyzeMut.data && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-white to-secondary/10 rounded-3xl p-8 shadow-xl shadow-secondary/10 border border-secondary/20"
        >
          <div className="flex flex-col md:flex-row gap-8 items-start">
            <div className="flex-1">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white shadow-sm mb-4 border border-border">
                <span className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Detection</span>
                <span className="text-lg font-bold text-primary capitalize">{analyzeMut.data.classification}</span>
              </div>
              
              <h2 className="text-3xl font-display font-bold text-foreground mb-4">
                Confidence: {(analyzeMut.data.confidence * 100).toFixed(1)}%
              </h2>
              <p className="text-lg text-foreground/80 mb-6 font-medium">
                {analyzeMut.data.description}
              </p>
              
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-border">
                <h4 className="font-bold text-lg mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-secondary-foreground" />
                  Recommendations
                </h4>
                <ul className="space-y-3">
                  {analyzeMut.data.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-3 text-foreground/80">
                      <div className="w-6 h-6 rounded-full bg-secondary/30 flex items-center justify-center shrink-0 mt-0.5 text-sm font-bold text-secondary-foreground">
                        {i + 1}
                      </div>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            <div className="w-full md:w-1/3 bg-white rounded-2xl p-6 shadow-sm border border-border">
              <h4 className="font-bold mb-4">Acoustic Profile</h4>
              {analyzeMut.data.features && (
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Mean Pitch</span>
                      <span className="font-bold">{analyzeMut.data.features.mean_pitch.toFixed(0)} Hz</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-primary" style={{ width: `${Math.min(100, analyzeMut.data.features.mean_pitch / 8)}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Intensity (RMS)</span>
                      <span className="font-bold">{analyzeMut.data.features.rms_energy.toFixed(2)}</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-secondary-foreground" style={{ width: `${Math.min(100, analyzeMut.data.features.rms_energy * 100)}%` }} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {analyzeMut.isError && (
        <div className="bg-destructive/10 text-destructive p-6 rounded-2xl flex items-center gap-3">
          <AlertCircle className="w-6 h-6 shrink-0" />
          <p className="font-bold">Analysis failed. Please try recording again with clearer audio.</p>
        </div>
      )}
    </div>
  );
}

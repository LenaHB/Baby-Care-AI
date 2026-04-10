import { useState } from "react";
import { Camera, Upload, AlertCircle, CheckCircle } from "lucide-react";
import { motion } from "framer-motion";
import { useAnalyzePhoto } from "@workspace/api-client-react";
import type { AnalyzePhotoBodyAnalysisType } from "@workspace/api-client-react";

export default function PhotoAnalysis() {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState<AnalyzePhotoBodyAnalysisType>("general");
  
  const analyzeMut = useAnalyzePhoto();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      setPreview(URL.createObjectURL(file));
      analyzeMut.reset();
    }
  };

  const handleAnalyze = () => {
    if (!imageFile) return;
    analyzeMut.mutate({ 
      data: { 
        image: imageFile,
        analysis_type: analysisType
      } 
    });
  };

  return (
    <div className="p-6 md:p-10 max-w-4xl mx-auto pb-20">
      <header className="mb-10">
        <div className="flex items-center gap-4 mb-4">
          <div className="p-3 bg-secondary/30 rounded-2xl">
            <Camera className="w-8 h-8 text-secondary-foreground" />
          </div>
          <h1 className="text-4xl font-display font-bold text-foreground">Photo Analysis</h1>
        </div>
        <p className="text-lg text-muted-foreground">
          Upload a photo of a rash, stool, or skin condition for AI-assisted medical assessment.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <div className="bg-white rounded-3xl p-6 shadow-xl shadow-black/5 border border-border">
          <h3 className="text-xl font-bold mb-6">1. Upload Photo</h3>
          
          {!preview ? (
            <label className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-primary/40 rounded-2xl bg-primary/5 hover:bg-primary/10 transition-colors cursor-pointer group">
              <Upload className="w-10 h-10 text-primary/60 mb-4 group-hover:-translate-y-1 transition-transform" />
              <span className="font-bold text-primary">Click to Upload</span>
              <span className="text-sm text-muted-foreground mt-2">JPG, PNG up to 5MB</span>
              <input type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
            </label>
          ) : (
            <div className="relative rounded-2xl overflow-hidden h-64 border border-border group">
              <img src={preview} alt="Preview" className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <label className="px-6 py-2 bg-white text-foreground rounded-full font-bold cursor-pointer hover:scale-105 transition-transform">
                  Change Photo
                  <input type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
                </label>
              </div>
            </div>
          )}

          <div className="mt-8">
            <h3 className="text-xl font-bold mb-4">2. Select Type</h3>
            <div className="grid grid-cols-2 gap-3">
              {(['general', 'rash', 'stool', 'jaundice'] as const).map(type => (
                <button
                  key={type}
                  onClick={() => setAnalysisType(type)}
                  className={`
                    py-3 px-4 rounded-xl font-bold capitalize transition-all border-2
                    ${analysisType === type 
                      ? 'border-primary bg-primary/10 text-primary-foreground shadow-sm' 
                      : 'border-transparent bg-muted text-muted-foreground hover:bg-muted/80'
                    }
                  `}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={!imageFile || analyzeMut.isPending}
            className="w-full mt-8 py-4 bg-gradient-to-r from-primary to-primary/80 text-white rounded-2xl font-bold text-lg shadow-lg shadow-primary/25 hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {analyzeMut.isPending ? "Analyzing Photo..." : "Run AI Analysis"}
          </button>
        </div>

        <div>
          {analyzeMut.isPending && (
            <div className="h-full flex flex-col items-center justify-center p-12 bg-white/50 rounded-3xl border border-white">
              <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mb-6" />
              <h3 className="text-2xl font-display font-bold text-primary animate-pulse">Analyzing...</h3>
              <p className="text-muted-foreground text-center mt-2">Checking pixel coloration and patterns.</p>
            </div>
          )}

          {analyzeMut.data && !analyzeMut.isPending && (
            <motion.div 
              initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
              className="bg-white rounded-3xl p-8 shadow-xl shadow-black/5 border border-border h-full flex flex-col"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-2xl font-display font-bold">Results</h3>
                <span className={`
                  px-4 py-1.5 rounded-full font-bold text-sm uppercase tracking-wider
                  ${analyzeMut.data.severity === 'normal' ? 'bg-green-100 text-green-700' :
                    analyzeMut.data.severity === 'mild' ? 'bg-yellow-100 text-yellow-700' :
                    analyzeMut.data.severity === 'moderate' ? 'bg-orange-100 text-orange-700' :
                    'bg-red-100 text-red-700'}
                `}>
                  {analyzeMut.data.severity}
                </span>
0              </div>

              <div className="mb-6 p-4 bg-muted/50 rounded-2xl">
                <span className="text-sm font-bold text-muted-foreground uppercase tracking-wider block mb-1">Detected Condition</span>
                <span className="text-xl font-bold capitalize text-foreground">{analyzeMut.data.condition}</span>
              </div>

              <p className="text-foreground/80 mb-8 leading-relaxed">
                {analyzeMut.data.description}
              </p>

              <div className="mb-8 flex-1">
                <h4 className="font-bold mb-3">Care Recommendations</h4>
                <ul className="space-y-2">
                  {analyzeMut.data.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2 text-foreground/80">
                      <CheckCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>

              {analyzeMut.data.see_doctor && (
                <div className="bg-destructive/10 text-destructive p-4 rounded-2xl flex items-start gap-3 border border-destructive/20 mt-auto">
                  <AlertCircle className="w-6 h-6 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold">Medical Attention Recommended</h4>
                    <p className="text-sm mt-1">Based on this analysis, we recommend consulting your pediatrician to be safe.</p>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}

import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { Layout } from "@/components/layout";

// Pages
import Dashboard from "./pages/dashboard";
import CryAnalyzer from "./pages/cry-analyzer";
import PhotoAnalysis from "./pages/photo-analysis";
import Diagnosis from "./pages/diagnosis";
import GrowthTracker from "./pages/growth-tracker";
import Reminders from "./pages/reminders";
import Emergency from "./pages/emergency";
import Community from "./pages/community";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function Router() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/cry-analyzer" component={CryAnalyzer} />
        <Route path="/photo-analysis" component={PhotoAnalysis} />
        <Route path="/diagnosis" component={Diagnosis} />
        <Route path="/growth" component={GrowthTracker} />
        <Route path="/reminders" component={Reminders} />
        <Route path="/emergency" component={Emergency} />
        <Route path="/community" component={Community} />
        <Route component={NotFound} />
      </Switch>
    </Layout>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

import InputScreen from "./components/InputScreen";
import LoadingScreen from "./components/LoadingScreen";
import ProfileScreen from "./components/ProfileScreen";
import { useAnalysis } from "./lib/useAnalysis";
import { profiles } from "./mock/profiles.fixture";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const { phase, data, selectProfile, run, reset } = useAnalysis();

  if (phase === "loading") return <LoadingScreen />;
  if (phase === "dashboard" && data) return <Dashboard data={data} onReset={reset} />;
  if (phase === "input") return <InputScreen onSubmit={run} onBack={reset} />;
  return <ProfileScreen profiles={profiles} onSelect={selectProfile} />;
}

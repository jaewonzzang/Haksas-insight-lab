import ErrorScreen from "./components/ErrorScreen";
import InputScreen from "./components/InputScreen";
import LoadingScreen from "./components/LoadingScreen";
import ProfileScreen from "./components/ProfileScreen";
import { useAnalysis } from "./lib/useAnalysis";
import { profiles } from "./mock/profiles.fixture";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const { phase, data, error, selectProfile, run, reset, backToInput } = useAnalysis();

  if (phase === "loading") return <LoadingScreen />;
  if (phase === "error")
    return <ErrorScreen message={error ?? "알 수 없는 오류"} onRetry={backToInput} onReset={reset} />;
  if (phase === "dashboard" && data) return <Dashboard data={data} onReset={reset} />;
  if (phase === "input") return <InputScreen onSubmit={run} onBack={reset} />;
  return <ProfileScreen profiles={profiles} onSelect={selectProfile} />;
}

import { useState } from "react";
import "./App.css";
import { SetupScreen } from "./screens/SetupScreen";
import { ProgressScreen } from "./screens/ProgressScreen";
import { ResultScreen } from "./screens/ResultScreen";
import { HistoryScreen } from "./screens/HistoryScreen";
import { useApiReadiness } from "./hooks/useApiReadiness";

type View =
  | { screen: "setup" }
  | { screen: "progress"; jobId: string }
  | { screen: "result"; jobId: string }
  | { screen: "history" };

function App() {
  const [view, setView] = useState<View>({ screen: "setup" });
  const { ready } = useApiReadiness();

  if (!ready) {
    return (
      <div className="app-loading">
        <p>Starting sync engine…</p>
      </div>
    );
  }

  return (
    <>
      <header className="app-header">
        <h1>Skelly Synchronize</h1>
        <nav>
          <a onClick={() => setView({ screen: "history" })}>History</a>
        </nav>
      </header>

      {view.screen === "setup" && (
        <SetupScreen
          onJobCreated={(jobId) => setView({ screen: "progress", jobId })}
        />
      )}

      {view.screen === "progress" && (
        <ProgressScreen
          jobId={view.jobId}
          onSucceeded={(jobId) => setView({ screen: "result", jobId })}
          onBackToSetup={() => setView({ screen: "setup" })}
        />
      )}

      {view.screen === "result" && (
        <ResultScreen
          jobId={view.jobId}
          onRunAnother={() => setView({ screen: "setup" })}
        />
      )}

      {view.screen === "history" && (
        <HistoryScreen
          onSelectJob={(jobId) => setView({ screen: "result", jobId })}
          onBackToSetup={() => setView({ screen: "setup" })}
        />
      )}
    </>
  );
}

export default App;

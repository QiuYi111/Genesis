import "./styles/app.css";
import { PaneLayout } from "./components/layout/PaneLayout";
import { MapPanel } from "./components/map/MapPanel";
import { TimelinePanel } from "./components/timeline/TimelinePanel";
import { AnalyticsPanel } from "./components/analytics/AnalyticsPanel";
import { TurnControls } from "./components/controls/TurnControls";
import { InteractionPanel } from "./components/interaction/InteractionPanel";
import { ConnectionBanner } from "./components/controls/ConnectionBanner";
import { useMonitorStream } from "./services/monitorStream";
import { RunControls } from "./components/controls/RunControls";
import { MessageBox } from "./components/messages/MessageBox";
import { useSimulationBootstrap } from "./hooks/useSimulationBootstrap";

function App(): JSX.Element {
  useSimulationBootstrap();
  useMonitorStream();

  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <div>
          <h1>Genesis Monitoring Console</h1>
          <p className="app-shell__subtitle">
            Real-time situational awareness with rewindable turn buffers and interaction tracing
          </p>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <TurnControls />
          <RunControls />
        </div>
      </header>
      <ConnectionBanner />
      <div style={{ margin: "8px 0" }}>
        <MessageBox />
      </div>
      <PaneLayout
        map={<MapPanel />}
        timeline={<TimelinePanel />}
        analytics={<AnalyticsPanel />}
        interactions={<InteractionPanel />}
      />
    </div>
  );
}

export default App;

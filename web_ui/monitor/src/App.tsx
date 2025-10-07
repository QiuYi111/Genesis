import "./styles/app.css";
import { PaneLayout } from "./components/layout/PaneLayout";
import { MapPanel } from "./components/map/MapPanel";
import { TimelinePanel } from "./components/timeline/TimelinePanel";
import { AnalyticsPanel } from "./components/analytics/AnalyticsPanel";
import { TurnControls } from "./components/controls/TurnControls";
import { InteractionPanel } from "./components/interaction/InteractionPanel";
import { ConnectionBanner } from "./components/controls/ConnectionBanner";
import { useMockTurnStream } from "./hooks/useMockTurnStream";

function App(): JSX.Element {
  useMockTurnStream();

  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <div>
          <h1>Genesis Monitoring Console</h1>
          <p className="app-shell__subtitle">
            Real-time situational awareness with rewindable turn buffers and interaction tracing
          </p>
        </div>
        <TurnControls />
      </header>
      <ConnectionBanner />
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

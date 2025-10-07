import "../../styles/pane-layout.css";
import type { ReactNode } from "react";

interface PaneLayoutProps {
  map: ReactNode;
  timeline: ReactNode;
  analytics: ReactNode;
  interactions: ReactNode;
}

export function PaneLayout({ map, timeline, analytics, interactions }: PaneLayoutProps): JSX.Element {
  return (
    <main className="pane-layout">
      <section className="pane-layout__map" aria-label="Simulation map">
        {map}
      </section>
      <section className="pane-layout__timeline" aria-label="Event timeline">
        {timeline}
      </section>
      <section className="pane-layout__analytics" aria-label="Analytics and cohorts">
        {analytics}
      </section>
      <section className="pane-layout__interactions" aria-label="Interaction log">
        {interactions}
      </section>
    </main>
  );
}

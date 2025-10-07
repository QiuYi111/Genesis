# Web UI Revamp Strategy

## Executive Summary
- **Recommendation**: double down on a modern web front end as the default operator console. A browser-based client remains the only option that can reach every stakeholder (Wei's demos, researchers, remote ops) without custom installs, while still letting us embed immersive elements through WebGL/WebGPU when needed.
- **Time horizon**: ship a dependable monitoring dashboard in four weeks, then layer richer 2.5D/3D visualisations on top of the same web stack instead of splitting focus with a separate game-engine build.
- **Success**: operators regain real-time situational awareness, demos stop desyncing, and the team has a maintainable code path for ongoing feature work.

## Current Web UI Assessment
The existing `web_ui/` implementation struggles far beyond layout polish; it fails to guarantee that the view reflects the running simulation and offers minimal tooling for analysis.

1. **Fragile data hydration & desync**
   - The client fetches a single `/api/simulation-data` snapshot on load and silently falls back to random sample data if that call fails, making it impossible to spot backend regressions (`loadSimulationData` in `simulation-ui.js`).
   - WebSocket messages are blindly applied with no turn/sequence validation or reconciliation. If the socket hiccups the UI simply reconnects without requesting missed turns, so the canvas can drift away from the server's authoritative state.
   - There is no notion of simulation clock control (pause, step, rewind). Operators cannot freeze a turn to investigate events; the UI always runs live.

2. **Monitoring ergonomics are missing**
   - The layout is a single canvas plus a static list (`index.html`), so operators must eyeball movement with no aggregated trends, alerts, or contextual overlays.
   - Agent and world stats are rendered ad hoc from raw arrays; there is no filtering, search, cohort comparison, or notification system for critical thresholds.
   - Log handling keeps only the last ~100 entries and offers no severity filtering or linking events to map entities, making after-the-fact analysis arduous.

3. **Maintainability blockers**
   - The UI is handwritten DOM/CSS without modular structure, unit tests, or state management. Small changes require editing monolithic scripts, and there is no shared design system or storybook to align contributions.
   - Data contracts between the simulation and UI live in implicit JavaScript object shapes, so backend changes routinely break the front end without type checks.

## Why Web UI is the Right Bet
1. **Cross-platform reach & frictionless delivery**: a responsive web client serves laptops, tablets, control-room displays, and investor demos instantly. Progressive enhancement keeps low-powered devices functional while letting high-end browsers access WebGL/WebGPU overlays.
2. **Unified pipeline for immersive elements**: modern web stacks (React + Three.js/Babylon.js, deck.gl, WebGPU) can deliver 2.5D/3D slices without rewriting the control plane. We can embed cinematic flythroughs and spatial layers inside the dashboard instead of building and maintaining a native game client.
3. **Team velocity & quality**: TypeScript, component libraries, and browser-based testing unlock fast iteration, CI integration, and shared UI primitives. Continuous deployment is trivial compared to shipping native binaries.
4. **Integration with existing tooling**: the simulation back end already emits JSON. Web clients can subscribe via WebSocket or Server-Sent Events, leverage GraphQL/REST for historical queries, and feed telemetry back into Grafana/Prometheus without bespoke glue.

## Target Architecture & Feature Set
### Data Synchronisation & Reliability
- Replace the ad hoc snapshot/WebSocket combo with a **versioned turn stream**: every payload carries `turn_id`, `revision`, and `hash`. The client acknowledges the latest applied turn so the server can resend gaps.
- Implement a **state store** (Redux Toolkit, Zustand, or Vuex) with derived selectors for map, cohorts, and alerts. Keep snapshots immutable per turn to enable time travel debugging.
- Support **replay buffers**: persist the last N turns client-side so operators can scrub backwards without reloading.
- Provide **offline diagnostics**: show explicit banners when sample data is loaded, expose connection latency, and surface backend schema mismatches instead of failing silently.

### Operator Experience
- **Composable layout**: adopt a resizable pane system (map, event timeline, analytics) with saved workspaces per persona (operations vs. research vs. demo).
- **Turn control & sync indicators**: add pause/play/step buttons, show "live" vs. "investigating turn X" badge, and ensure log/timeline panes stay in lockstep with the map.
- **Event timeline & alerting**: annotate turns with major events (conflicts, starvation, policy changes), filter by severity, and let operators jump directly to the corresponding agent cluster.
- **Agent intelligence**: include cohort filters (faction, morale band, role), inline sparklines for health/resources, and quick comparisons between selected agents or groups.
- **Contextual overlays**: layer heatmaps (resource availability, morale, conflict probability) and tooltips driven by aggregated statistics rather than raw values.

### Engineering Foundations
- Scaffold the UI with **React + Vite + TypeScript** (or SvelteKit + TypeScript) for modularity, fast HMR, and tree-shakeable builds.
- Establish a **component library** (Storybook + Tailwind or CSS Modules) with tokens for color, typography, and spacing that match Wei's desired visual language.
- Define a **typed contract**: generate TypeScript types from OpenAPI/JSON Schema, maintain compatibility tests against simulation snapshots, and validate incoming WebSocket payloads.
- Add **testing and observability**: Vitest/Jest for unit tests, Playwright for end-to-end sync scenarios, and client telemetry (turn latency, dropped frames, socket reconnects) streamed to Grafana.

## Implementation Plan (4-Week Push)
1. **Week 0–1: Foundations**
   - Run a joint discovery session with operators to map workflows and metrics.
   - Stand up the new TypeScript/Vite project, CI pipeline, and Storybook playground.
   - Define the turn-based messaging protocol, implement basic store/reducer scaffolding, and expose a mock data service for rapid UI iteration.

2. **Week 2: Core Monitoring Features**
   - Deliver the resizable layout (map + timeline + analytics) with real data bindings.
   - Implement pause/step controls, turn scrubber, and sync indicators wired into the state store.
   - Add cohort filters, agent search, and alert cards (thresholds for starvation, conflict, production stalls).

3. **Week 3: Reliability & Ergonomics**
   - Harden WebSocket reconnection with ack/rewind, surface backend schema drift alerts, and add offline/sample mode banners.
   - Ship log/timeline correlation, severity filters, and ability to pin turns for later review.
   - Add Playwright regression suite covering load, pause/resume, and filter scenarios; capture baseline performance metrics.

4. **Week 4: Polish & Demo Readiness**
   - Layer in contextual overlays (heatmaps, cluster annotations) and cinematic camera presets for demos.
   - Run usability sessions with Wei and operators, iterate on visual hierarchy, and document operational runbooks.
   - Instrument telemetry dashboards (load time, socket health, FPS) and set alert thresholds for ops.

## Post-MVP Enhancements
- Integrate historical queries (time-travel beyond local buffer) via an API that streams archived turns.
- Experiment with WebGPU-powered 3D modes embedded inside the web client for investor showcases.
- Enable collaborative annotations: allow multiple viewers to comment on turns, share focus modes, and capture snapshots for reports.

## Immediate Next Steps
1. Confirm backend resources to implement versioned turn streaming and schema generation.
2. Kick off design sprints to produce wireframes for the three-pane layout, timeline, and overlays.
3. Bootstrap the new TypeScript project, migrate existing canvas rendering into a reusable map component, and wire it to mock turn data.
4. Draft a telemetry spec capturing connection quality, render performance, and user actions for future tuning.

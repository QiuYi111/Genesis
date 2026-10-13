# Monitoring Console Foundations

This document captures the initial implementation that follows the latest Web UI and interactive roleplay plans. The new Vite + React project under `web_ui/monitor/` provides the scaffolding for the three-pane monitoring layout, turn-synchronised controls, and the interaction ledger required for operator roleplay.

## Key Capabilities

- **Versioned turn buffer**: the Zustand store keeps the latest 120 turns, exposes live/scrubbing modes, and tracks connection health for future ack/rewind protocols.
- **Composable panes**: the layout renders map, timeline, analytics, and interaction panels with responsive CSS, matching the discovery sketches.
- **Mock turn stream**: a deterministic generator emits turn payloads with hashes, latency measurements, events, cohorts, heatmap cells, and interactions. This unlocks rapid UI iteration before the backend protocol lands.
- **Interactive ledger**: operator, agent, and Trinity exchanges are recorded per turn for replay-ready UX, aligning with the interactive roleplay roadmap.
- **Testability**: the store ships with Vitest coverage to guarantee buffer retention and live-mode behaviour.

## Next Steps

1. Replace the mock stream with the real versioned WebSocket protocol once the backend exposes it.
2. Hook the map panel to deck.gl or WebGL rendering for richer spatial context and camera presets.
3. Expand the interaction ledger with filtering, search, and export APIs so ops can annotate critical turns.
4. Add Playwright end-to-end checks that validate pause/resume, scrub, and offline banner flows.

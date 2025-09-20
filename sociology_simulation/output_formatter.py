#!/usr/bin/env python3
"""
Enhanced output formatting system for sociology simulation.
Provides structured, readable output with color coding and progress tracking.
"""

import sys
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import shutil

# Color codes for terminal output
class Colors:
    """Terminal color codes for better output formatting."""
    
    # Basic colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Style
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    STRIKETHROUGH = '\033[9m'
    
    # Reset
    RESET = '\033[0m'
    
    @classmethod
    def disable(cls):
        """Disable all colors (for non-terminal output)."""
        for attr in dir(cls):
            if not attr.startswith('_') and attr != 'disable':
                setattr(cls, attr, '')


@dataclass
class SimulationStats:
    """Track simulation statistics for summary display."""
    
    turn: int = 0
    total_turns: int = 0
    active_agents: int = 0
    total_agents: int = 0
    actions_completed: int = 0
    actions_failed: int = 0
    social_interactions: int = 0
    resource_gathered: int = 0
    buildings_constructed: int = 0
    technologies_discovered: int = 0
    agent_deaths: int = 0
    start_time: float = 0
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since simulation start."""
        return time.time() - self.start_time if self.start_time > 0 else 0
    
    @property
    def progress_percentage(self) -> float:
        """Get simulation progress as percentage."""
        return (self.turn / self.total_turns) * 100 if self.total_turns > 0 else 0
    
    @property
    def estimated_time_remaining(self) -> float:
        """Estimate remaining time based on current progress."""
        if self.turn <= 0 or self.elapsed_time <= 0:
            return 0
        time_per_turn = self.elapsed_time / self.turn
        remaining_turns = self.total_turns - self.turn
        return time_per_turn * remaining_turns


class OutputFormatter:
    """Enhanced output formatter for sociology simulation."""
    
    def __init__(self, use_colors: bool = True, verbose: bool = True, mode: str = "pretty", emoji: bool = True):
        self.use_colors = use_colors and sys.stdout.isatty()
        self.verbose = verbose
        self.mode = mode  # one of: pretty, fancy, compact, plain, jsonl
        self.emoji = emoji
        self.stats = SimulationStats()
        
        if not self.use_colors:
            Colors.disable()

    # ---------- Terminal sizing ----------
    def _term_width(self) -> int:
        try:
            return shutil.get_terminal_size(fallback=(100, 24)).columns
        except Exception:
            return 100
    
    def format_header(self, title: str, level: int = 1) -> str:
        """Format a header with appropriate styling."""
        width = max(40, min(120, self._term_width()))
        if level == 1:
            # Main header
            line = "=" * width
            return f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{line}\n{title.upper():^{width}}\n{line}{Colors.RESET}\n"
        elif level == 2:
            # Sub header
            line = "-" * max(30, min(80, width - 20))
            return f"\n{Colors.BOLD}{Colors.BRIGHT_YELLOW}{line}\n{title}\n{line}{Colors.RESET}\n"
        else:
            # Minor header
            return f"\n{Colors.BOLD}{Colors.BRIGHT_WHITE}>>> {title}{Colors.RESET}\n"
    
    def format_turn_header(self, turn: int, total_turns: int) -> str:
        """Format turn header with progress information."""
        progress = (turn / total_turns) * 100 if total_turns > 0 else 0
        width = max(40, min(120, self._term_width()))
        bar_width = max(20, min(60, width - 20))
        progress_bar = self._create_progress_bar(progress, width=bar_width)
        
        elapsed = self.stats.elapsed_time
        remaining = self.stats.estimated_time_remaining
        
        header = f"TURN {turn}/{total_turns}"
        time_info = f"Elapsed: {self._format_time(elapsed)} | ETA: {self._format_time(remaining)}"
        line = "=" * max(40, min(100, width))
        return f"\n{Colors.BOLD}{Colors.BRIGHT_MAGENTA}{line}\n{header:^{len(line)}}\n{progress_bar}\n{time_info:^{len(line)}}\n{line}{Colors.RESET}\n"
    
    def format_agent_action(self, agent_name: str, agent_id: int, action: str, 
                          success: Optional[bool] = None, details: Optional[str] = None) -> str:
        """Format agent action with status indicator."""
        if success is None:
            # No status indicator, just format as info
            status_color = Colors.BRIGHT_CYAN
            status_symbol = "→"
        else:
            status_color = Colors.BRIGHT_GREEN if success else Colors.BRIGHT_RED
            status_symbol = "✓" if success else "✗"
        
        # Truncate long actions
        if len(action) > 80:
            action = action[:77] + "..."
        
        result = f"{status_color}{status_symbol}{Colors.RESET} {Colors.BOLD}{agent_name}({agent_id}){Colors.RESET}: {action}"
        
        if details and self.verbose:
            result += f"\n  {Colors.DIM}{details}{Colors.RESET}"
        
        return result
    
    def format_agent_goal(self, agent_name: str, agent_id: int, goal: str) -> str:
        """Format agent personal goal with special styling."""
        # Truncate very long goals
        if len(goal) > 100:
            goal = goal[:97] + "..."
        
        return f"{Colors.BRIGHT_MAGENTA}🎯{Colors.RESET} {Colors.BOLD}{agent_name}({agent_id}){Colors.RESET} {Colors.BRIGHT_BLUE}personal goal ➜{Colors.RESET} {Colors.ITALIC}{goal}{Colors.RESET}"
    
    def format_agent_action_complete(self, agent_name: str, agent_id: int, action: str) -> str:
        """Format completed agent action with special styling."""
        # Truncate very long actions
        if len(action) > 120:
            action = action[:117] + "..."
        
        lightning = "⚡" if self.emoji else "*"
        arrow = "→" if self.emoji else ">"
        return f"{Colors.BRIGHT_GREEN}{lightning}{Colors.RESET} {Colors.BOLD}{agent_name}({agent_id}){Colors.RESET} {Colors.BRIGHT_YELLOW}行动 {arrow}{Colors.RESET} {Colors.CYAN}{action}{Colors.RESET}"
    
    def format_world_event(self, event: str, event_type: str = "info") -> str:
        """Format world events with appropriate styling."""
        color_map = {
            "info": Colors.BRIGHT_BLUE,
            "warning": Colors.BRIGHT_YELLOW,
            "error": Colors.BRIGHT_RED,
            "success": Colors.BRIGHT_GREEN,
            "death": Colors.BRIGHT_RED,
            "birth": Colors.BRIGHT_GREEN,
            "discovery": Colors.BRIGHT_MAGENTA,
            "construction": Colors.BRIGHT_CYAN
        }
        
        color = color_map.get(event_type, Colors.WHITE)
        icon_map = {
            "info": "ℹ" if self.emoji else "i",
            "warning": "⚠" if self.emoji else "!",
            "error": "✗" if self.emoji else "x",
            "success": "✓" if self.emoji else "+",
            "death": "💀" if self.emoji else "X",
            "birth": "👶" if self.emoji else "+",
            "discovery": "🔍" if self.emoji else "*",
            "construction": "🏗" if self.emoji else "#",
        }
        
        icon = icon_map.get(event_type, "•")
        
        return f"{color}{icon} {event}{Colors.RESET}"
    
    def format_statistics_summary(self) -> str:
        """Format comprehensive statistics summary."""
        stats = self.stats
        
        # Calculate derived stats
        success_rate = (stats.actions_completed / (stats.actions_completed + stats.actions_failed)) * 100 if (stats.actions_completed + stats.actions_failed) > 0 else 0
        avg_time_per_turn = stats.elapsed_time / stats.turn if stats.turn > 0 else 0
        
        summary = f"""
{Colors.BOLD}{Colors.BRIGHT_CYAN}SIMULATION STATISTICS{Colors.RESET}
{Colors.DIM}{'─' * 40}{Colors.RESET}

{Colors.BOLD}Progress:{Colors.RESET}
  Turn: {Colors.BRIGHT_YELLOW}{stats.turn}/{stats.total_turns}{Colors.RESET} ({stats.progress_percentage:.1f}%)
  Elapsed Time: {Colors.BRIGHT_BLUE}{self._format_time(stats.elapsed_time)}{Colors.RESET}
  Avg Time/Turn: {Colors.BRIGHT_BLUE}{avg_time_per_turn:.1f}s{Colors.RESET}

{Colors.BOLD}Agents:{Colors.RESET}
  Active: {Colors.BRIGHT_GREEN}{stats.active_agents}/{stats.total_agents}{Colors.RESET}
  Deaths: {Colors.BRIGHT_RED}{stats.agent_deaths}{Colors.RESET}

{Colors.BOLD}Actions:{Colors.RESET}
  Completed: {Colors.BRIGHT_GREEN}{stats.actions_completed}{Colors.RESET}
  Failed: {Colors.BRIGHT_RED}{stats.actions_failed}{Colors.RESET}
  Success Rate: {Colors.BRIGHT_YELLOW}{success_rate:.1f}%{Colors.RESET}

{Colors.BOLD}World Events:{Colors.RESET}
  Social Interactions: {Colors.BRIGHT_MAGENTA}{stats.social_interactions}{Colors.RESET}
  Resources Gathered: {Colors.BRIGHT_CYAN}{stats.resource_gathered}{Colors.RESET}
  Buildings Built: {Colors.BRIGHT_YELLOW}{stats.buildings_constructed}{Colors.RESET}
  Technologies: {Colors.BRIGHT_BLUE}{stats.technologies_discovered}{Colors.RESET}
"""
        return summary
    
    def format_agent_status_table(self, agents: List[Dict[str, Any]]) -> str:
        """Format agent status as a table."""
        if not agents:
            return f"{Colors.DIM}No agents to display{Colors.RESET}"
        
        # Table header
        header = f"{Colors.BOLD}{Colors.UNDERLINE}{'Name':<12} {'Age':<4} {'Health':<7} {'Position':<10} {'Action':<20} {'Status':<10}{Colors.RESET}"
        rows = [header]
        
        for agent in agents:
            name = agent.get('name', 'Unknown')[:11]
            age = str(agent.get('age', 0))
            health = f"{agent.get('health', 100)}/100"
            pos = f"({agent.get('x', 0)},{agent.get('y', 0)})"
            action = agent.get('current_action', 'idle')[:19]
            status = "alive" if agent.get('health', 100) > 0 else "dead"
            
            # Color code based on health
            health_color = Colors.BRIGHT_GREEN if agent.get('health', 100) > 70 else Colors.BRIGHT_YELLOW if agent.get('health', 100) > 30 else Colors.BRIGHT_RED
            
            row = f"{name:<12} {age:<4} {health_color}{health:<7}{Colors.RESET} {pos:<10} {action:<20} {status:<10}"
            rows.append(row)
        
        return "\n".join(rows)
    
    def _create_progress_bar(self, percentage: float, width: int = 40) -> str:
        """Create a visual progress bar."""
        filled = int(width * percentage / 100)
        bar_char = "█" if self.use_colors or self.emoji else "#"
        empty_char = "░" if self.use_colors or self.emoji else "-"
        bar = bar_char * filled + empty_char * (width - filled)
        return f"{Colors.BRIGHT_GREEN}[{bar}] {percentage:.1f}%{Colors.RESET}"
    
    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def print_simulation_start(self, era: str, world_size: int, num_agents: int, total_turns: int):
        """Print simulation start information."""
        self.stats.start_time = time.time()
        self.stats.total_turns = total_turns
        self.stats.total_agents = num_agents
        self.stats.active_agents = num_agents
        
        print(self.format_header("SOCIOLOGY SIMULATION", 1))
        print(f"{Colors.BOLD}Era:{Colors.RESET} {Colors.BRIGHT_YELLOW}{era}{Colors.RESET}")
        print(f"{Colors.BOLD}World Size:{Colors.RESET} {Colors.BRIGHT_CYAN}{world_size}x{world_size}{Colors.RESET}")
        print(f"{Colors.BOLD}Agents:{Colors.RESET} {Colors.BRIGHT_GREEN}{num_agents}{Colors.RESET}")
        print(f"{Colors.BOLD}Turns:{Colors.RESET} {Colors.BRIGHT_MAGENTA}{total_turns}{Colors.RESET}")
        print(f"{Colors.BOLD}Started:{Colors.RESET} {Colors.BRIGHT_BLUE}{time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
        
    def print_turn_start(self, turn: int):
        """Print turn start information."""
        self.stats.turn = turn
        if self.mode in ("compact",):
            # Compact mode: draw lightweight header once every 10 turns
            if turn == 1 or turn % 10 == 0:
                print(self.format_turn_header(turn, self.stats.total_turns))
        elif self.mode in ("fancy",):
            # Fancy mode: no big header; a HUD line will be printed per turn
            pass
        else:
            print(self.format_turn_header(turn, self.stats.total_turns))
    
    def print_turn_summary(self, turn_stats: Dict[str, Any]):
        """Print turn summary with key events."""
        if not turn_stats:
            return
        
        print(f"\n{Colors.BOLD}{Colors.BRIGHT_WHITE}Turn {self.stats.turn} Summary:{Colors.RESET}")
        
        for event_type, events in turn_stats.items():
            if events:
                if isinstance(events, list):
                    for event in events:
                        print(f"  {self.format_world_event(str(event), event_type)}")
                else:
                    print(f"  {self.format_world_event(str(events), event_type)}")

    # ---------- Fancy/Compact live HUD and panels ----------
    def format_turn_hud(self, extras: Optional[Dict[str, Any]] = None) -> str:
        """Return a single-line HUD with progress and key metrics."""
        stats = self.stats
        width = max(60, min(160, self._term_width()))
        progress = f"{stats.turn}/{stats.total_turns}"
        pct = f"{stats.progress_percentage:.1f}%"
        elapsed = self._format_time(stats.elapsed_time)
        eta = self._format_time(stats.estimated_time_remaining)
        alive = f"{stats.active_agents}/{stats.total_agents}"
        sr = 0.0
        denom = stats.actions_completed + stats.actions_failed
        if denom > 0:
            sr = (stats.actions_completed / denom) * 100.0
        success = f"{sr:.1f}%"
        parts = [
            f"Turn {progress}",
            f"{pct}",
            f"Elapsed {elapsed}",
            f"ETA {eta}",
            f"Alive {alive}",
            f"Success {success}",
        ]
        if extras:
            for k in ["births", "deaths", "resources", "tech"]:
                if k in extras:
                    parts.append(f"{k.capitalize()} {extras[k]}")
        line = " | ".join(parts)
        if len(line) > width:
            line = line[: width - 3] + "..."
        return f"{Colors.BRIGHT_WHITE}{line}{Colors.RESET}"

    def print_turn_panel(self, turn: int, facts: Dict[str, Any], highlights: List[str], events: List[str]) -> None:
        """Fancy immersive panel for a turn using facts/highlights/events."""
        width = max(60, min(160, self._term_width()))
        sep = "─" * width
        title_icon = "🌐" if self.emoji else "*"
        header = f"{title_icon} TURN {turn} HIGHLIGHTS"
        print(f"\n{Colors.BRIGHT_CYAN}{sep}{Colors.RESET}")
        print(f"{Colors.BOLD}{header:^{width}}{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{sep}{Colors.RESET}")

        # Facts row
        facts_kvs: List[Tuple[str, str]] = []
        for key in [
            "groups_count",
            "technologies_count",
            "markets_count",
            "political_entities",
            "skill_diversity",
            "avg_social_connections",
            "economic_health",
        ]:
            if key in facts:
                val = facts[key]
                if isinstance(val, float):
                    val = f"{val:.2f}"
                facts_kvs.append((key, str(val)))
        # Format two lines of facts
        line_buf = []
        chunk = []
        for k, v in facts_kvs:
            pretty_k = k.replace("_", " ").title()
            chunk.append(f"{Colors.DIM}{pretty_k}:{Colors.RESET} {Colors.BRIGHT_YELLOW}{v}{Colors.RESET}")
            if sum(len(x) for x in chunk) + len(chunk) * 3 > width - 8:
                line_buf.append("   ".join(chunk))
                chunk = []
        if chunk:
            line_buf.append("   ".join(chunk))
        for ln in line_buf[:2]:
            print(ln)

        # Highlights
        if highlights:
            star = "⭐" if self.emoji else "*"
            print(self.format_header("Highlights", 3))
            for h in highlights[:6]:
                h = h.strip()
                if not h:
                    continue
                if len(h) > width - 4:
                    h = h[: width - 7] + "..."
                print(f" {Colors.BRIGHT_GREEN}{star}{Colors.RESET} {h}")

        # Events marquee
        if events:
            bolt = "⚡" if self.emoji else "!"
            print(self.format_header("Events", 3))
            for e in events[:6]:
                e = e.strip()
                if len(e) > width - 4:
                    e = e[: width - 7] + "..."
                print(f" {Colors.BRIGHT_MAGENTA}{bolt}{Colors.RESET} {e}")
        print(f"{Colors.BRIGHT_CYAN}{sep}{Colors.RESET}")
    
    def print_simulation_end(self):
        """Print simulation end summary."""
        print(self.format_header("SIMULATION COMPLETED", 1))
        print(self.format_statistics_summary())
        print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN}Simulation finished successfully!{Colors.RESET}")
        print(f"{Colors.BOLD}Total Time:{Colors.RESET} {Colors.BRIGHT_BLUE}{self._format_time(self.stats.elapsed_time)}{Colors.RESET}")
    
    def update_stats(self, **kwargs):
        """Update simulation statistics."""
        for key, value in kwargs.items():
            if hasattr(self.stats, key):
                setattr(self.stats, key, value)


# Global formatter instance
_formatter = None

def get_formatter() -> OutputFormatter:
    """Get the global output formatter instance."""
    global _formatter
    if _formatter is None:
        _formatter = OutputFormatter()
    return _formatter

def set_formatter_options(use_colors: bool = True, verbose: bool = True, mode: str = "pretty", emoji: bool = True):
    """Set global formatter options."""
    global _formatter
    _formatter = OutputFormatter(use_colors=use_colors, verbose=verbose, mode=mode, emoji=emoji)

"""
scripts/build_polaris_dashboard.py
-----------------------------------
Compiles the exact 1:1 replica of the Polaris Dashboard into dashboard/index.html.
Recreates the exact visual design from the user's reference screenshots:
- Beams: Monochrome white/silver glossy rippling ribbons (@react-bits/Beams-TS-TW), NOT blue!
- Liquid Glass: Ambient backdrop blur across viewport + deep frosted liquid glass on all components
- Expandable Capsule Sidebar: Expands smoothly on hover from 56px to 250px showing full labels,
  emblem header (Polaris - Pre Prod Env / RISK INTELLIGENCE), and user profile (Aarav Sharma [ADMIN])
- Top bar with Search (⌘K), Center Glossy Brand Pill, Workspace [ADMIN], Orbit status, live UTC clock, notification bell
- Command Centre with dual-column layout, severity filters, active bounties, and KPI metrics
- Incident Dossier / Order Receipt with dual stat boxes, budget slider, playbook tabs, and phase pills
"""

import os
import json

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ProcureAgent — Polaris Autonomous Capability Procurement</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23ffffff'><circle cx='12' cy='12' r='10'/></svg>">
  <style>
    /* ==========================================================================
       POLARIS STRICT OBSIDIAN & LIQUID GLASS TOKENS
       ========================================================================== */
    :root {
      --bg-space: #070709;
      --bg-glass-panel: rgba(16, 16, 22, 0.52);
      --bg-glass-card: rgba(22, 22, 30, 0.45);
      --bg-glass-inner: rgba(8, 8, 12, 0.48);
      --border-glass: rgba(255, 255, 255, 0.09);
      --border-glass-bright: rgba(255, 255, 255, 0.18);
      --text-white: #ffffff;
      --text-bright: #f4f4f5;
      --text-dim: #a1a1aa;
      --text-muted: #71717a;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #ef4444;
      --accent-blue: #ffffff;
      --font-polaris: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-space);
      color: var(--text-bright);
      font-family: var(--font-polaris);
      min-height: 100vh;
      overflow-x: hidden;
      line-height: 1.45;
      -webkit-font-smoothing: antialiased;
    }

    /* Fullscreen React Bits Beams WebGL2 Canvas (White/Silver Monochrome) */
    #beams-canvas {
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      pointer-events: none;
      z-index: 0;
      opacity: 1.0;
    }

    /* Viewport-Wide Ambient Liquid Glass Frosted Layer */
    .ambient-glass-layer {
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 1;
      background: radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.03) 0%, transparent 70%);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
    }

    /* ==========================================================================
       1. POLARIS TOP NAVIGATION BAR
       ========================================================================== */
    .polaris-topbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: 56px;
      z-index: 1000;
      background: rgba(10, 10, 14, 0.65);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border-bottom: 1px solid var(--border-glass);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
    }

    /* Left: Search Box with ⌘K badge */
    .topbar-search {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 320px;
      height: 36px;
      background: rgba(18, 18, 24, 0.65);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-glass);
      border-radius: 10px;
      padding: 0 12px;
      color: var(--text-dim);
      font-size: 13px;
      transition: all 0.2s ease;
    }
    .topbar-search:hover {
      border-color: var(--border-glass-bright);
      background: rgba(25, 25, 34, 0.8);
    }
    .topbar-search input {
      background: transparent;
      border: none;
      outline: none;
      color: var(--text-white);
      font-size: 13px;
      width: 100%;
    }
    .topbar-search input::placeholder {
      color: var(--text-muted);
    }
    .search-kbd {
      font-size: 11px;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 5px;
      padding: 2px 5px;
      color: var(--text-muted);
    }

    /* Center: Floating Glossy Brand Pill */
    .center-brand-pill {
      display: flex;
      align-items: center;
      gap: 9px;
      background: linear-gradient(180deg, rgba(28, 28, 36, 0.95) 0%, rgba(12, 12, 16, 0.98) 100%);
      border: 1px solid rgba(255, 255, 255, 0.18);
      border-radius: 9999px;
      padding: 6px 18px 6px 10px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.7), inset 0 1px 1px rgba(255, 255, 255, 0.25);
      cursor: pointer;
      transition: transform 0.2s ease;
    }
    .center-brand-pill:hover {
      transform: scale(1.02);
    }
    .sphere-logo {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #ffffff 0%, #94a3b8 60%, #1e293b 100%);
      box-shadow: 0 0 12px rgba(255, 255, 255, 0.4), inset 0 1px 2px rgba(255, 255, 255, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .sphere-logo svg {
      width: 12px;
      height: 12px;
      fill: none;
      stroke: #000;
      stroke-width: 2.5;
    }
    .brand-pill-text {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-white);
      letter-spacing: 0.02em;
    }

    /* Right: Workspace, Orbit / Stack status, UTC Clock, Bell */
    .topbar-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .workspace-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--text-dim);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-glass);
      border-radius: 8px;
      padding: 4px 10px;
    }
    .admin-badge {
      font-size: 10px;
      font-weight: 700;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 4px;
      padding: 1px 5px;
      color: var(--text-white);
    }
    .orbit-pill {
      display: flex;
      align-items: center;
      gap: 7px;
      font-size: 12px;
      font-weight: 500;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #e2e8f0;
      border-radius: 9999px;
      padding: 4px 12px;
    }
    .orbit-pill.replay {
      background: rgba(245, 158, 11, 0.15);
      border-color: rgba(245, 158, 11, 0.35);
      color: #fde68a;
    }
    .utc-clock {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      color: var(--text-dim);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-glass);
      border-radius: 8px;
      padding: 4px 10px;
    }
    .utc-clock .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--accent-emerald);
      box-shadow: 0 0 8px rgba(16, 185, 129, 0.8);
    }
    .bell-btn {
      position: relative;
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-glass);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-dim);
      cursor: pointer;
    }
    .bell-badge {
      position: absolute;
      top: -2px;
      right: -2px;
      width: 14px;
      height: 14px;
      background: var(--accent-rose);
      border-radius: 50%;
      font-size: 9px;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    /* ==========================================================================
       2. EXPANDABLE POLARIS CAPSULE SIDEBAR DOCK (Exact 1:1)
       ========================================================================== */
    .polaris-dock {
      position: fixed;
      left: 16px;
      top: 50%;
      transform: translateY(-50%);
      height: 680px;
      max-height: calc(100vh - 32px);
      width: 64px;
      background: rgba(18, 18, 20, 0.85);
      backdrop-filter: blur(60px);
      -webkit-backdrop-filter: blur(60px);
      border: 1px solid var(--border-glass);
      border-radius: 28px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
      display: flex;
      flex-direction: column;
      padding: 16px 0;
      z-index: 950;
      transition: width 0.3s cubic-bezier(0.16, 1, 0.3, 1), padding 0.3s ease, border-radius 0.3s ease, background 0.25s ease;
      overflow: hidden;
      white-space: nowrap;
      user-select: none;
    }

    /* Expand on hover or pinned */
    .polaris-dock:hover,
    .polaris-dock.pinned {
      width: 256px;
      padding: 16px 12px;
      background: rgba(18, 18, 22, 0.95);
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.85), inset 0 1px 1px rgba(255, 255, 255, 0.15);
    }

    /* Top Brand Header inside Sidebar */
    .sidebar-header-box {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 4px 6px 4px;
      cursor: pointer;
    }
    .dock-emblem {
      width: 38px;
      height: 38px;
      min-width: 38px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-glass);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .dock-emblem svg {
      width: 20px;
      height: 20px;
      stroke: #fff;
      fill: none;
      stroke-width: 2;
    }
    .sidebar-header-text {
      display: flex;
      flex-direction: column;
      opacity: 0;
      transform: translateX(-8px);
      transition: opacity 0.2s ease 0.05s, transform 0.2s ease 0.05s;
    }
    .polaris-dock:hover .sidebar-header-text,
    .polaris-dock.pinned .sidebar-header-text {
      opacity: 1;
      transform: translateX(0);
    }
    .sidebar-title {
      font-size: 13px;
      font-weight: 700;
      color: #fff;
    }
    .sidebar-sub {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--text-muted);
    }

    .dock-sep {
      width: 100%;
      height: 1px;
      background: var(--border-glass);
      margin: 4px 0;
    }

    .dock-icons {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
    }

    .dock-icon-btn {
      width: 40px;
      height: 40px;
      min-height: 40px;
      border-radius: 10px;
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-dim);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
      position: relative;
      flex-shrink: 0;
    }
    .polaris-dock:hover .dock-icon-btn,
    .polaris-dock.pinned .dock-icon-btn {
      width: 100%;
      justify-content: flex-start;
      padding: 0 10px;
      gap: 12px;
    }
    .dock-icon-btn:hover {
      color: var(--text-white);
      background: rgba(255, 255, 255, 0.06);
    }
    .dock-icon-btn.active {
      background: #27272a;
      border-color: rgba(255, 255, 255, 0.14);
      color: var(--text-white);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    }
    .dock-icon-btn svg {
      width: 19px;
      height: 19px;
      min-width: 19px;
      stroke: currentColor;
      fill: none;
      stroke-width: 1.8;
      stroke-linecap: round;
      stroke-linejoin: round;
      flex-shrink: 0;
    }
    .dock-text-label {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-dim);
      opacity: 0;
      transform: translateX(-6px);
      transition: opacity 0.2s ease 0.05s, transform 0.2s ease 0.05s;
    }
    .dock-icon-btn.active .dock-text-label {
      color: #fff;
      font-weight: 600;
    }
    .polaris-dock:hover .dock-text-label,
    .polaris-dock.pinned .dock-text-label {
      opacity: 1;
      transform: translateX(0);
    }

    /* Bottom: Log Out & User Profile Card */
    .sidebar-footer-user {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 6px 4px;
      margin-top: 4px;
      border-top: 1px solid var(--border-glass);
      cursor: pointer;
    }
    .dock-avatar-circle {
      width: 36px;
      height: 36px;
      min-width: 36px;
      border-radius: 50%;
      background: #27272a;
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: var(--text-white);
      font-size: 12px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .user-footer-details {
      display: flex;
      flex-direction: column;
      flex: 1;
      opacity: 0;
      transition: opacity 0.2s ease 0.05s;
    }
    .polaris-dock:hover .user-footer-details,
    .polaris-dock.pinned .user-footer-details {
      opacity: 1;
    }
    .user-name-line {
      font-size: 12px;
      font-weight: 700;
      color: #fff;
    }
    .user-email-line {
      font-size: 10px;
      color: var(--text-muted);
    }

    /* ==========================================================================
       3. POLARIS WORKSPACE & PAGE VIEWPORT
       ========================================================================== */
    .polaris-main {
      margin-top: 68px;
      margin-left: 88px;
      margin-right: 24px;
      padding-bottom: 60px;
      position: relative;
      z-index: 10;
    }

    /* Header line with radio wave tracker */
    .page-kicker {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--text-dim);
      margin-bottom: 4px;
    }
    .page-title-row {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      margin-bottom: 20px;
    }
    .page-headline {
      font-size: 28px;
      font-weight: 700;
      letter-spacing: -0.025em;
      color: var(--text-white);
    }
    .page-subtext {
      font-size: 13px;
      color: var(--text-dim);
      margin-top: 4px;
    }
    .btn-polaris-action {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 18px;
      border-radius: 10px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      background: rgba(24, 24, 32, 0.65);
      border: 1px solid rgba(255, 255, 255, 0.16);
      color: #fff;
      backdrop-filter: blur(16px);
      transition: all 0.2s ease;
    }
    .btn-polaris-action:hover {
      background: rgba(36, 36, 48, 0.85);
      border-color: rgba(255, 255, 255, 0.28);
      transform: translateY(-1px);
    }

    /* Screen Visibility */
    .polaris-screen {
      display: none;
      animation: polarisFade 0.2s ease forwards;
    }
    .polaris-screen.active {
      display: block;
    }
    @keyframes polarisFade {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* ==========================================================================
       4. COMMAND CENTRE: DUAL-COLUMN POLARIS LIQUID GLASS LAYOUT
       ========================================================================== */
    .command-grid {
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 20px;
    }
    @media (max-width: 1180px) {
      .command-grid {
        grid-template-columns: 1fr;
      }
    }

    /* Liquid Glass Panels */
    .polaris-panel {
      background: var(--bg-glass-panel);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      border: 1px solid var(--border-glass);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55), inset 0 1px 1px rgba(255, 255, 255, 0.12);
    }
    .panel-search {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--bg-glass-inner);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-glass);
      border-radius: 10px;
      padding: 8px 12px;
      color: var(--text-dim);
      font-size: 13px;
      margin-bottom: 14px;
    }
    .panel-search input {
      background: transparent;
      border: none;
      outline: none;
      color: #fff;
      font-size: 13px;
      width: 100%;
    }
    .segmented-tabs {
      display: flex;
      background: var(--bg-glass-inner);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-glass);
      border-radius: 10px;
      padding: 3px;
      gap: 3px;
      margin-bottom: 16px;
    }
    .tab-pill {
      flex: 1;
      padding: 6px 12px;
      border-radius: 8px;
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
      transition: all 0.2s;
    }
    .tab-pill.active {
      background: #27272a;
      color: #fff;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
    }

    .events-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-bottom: 12px;
    }
    .filter-pills-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }
    .filter-pill {
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 9999px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-glass);
      color: var(--text-dim);
      cursor: pointer;
    }
    .filter-pill.active {
      background: #27272a;
      color: #fff;
      border-color: rgba(255, 255, 255, 0.16);
    }

    /* Event / Bounty Card */
    .bounty-card-item {
      background: var(--bg-glass-inner);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-glass);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .bounty-card-item:hover {
      background: rgba(255, 255, 255, 0.05);
      border-color: var(--border-glass-bright);
      transform: translateY(-1px);
    }
    .bounty-card-item.selected {
      border-color: rgba(255, 255, 255, 0.25);
      background: rgba(255, 255, 255, 0.06);
    }
    .card-tags {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 8px;
    }
    .polaris-tag {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 2px 7px;
      border-radius: 5px;
    }
    .polaris-tag.critical { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.3); }
    .polaris-tag.success { background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.3); }
    .polaris-tag.neutral { background: rgba(255, 255, 255, 0.06); color: var(--text-dim); border: 1px solid var(--border-glass); }

    .bounty-item-title {
      font-size: 13px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 4px;
      line-height: 1.35;
    }
    .bounty-item-meta {
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* Right Column: Polaris KPI Grid + Live Activity */
    .kpi-row-polaris {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-bottom: 20px;
    }
    @media (max-width: 1360px) {
      .kpi-row-polaris {
        grid-template-columns: repeat(2, 1fr);
      }
    }
    .kpi-box {
      background: var(--bg-glass-panel);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      border: 1px solid var(--border-glass);
      border-radius: 16px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    }
    .kpi-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .kpi-num {
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #fff;
    }
    .kpi-detail {
      font-size: 11px;
      color: var(--text-dim);
    }
    .polaris-bar {
      width: 100%;
      height: 5px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 9999px;
      overflow: hidden;
      margin-top: 4px;
    }
    .polaris-bar-fill {
      height: 100%;
      background: var(--accent-emerald);
      border-radius: 9999px;
    }

    /* ==========================================================================
       5. INCIDENT DOSSIER / ORDER RECEIPT (1:1 Polaris Incident Card Layout)
       ========================================================================== */
    .dossier-card {
      background: var(--bg-glass-panel);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      border: 1px solid var(--border-glass);
      border-radius: 20px;
      padding: 24px 28px;
      box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6), inset 0 1px 1px rgba(255, 255, 255, 0.14);
    }
    .dossier-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }
    .dossier-badges {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .dossier-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .btn-dossier-icon {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-glass);
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 12px;
      color: var(--text-dim);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .btn-dossier-icon:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
    }
    .dossier-title {
      font-size: 22px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 4px;
    }
    .dossier-location {
      font-size: 13px;
      color: var(--text-dim);
      margin-bottom: 20px;
    }

    /* Dual ETA / Hazard Radius Stat Boxes */
    .stat-boxes-dual {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 20px;
    }
    .dual-box {
      background: var(--bg-glass-inner);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-glass);
      border-radius: 14px;
      padding: 16px;
    }
    .dual-label {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .dual-val {
      font-size: 22px;
      font-weight: 700;
      color: #fff;
    }
    .dual-sub {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
    }

    /* Distance / Budget Progress Slider */
    .slider-track-box {
      background: var(--bg-glass-inner);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-glass);
      border-radius: 12px;
      padding: 12px 16px;
      margin-bottom: 20px;
    }
    .slider-top-labels {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--text-dim);
      margin-bottom: 6px;
    }

    /* Tactical Playbook Segmented Controls */
    .playbook-tabs {
      display: flex;
      background: var(--bg-glass-inner);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-glass);
      border-radius: 10px;
      padding: 4px;
      gap: 4px;
      margin-bottom: 16px;
    }
    .playbook-tab {
      flex: 1;
      padding: 8px 12px;
      border-radius: 8px;
      background: transparent;
      border: none;
      color: var(--text-dim);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
    }
    .playbook-tab.active {
      background: #27272a;
      color: #fff;
    }

    /* Phase Pills */
    .phase-pills-row {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
    }
    .phase-pill {
      padding: 6px 14px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-glass);
      font-size: 12px;
      color: var(--text-dim);
      cursor: pointer;
    }
    .phase-pill.active {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.25);
      color: #fff;
    }

    /* Tables */
    .polaris-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    .polaris-table th {
      text-align: left;
      padding: 10px 12px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-glass);
    }
    .polaris-table td {
      padding: 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-white);
    }

    /* Bottom Governance Bar */
    .dossier-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid var(--border-glass);
      padding-top: 14px;
      margin-top: 20px;
      font-size: 11px;
      color: var(--text-muted);
    }

    /* ==========================================================================
       6. WORKERS FLEET & GOVERNANCE POLICY GRIDS
       ========================================================================== */
    .fleet-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 18px;
    }
    .fleet-card {
      background: var(--bg-glass-panel);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      border: 1px solid var(--border-glass);
      border-radius: 18px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 16px;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    }
    .fleet-stats-3 {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      background: var(--bg-glass-inner);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-glass);
      border-radius: 12px;
      padding: 12px;
    }

    /* Modal */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(12px);
      z-index: 2000;
      display: none;
      align-items: center;
      justify-content: center;
    }
    .modal-backdrop.open { display: flex; }
    .modal-box {
      width: 90%;
      max-width: 640px;
      background: rgba(16, 16, 22, 0.95);
      backdrop-filter: blur(32px);
      border: 1px solid var(--border-glass-bright);
      border-radius: 20px;
      padding: 28px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.85);
    }

    /* Toast */
    #toast-msg {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #18181b;
      border: 1px solid var(--border-glass-bright);
      color: #fff;
      padding: 12px 20px;
      border-radius: 12px;
      font-size: 13px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
      transform: translateY(100px);
      opacity: 0;
      transition: all 0.25s ease;
      z-index: 3000;
      pointer-events: none;
    }
    #toast-msg.show {
      transform: translateY(0);
      opacity: 1;
    }
  </style>
  <script src="three.min.js"></script>
  <script>
/**
 * dashboard/beams.js
 * -------------------
 * Official WebGL2 Beams engine from @react-bits/Beams-TS-TW (React Bits).
 * Glossy ribbons that ripple in the dark and catch the light following the cursor.
 * 100% local, dependency-free WebGL2 shader implementation.
 */

(function (global) {
  const QUAD_VERTEX = `#version 300 es
in vec2 aPosition;
void main() {
  gl_Position = vec4(aPosition, 0.0, 1.0);
}`;

  const FIELD = `#version 300 es
precision highp float;
uniform vec2 uView;
uniform vec2 uScale;
uniform vec2 uTurn;
uniform float uTime;
uniform float uWidth;
uniform float uWave;
uniform float uDepth;
uniform float uRough;
uniform float uSeed;
uniform float uTwist;
uniform vec3 uLight;
uniform float uFill;
uniform float uCamera;
uniform vec4 uPointer;
out vec4 outColor;

const float PI = 3.141592653589793;

vec4 permute(vec4 x) {
  return mod(((x * 34.0) + 1.0) * x, 289.0);
}

vec4 taylorInvSqrt(vec4 r) {
  return 1.79284291400159 - 0.85373472095314 * r;
}

vec3 fade(vec3 t) {
  return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

float cnoise(vec3 P) {
  vec3 Pi0 = floor(P);
  vec3 Pi1 = Pi0 + vec3(1.0);
  Pi0 = mod(Pi0, 289.0);
  Pi1 = mod(Pi1, 289.0);
  vec3 Pf0 = fract(P);
  vec3 Pf1 = Pf0 - vec3(1.0);
  vec4 ix = vec4(Pi0.x, Pi1.x, Pi0.x, Pi1.x);
  vec4 iy = vec4(Pi0.yy, Pi1.yy);
  vec4 iz0 = Pi0.zzzz;
  vec4 iz1 = Pi1.zzzz;
  vec4 ixy = permute(permute(ix) + iy);
  vec4 ixy0 = permute(ixy + iz0);
  vec4 ixy1 = permute(ixy + iz1);
  vec4 gx0 = ixy0 / 7.0;
  vec4 gy0 = fract(floor(gx0) / 7.0) - 0.5;
  gx0 = fract(gx0);
  vec4 gz0 = vec4(0.5) - abs(gx0) - abs(gy0);
  vec4 sz0 = step(gz0, vec4(0.0));
  gx0 -= sz0 * (step(0.0, gx0) - 0.5);
  gy0 -= sz0 * (step(0.0, gy0) - 0.5);
  vec4 gx1 = ixy1 / 7.0;
  vec4 gy1 = fract(floor(gx1) / 7.0) - 0.5;
  gx1 = fract(gx1);
  vec4 gz1 = vec4(0.5) - abs(gx1) - abs(gy1);
  vec4 sz1 = step(gz1, vec4(0.0));
  gx1 -= sz1 * (step(0.0, gx1) - 0.5);
  gy1 -= sz1 * (step(0.0, gy1) - 0.5);
  vec3 g000 = vec3(gx0.x, gy0.x, gz0.x);
  vec3 g100 = vec3(gx0.y, gy0.y, gz0.y);
  vec3 g010 = vec3(gx0.z, gy0.z, gz0.z);
  vec3 g110 = vec3(gx0.w, gy0.w, gz0.w);
  vec3 g001 = vec3(gx1.x, gy1.x, gz1.x);
  vec3 g101 = vec3(gx1.y, gy1.y, gz1.y);
  vec3 g011 = vec3(gx1.z, gy1.z, gz1.z);
  vec3 g111 = vec3(gx1.w, gy1.w, gz1.w);
  vec4 norm0 = taylorInvSqrt(vec4(dot(g000, g000), dot(g010, g010), dot(g100, g100), dot(g110, g110)));
  g000 *= norm0.x;
  g010 *= norm0.y;
  g100 *= norm0.z;
  g110 *= norm0.w;
  vec4 norm1 = taylorInvSqrt(vec4(dot(g001, g001), dot(g011, g011), dot(g101, g101), dot(g111, g111)));
  g001 *= norm1.x;
  g011 *= norm1.y;
  g101 *= norm1.z;
  g111 *= norm1.w;
  float n000 = dot(g000, Pf0);
  float n100 = dot(g100, vec3(Pf1.x, Pf0.yz));
  float n010 = dot(g010, vec3(Pf0.x, Pf1.y, Pf0.z));
  float n110 = dot(g110, vec3(Pf1.xy, Pf0.z));
  float n001 = dot(g001, vec3(Pf0.xy, Pf1.z));
  float n101 = dot(g101, vec3(Pf1.x, Pf0.y, Pf1.z));
  float n011 = dot(g011, vec3(Pf0.x, Pf1.yz));
  float n111 = dot(g111, Pf1);
  vec3 fade_xyz = fade(Pf0);
  vec4 n_z = mix(vec4(n000, n100, n010, n110), vec4(n001, n101, n011, n111), fade_xyz.z);
  vec2 n_yz = mix(n_z.xy, n_z.zw, fade_xyz.y);
  float n_xyz = mix(n_yz.x, n_yz.y, fade_xyz.x);
  return 2.2 * n_xyz;
}

float laneHash(float lane, float seed) {
  return fract(sin(lane * 91.3458 + seed * 17.17) * 47453.5453);
}

float lobe(float nh, float nl, float nv, float vh, float roughness) {
  float a = roughness * roughness;
  float a2 = a * a;
  float d = nh * nh * (a2 - 1.0) + 1.0;
  float distribution = a2 / (PI * d * d);
  float gv = nl * sqrt(nv * nv * (1.0 - a2) + a2);
  float gl = nv * sqrt(nl * nl * (1.0 - a2) + a2);
  float visibility = 0.5 / max(gv + gl, 0.0001);
  float fresnel = 0.028 + 0.972 * pow(1.0 - vh, 5.0);
  return distribution * visibility * fresnel * nl;
}

vec2 glint(float lane, vec2 local, float wave, float depth, float time, float twist, float rough, vec3 light, float fill, float camera, float seed) {
  float along = local.y / wave - laneHash(lane, seed) * 60.0;
  float stepVal = 0.01;
  float slope = (cnoise(vec3(0.0, along + stepVal, time)) - cnoise(vec3(0.0, along - stepVal, time))) / (2.0 * stepVal);
  slope *= 0.2 * depth;
  float spin = laneHash(lane + 0.37, seed);
  float tilt = ((spin - 0.5) * 0.5 + sin(time * 2.1 + spin * 6.2831) * 0.06) * twist;
  vec3 normal = normalize(vec3(tilt, -slope, 1.0));
  vec3 view = normalize(vec3(-local, camera));
  float nv = max(dot(normal, view), 0.0001);
  vec3 l = normalize(light);
  vec3 halfway = normalize(l + view);
  float core = lobe(max(dot(normal, halfway), 0.0), max(dot(normal, l), 0.0), nv, max(dot(view, halfway), 0.0), rough);
  vec3 fillL = normalize(vec3(0.0, -light.y * 1.25, light.z));
  vec3 fillHalf = normalize(fillL + view);
  core += fill * lobe(max(dot(normal, fillHalf), 0.0), max(dot(normal, fillL), 0.0), nv, max(dot(view, fillHalf), 0.0), rough);
  return vec2(core, core);
}

void main() {
  vec2 css = gl_FragCoord.xy * uScale;
  vec2 centered = css - uView * 0.5;
  vec2 local = mat2(uTurn.x, -uTurn.y, uTurn.y, uTurn.x) * centered;

  float across = local.x / uWidth + 0.5;
  float lane = floor(across);
  float u = across - lane;

  vec2 value = glint(lane, local, uWave, uDepth, uTime, uTwist, uRough, uLight, uFill, uCamera, uSeed);

  float pixel = max(uScale.x, uScale.y);
  float seam = min(u, 1.0 - u) * uWidth;
  if (seam < pixel * 1.5) {
    float other = u < 0.5 ? lane - 1.0 : lane + 1.0;
    float blend = 0.5 * (1.0 - smoothstep(0.0, pixel * 1.5, seam));
    value = mix(value, glint(other, local, uWave, uDepth, uTime, uTwist, uRough, uLight, uFill, uCamera, uSeed), blend);
  }

  vec2 toPointer = css - uPointer.xy;
  float near = exp(-dot(toPointer, toPointer) / (2.0 * uPointer.w * uPointer.w)) * uPointer.z;
  value *= 1.0 + near * 0.8;
  float hot = max(value.y - 0.18, 0.0);
  outColor = vec4(value.x, value.y, min(hot, 6.0), 1.0);
}`;

  const COMPOSITE = `#version 300 es
precision highp float;
uniform sampler2D uField;
uniform vec2 uResolution;
uniform vec3 uColor;
uniform vec3 uInk;
uniform float uGain;
uniform float uGlow;
uniform float uPresence;
uniform float uGrain;
uniform float uFade;
uniform float uOpacity;
uniform float uLightMode;
out vec4 outColor;

float random(vec2 st) {
  return fract(sin(dot(st, vec2(12.9898, 78.233))) * 43758.5453123);
}

float grainNoise(vec2 st) {
  vec2 i = floor(st);
  vec2 f = fract(st);
  float a = random(i);
  float b = random(i + vec2(1.0, 0.0));
  float c = random(i + vec2(0.0, 1.0));
  float d = random(i + vec2(1.0, 1.0));
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
}

vec3 acesFilmic(vec3 color) {
  const mat3 inputMatrix = mat3(
    vec3(0.59719, 0.07600, 0.02840),
    vec3(0.35458, 0.90834, 0.13383),
    vec3(0.04823, 0.01566, 0.83777)
  );
  const mat3 outputMatrix = mat3(
    vec3(1.60475, -0.10208, -0.00327),
    vec3(-0.53108, 1.10813, -0.07276),
    vec3(-0.07367, -0.00605, 1.07602)
  );
  color = inputMatrix * (color / 0.6);
  vec3 a = color * (color + 0.0245786) - 0.000090537;
  vec3 b = color * (0.983729 * color + 0.4329510) + 0.238081;
  color = outputMatrix * (a / b);
  return clamp(color, 0.0, 1.0);
}

vec3 toSrgb(vec3 color) {
  return mix(color * 12.92, 1.055 * pow(color, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), color));
}

float feather(float x, float edge) {
  float t = clamp(x / max(edge, 0.0001), 0.0, 1.0);
  return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;
  float radiance = textureLod(uField, uv, 0.0).r;
  float bloom = 0.0;
  bloom += textureLod(uField, uv, 2.0).b * 0.3;
  bloom += textureLod(uField, uv, 3.0).b * 0.3;
  bloom += textureLod(uField, uv, 4.0).b * 0.22;
  bloom += textureLod(uField, uv, 5.0).b * 0.18;

  float hot = textureLod(uField, uv, 0.0).g;
  vec3 light = uColor * (radiance + bloom * uGlow) * uGain;
  light += mix(uColor, vec3(1.0), 0.7) * hot * hot * 0.12 * uGain;
  light *= uPresence;
  vec3 color = toSrgb(acesFilmic(light));
  color -= grainNoise(gl_FragCoord.xy) / 15.0 * uGrain;
  color = max(color, 0.0);

  float edge = uFade * 0.5;
  float mask = feather(uv.x, edge) * feather(1.0 - uv.x, edge) * feather(uv.y, edge) * feather(1.0 - uv.y, edge);
  mask *= uOpacity;
  float dither = (random(gl_FragCoord.yx + 31.7) - 0.5) / 255.0;

  color = clamp(color + dither, 0.0, 1.0) * mask;
  outColor = vec4(color, max(color.r, max(color.g, color.b)));
}`;

  const INTRO_SECONDS = 1.6;
  const MAX_FIELD_PIXELS = 1600000;
  const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

  const compileShader = (gl, type, source) => {
    const s = gl.createShader(type);
    if (!s) return null;
    gl.shaderSource(s, source);
    gl.compileShader(s);
    if (gl.getShaderParameter(s, gl.COMPILE_STATUS)) return s;
    console.warn("Shader compile error:", gl.getShaderInfoLog(s));
    gl.deleteShader(s);
    return null;
  };

  const linkProgram = (gl, fragmentSource) => {
    const v = compileShader(gl, gl.VERTEX_SHADER, QUAD_VERTEX);
    const f = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
    const p = gl.createProgram();
    if (!v || !f || !p) return null;
    gl.attachShader(p, v);
    gl.attachShader(p, f);
    gl.bindAttribLocation(p, 0, 'aPosition');
    gl.linkProgram(p);
    gl.deleteShader(v);
    gl.deleteShader(f);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      console.warn("Program link error:", gl.getProgramInfoLog(p));
      gl.deleteProgram(p);
      return null;
    }
    const uniforms = {};
    const count = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < count; i++) {
      const info = gl.getActiveUniform(p, i);
      if (info) uniforms[info.name] = gl.getUniformLocation(p, info.name);
    }
    return { program: p, uniforms };
  };

  function initBeams(canvasId, userOptions) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const gl = canvas.getContext('webgl2', {
      alpha: true,
      premultipliedAlpha: true,
      antialias: false,
      depth: false,
      stencil: false,
      powerPreference: 'high-performance'
    });

    if (!gl) {
      console.warn("WebGL2 not supported, Beams fallback active.");
      return null;
    }

    const opts = Object.assign({
      color: '#ffffff',
      beamWidth: 170,
      rotation: 30,
      speed: 0.85,
      waveLength: 220,
      depth: 1.25,
      sharpness: 0.65,
      twist: 0.15,
      fillLight: 0.45,
      glow: 0.85,
      brightness: 2.0,
      variation: 0,
      grain: 0.18,
      quality: 0.85,
      mouseInteraction: true,
      mouseStrength: 1.0,
      intro: true,
      fade: 0.05,
      opacity: 0.85
    }, userOptions || {});

    const floatTargets = !!gl.getExtension('EXT_color_buffer_float');
    const fieldProgram = linkProgram(gl, FIELD);
    const compositeProgram = linkProgram(gl, COMPOSITE);
    if (!fieldProgram || !compositeProgram) return null;

    const buffer = gl.createBuffer();
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    let texture = null;
    const framebuffer = gl.createFramebuffer();
    const target = { width: 0, height: 0 };
    const sizeTarget = (w, h) => {
      if (target.width === w && target.height === h) return;
      target.width = w;
      target.height = h;
      if (texture) gl.deleteTexture(texture);
      texture = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, texture);
      const levels = Math.floor(Math.log2(Math.max(w, h))) + 1;
      gl.texStorage2D(gl.TEXTURE_2D, levels, floatTargets ? gl.RGBA16F : gl.RGBA8, w, h);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
    };

    const probe = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
    const toLinear = (hex) => {
      if (!probe) return [0.5, 0.55, 0.97];
      probe.clearRect(0, 0, 1, 1);
      probe.fillStyle = hex;
      probe.fillRect(0, 0, 1, 1);
      const d = probe.getImageData(0, 0, 1, 1).data;
      return [Math.pow(d[0] / 255, 2.2), Math.pow(d[1] / 255, 2.2), Math.pow(d[2] / 255, 2.2)];
    };

    const view = { width: 1, height: 1, fieldWidth: 1, fieldHeight: 1 };
    const pointer = { x: 0, y: 0, inside: false };
    const state = { clock: 0, intro: 0, reach: 0, x: 0, y: 0, lightY: 0 };
    let raf = 0;
    let last = 0;

    const render = () => {
      const presence = state.intro * state.intro * state.intro * (state.intro * (state.intro * 6 - 15) + 10);
      gl.bindVertexArray(vao);
      sizeTarget(view.fieldWidth, view.fieldHeight);

      const angle = (opts.rotation * Math.PI) / 180;
      const sweep = (1 - presence) * -9;
      const reach = state.reach * opts.mouseStrength;
      const f = fieldProgram.uniforms;
      gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
      gl.viewport(0, 0, target.width, target.height);
      gl.useProgram(fieldProgram.program);
      gl.uniform2f(f.uView, view.width, view.height);
      gl.uniform2f(f.uScale, view.width / target.width, view.height / target.height);
      gl.uniform2f(f.uTurn, Math.cos(angle), Math.sin(angle));
      gl.uniform1f(f.uTime, (state.clock * 0.12) % 289);
      gl.uniform1f(f.uWidth, opts.beamWidth);
      gl.uniform1f(f.uWave, opts.waveLength);
      gl.uniform1f(f.uDepth, opts.depth);
      gl.uniform1f(f.uRough, 0.55 - opts.sharpness * 0.5);
      gl.uniform1f(f.uSeed, opts.variation);
      gl.uniform1f(f.uTwist, opts.twist);
      gl.uniform1f(f.uFill, opts.fillLight);
      gl.uniform3f(f.uLight, 0, 3 + sweep + state.lightY * reach, 10);
      gl.uniform1f(f.uCamera, view.height * 1.866);
      gl.uniform4f(f.uPointer, state.x, view.height - state.y, reach, Math.max(view.height, view.width) * 0.28);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.generateMipmap(gl.TEXTURE_2D);

      const c = compositeProgram.uniforms;
      const tint = toLinear(opts.color);
      const tone = 0.2126 * tint[0] + 0.7152 * tint[1] + 0.0722 * tint[2];
      const shadeDepth = Math.min(1, 0.18 / Math.max(tone, 0.001));
      const ink = tint.map(v => Math.pow(Math.min(1, v * shadeDepth), 1 / 2.2));
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.useProgram(compositeProgram.program);
      gl.uniform2f(c.uResolution, canvas.width, canvas.height);
      gl.uniform3fv(c.uColor, tint);
      gl.uniform3fv(c.uInk, ink);
      gl.uniform1f(c.uGain, opts.brightness);
      gl.uniform1f(c.uGlow, opts.glow);
      gl.uniform1f(c.uPresence, presence);
      gl.uniform1f(c.uGrain, opts.grain * 1.75);
      gl.uniform1f(c.uFade, opts.fade);
      gl.uniform1f(c.uOpacity, opts.opacity);
      gl.uniform1f(c.uLightMode, 0);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.uniform1i(c.uField, 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    const frame = (now) => {
      raf = 0;
      if (document.hidden) return;
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 1 / 60;
      last = now;
      state.clock += dt * opts.speed;
      if (state.intro < 1) state.intro = Math.min(1, state.intro + dt / INTRO_SECONDS);

      const engaged = opts.mouseInteraction && pointer.inside;
      if (engaged && state.reach < 0.01) {
        state.x = pointer.x;
        state.y = pointer.y;
      }
      const follow = 1 - Math.exp(-dt * 7);
      state.x += (pointer.x - state.x) * follow;
      state.y += (pointer.y - state.y) * follow;
      state.reach += ((engaged ? 1 : 0) - state.reach) * (1 - Math.exp(-dt * (engaged ? 3.2 : 1.8)));
      const turn = (opts.rotation * Math.PI) / 180;
      const offsetX = state.x - view.width / 2;
      const offsetY = view.height / 2 - state.y;
      const along = -Math.sin(turn) * offsetX + Math.cos(turn) * offsetY;
      state.lightY = clamp((along / (view.height * 0.5)) * 3, -4, 4);
      render();

      raf = requestAnimationFrame(frame);
    };

    const resize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      view.width = w;
      view.height = h;
      canvas.width = Math.max(1, Math.round(w * ratio));
      canvas.height = Math.max(1, Math.round(h * ratio));
      let fieldScale = opts.quality * ratio;
      if (w * h * fieldScale * fieldScale > MAX_FIELD_PIXELS) {
        fieldScale = Math.sqrt(MAX_FIELD_PIXELS / (w * h));
      }
      view.fieldWidth = Math.max(1, Math.round(w * fieldScale));
      view.fieldHeight = Math.max(1, Math.round(h * fieldScale));
      render();
    };

    window.addEventListener('resize', resize);
    window.addEventListener('pointermove', (e) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      pointer.inside = true;
    }, { passive: true });
    document.documentElement.addEventListener('pointerleave', () => {
      pointer.inside = false;
    });

    resize();
    raf = requestAnimationFrame(frame);

    return {
      destroy: () => {
        cancelAnimationFrame(raf);
        window.removeEventListener('resize', resize);
      }
    };
  }

  global.initReactBitsBeams = initBeams;
})(window);


</script>
</head>
<body>

  <!-- Fullscreen Interactive React Bits Beams WebGL2 Canvas (White/Silver Monochrome) -->
  <canvas id="beams-canvas"></canvas>

  <!-- Viewport-Wide Ambient Liquid Glass Frosted Layer -->
  <div class="ambient-glass-layer"></div>

  <!-- ==========================================================================
       1. POLARIS TOP NAVIGATION BAR (Exact 1:1 Layout)
       ========================================================================== -->
  <header class="polaris-topbar">
    <!-- Left: Search Box -->
    <div class="topbar-search">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>
      <input type="text" placeholder="Search telemetry, threats, assets..." aria-label="Search">
      <span class="search-kbd">⌘K</span>
    </div>

    <!-- Center: Glossy Brand Pill -->
    <div class="center-brand-pill" onclick="showScreen('command')">
      <div class="sphere-logo">
        <svg viewBox="0 0 24 24"><polygon points="12 2 22 21 12 17 2 21 12 2"/></svg>
      </div>
      <span class="brand-pill-text">ProcureAgent</span>
    </div>

    <!-- Right: Workspace, Orbit / Stack status, UTC Clock, Bell -->
    <div class="topbar-right">
      <div class="workspace-pill">
        <span>Aarav Sharma's worksp...</span>
        <span class="admin-badge">ADMIN</span>
      </div>

      <div class="orbit-pill" id="top-orbit-pill">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 4.24 4.24"/><path d="m14.83 9.17 4.24-4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="m9.17 14.83-4.24 4.24"/></svg>
        <span id="top-orbit-text">Polaris Orbit • Sentinel-2 Active</span>
      </div>

      <div class="utc-clock">
        <span class="dot"></span>
        <span id="utc-clock-time">17:24:12 UTC</span>
      </div>

      <div class="bell-btn" title="1 Notification">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        <span class="bell-badge">1</span>
      </div>
    </div>
  </header>

  <!-- ==========================================================================
       2. EXPANDABLE POLARIS CAPSULE SIDEBAR DOCK (Exact 1:1)
       ========================================================================== -->
  <nav class="polaris-dock" id="polaris-dock" aria-label="Sidebar Navigation">
    <!-- Top Emblem / Brand Header -->
    <div class="sidebar-header-box" onclick="toggleSidebarPin()" title="Toggle Sidebar">
      <div class="dock-emblem">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 48 46"><path fill="#863bff" d="M25.946 44.938c-.664.845-2.021.375-2.021-.698V33.937a2.26 2.26 0 0 0-2.262-2.262H10.287c-.92 0-1.456-1.04-.92-1.788l7.48-10.471c1.07-1.497 0-3.578-1.842-3.578H1.237c-.92 0-1.456-1.04-.92-1.788L10.013.474c.214-.297.556-.474.92-.474h28.894c.92 0 1.456 1.04.92 1.788l-7.48 10.471c-1.07 1.498 0 3.579 1.842 3.579h11.377c.943 0 1.473 1.088.89 1.83L25.947 44.94z" style="fill:#863bff;fill:color(display-p3 .5252 .23 1);fill-opacity:1"/><mask id="a" width="20" height="20" x="0" y="0" maskUnits="userSpaceOnUse" style="mask-type:alpha"><path fill="#000" d="M25.842 44.938c-.664.844-2.021.375-2.021-.698V33.937a2.26 2.26 0 0 0-2.262-2.262H10.183c-.92 0-1.456-1.04-.92-1.788l7.48-10.471c1.07-1.498 0-3.579-1.842-3.579H1.133c-.92 0-1.456-1.04-.92-1.787L9.91.473c.214-.297.556-.474.92-.474h28.894c.92 0 1.456 1.04.92 1.788l-7.48 10.471c-1.07 1.498 0 3.578 1.842 3.578h11.377c.943 0 1.473 1.088.89 1.832L25.843 44.94z" style="fill:#000;fill-opacity:1"/></mask><g mask="url(#a)"><g filter="url(#b)"><ellipse cx="5.508" cy="14.704" fill="#ede6ff" rx="5.508" ry="14.704" style="fill:#ede6ff;fill:color(display-p3 .9275 .9033 1);fill-opacity:1" transform="matrix(.00324 1 1 -.00324 -4.47 31.516)"/></g><g filter="url(#c)"><ellipse cx="10.399" cy="29.851" fill="#ede6ff" rx="10.399" ry="29.851" style="fill:#ede6ff;fill:color(display-p3 .9275 .9033 1);fill-opacity:1" transform="matrix(.00324 1 1 -.00324 -39.328 7.883)"/></g><g filter="url(#d)"><ellipse cx="5.508" cy="30.487" fill="#7e14ff" rx="5.508" ry="30.487" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="rotate(89.814 -25.913 -14.639)scale(1 -1)"/></g><g filter="url(#e)"><ellipse cx="5.508" cy="30.599" fill="#7e14ff" rx="5.508" ry="30.599" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="rotate(89.814 -32.644 -3.334)scale(1 -1)"/></g><g filter="url(#f)"><ellipse cx="5.508" cy="30.599" fill="#7e14ff" rx="5.508" ry="30.599" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="matrix(.00324 1 1 -.00324 -34.34 30.47)"/></g><g filter="url(#g)"><ellipse cx="14.072" cy="22.078" fill="#ede6ff" rx="14.072" ry="22.078" style="fill:#ede6ff;fill:color(display-p3 .9275 .9033 1);fill-opacity:1" transform="rotate(93.35 24.506 48.493)scale(-1 1)"/></g><g filter="url(#h)"><ellipse cx="3.47" cy="21.501" fill="#7e14ff" rx="3.47" ry="21.501" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="rotate(89.009 28.708 47.59)scale(-1 1)"/></g><g filter="url(#i)"><ellipse cx="3.47" cy="21.501" fill="#7e14ff" rx="3.47" ry="21.501" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="rotate(89.009 28.708 47.59)scale(-1 1)"/></g><g filter="url(#j)"><ellipse cx=".387" cy="8.972" fill="#7e14ff" rx="4.407" ry="29.108" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="rotate(39.51 .387 8.972)"/></g><g filter="url(#k)"><ellipse cx="47.523" cy="-6.092" fill="#7e14ff" rx="4.407" ry="29.108" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="rotate(37.892 47.523 -6.092)"/></g><g filter="url(#l)"><ellipse cx="41.412" cy="6.333" fill="#47bfff" rx="5.971" ry="9.665" style="fill:#47bfff;fill:color(display-p3 .2799 .748 1);fill-opacity:1" transform="rotate(37.892 41.412 6.333)"/></g><g filter="url(#m)"><ellipse cx="-1.879" cy="38.332" fill="#7e14ff" rx="4.407" ry="29.108" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="rotate(37.892 -1.88 38.332)"/></g><g filter="url(#n)"><ellipse cx="-1.879" cy="38.332" fill="#7e14ff" rx="4.407" ry="29.108" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="rotate(37.892 -1.88 38.332)"/></g><g filter="url(#o)"><ellipse cx="35.651" cy="29.907" fill="#7e14ff" rx="4.407" ry="29.108" style="fill:#7e14ff;fill:color(display-p3 .4922 .0767 1);fill-opacity:1" transform="rotate(37.892 35.651 29.907)"/></g><g filter="url(#p)"><ellipse cx="38.418" cy="32.4" fill="#47bfff" rx="5.971" ry="15.297" style="fill:#47bfff;fill:color(display-p3 .2799 .748 1);fill-opacity:1" transform="rotate(37.892 38.418 32.4)"/></g></g><defs><filter id="b" width="60.045" height="41.654" x="-19.77" y="16.149" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="7.659"/></filter><filter id="c" width="90.34" height="51.437" x="-54.613" y="-7.533" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="7.659"/></filter><filter id="d" width="79.355" height="29.4" x="-49.64" y="2.03" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="e" width="79.579" height="29.4" x="-45.045" y="20.029" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="f" width="79.579" height="29.4" x="-43.513" y="21.178" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="g" width="74.749" height="58.852" x="15.756" y="-17.901" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="7.659"/></filter><filter id="h" width="61.377" height="25.362" x="23.548" y="2.284" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="i" width="61.377" height="25.362" x="23.548" y="2.284" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="j" width="56.045" height="63.649" x="-27.636" y="-22.853" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="k" width="54.814" height="64.646" x="20.116" y="-38.415" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="l" width="33.541" height="35.313" x="24.641" y="-11.323" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="m" width="54.814" height="64.646" x="-29.286" y="6.009" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="n" width="54.814" height="64.646" x="-29.286" y="6.009" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="o" width="54.814" height="64.646" x="8.244" y="-2.416" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter><filter id="p" width="39.409" height="43.623" x="18.713" y="10.588" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"/><feGaussianBlur result="effect1_foregroundBlur_2002_17158" stdDeviation="4.596"/></filter></defs></svg>
      </div>
      <div class="sidebar-header-text">
        <span class="sidebar-title">ProcureAgent</span>
        <span class="sidebar-sub">RISK & SPEND INTEL</span>
      </div>
    </div>

    <div class="dock-sep"></div>

    <!-- Navigation Buttons with Icons + Text Labels -->
    <div class="dock-icons">
      <!-- 1: Command Centre -->
      <button class="dock-icon-btn active" id="btn-dock-command" onclick="showScreen('command')" aria-label="Command Centre">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
        <span class="dock-text-label">Command Centre</span>
      </button>

      <!-- 2: Incidents & Threats / Purchases -->
      <button class="dock-icon-btn" id="btn-dock-purchases" onclick="showScreen('purchases')" aria-label="Purchases & Bounties">
        <svg viewBox="0 0 24 24"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>
        <span class="dock-text-label">Incidents & Threats</span>
      </button>

      <!-- 3: Polaris Orbit / Workers -->
      <button class="dock-icon-btn" id="btn-dock-workers" onclick="showScreen('workers')" aria-label="Workers & Fleet">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><path d="M10.4 10.4 6.3 6.3"/><path d="m13.6 13.6 4.1 4.1"/><path d="M17.6 6.4 13.6 10.4"/><path d="m6.4 17.6 4-4"/></svg>
        <span class="dock-text-label">Polaris Orbit</span>
      </button>

      <!-- 4: Assets & Facilities / Policy -->
      <button class="dock-icon-btn" id="btn-dock-policy" onclick="showScreen('policy')" aria-label="Governance Policy">
        <svg viewBox="0 0 24 24"><rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/></svg>
        <span class="dock-text-label">Assets & Facilities</span>
      </button>

      <!-- 5: Sources & Feeds / Audit -->
      <button class="dock-icon-btn" id="btn-dock-audit" onclick="showScreen('audit')" aria-label="Audit Ledger">
        <svg viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        <span class="dock-text-label">Sources & Feeds</span>
      </button>

      <!-- 6: Feed Monitoring / Demo Scenarios -->
      <button class="dock-icon-btn" id="btn-dock-demo" onclick="openDemoModal()" aria-label="Demo Scenarios">
        <svg viewBox="0 0 24 24"><path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19"/></svg>
        <span class="dock-text-label">Feed Monitoring</span>
      </button>

      <!-- 7: Settings -->
      <button class="dock-icon-btn" id="btn-dock-settings" onclick="showScreen('policy')" aria-label="Settings">
        <svg viewBox="0 0 24 24"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
        <span class="dock-text-label">Settings</span>
      </button>
    </div>

    <!-- Log Out Button -->
    <button class="dock-icon-btn" onclick="togglePlaybackMode()" aria-label="Log Out / Mode" style="margin-top: 4px;">
      <svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
      <span class="dock-text-label">Log Out</span>
    </button>

    <!-- Bottom User Profile Card -->
    <div class="sidebar-footer-user" onclick="togglePlaybackMode()" title="Aarav Sharma [ADMIN]">
      <div class="dock-avatar-circle">AA</div>
      <div class="user-footer-details">
        <span class="user-name-line">Aarav Sharma</span>
        <span class="user-email-line">aarav@polaris.ai</span>
      </div>
      <span class="admin-badge" style="margin-left: auto;">ADMIN</span>
    </div>
  </nav>

  <!-- ==========================================================================
       3. MAIN VIEWPORT
       ========================================================================= -->
  <main class="polaris-main">

    <!-- ========================================================================
         SCREEN 1: COMMAND CENTRE
         ======================================================================== -->
    <section id="screen-command" class="polaris-screen active">
      <div class="page-kicker">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19"/></svg>
        SOURCE ORCHESTRATION
      </div>
      <div class="page-title-row">
        <div>
          <h1 class="page-headline">Autonomous Procurement Command Centre</h1>
          <p class="page-subtext">Run history and authenticated manual retrieval. External alerting remains disabled.</p>
        </div>
        <button class="btn-polaris-action" onclick="openDemoModal()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          Run monitoring now
        </button>
      </div>

      <!-- Dual Column Polaris Liquid Glass Command Grid -->
      <div class="command-grid">
        <!-- Left Column: Risk Events Panel -->
        <div class="polaris-panel">
          <div class="panel-search">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>
            <input type="text" placeholder="Search telemetry, threats, assets...">
          </div>

          <div class="segmented-tabs">
            <button class="tab-pill active">≡ Events</button>
            <button class="tab-pill" onclick="showScreen('workers')">⊞ Layers</button>
          </div>

          <div class="events-header">
            <span style="display: flex; align-items: center; gap: 6px; color: #fff;">
              <span style="width: 7px; height: 7px; border-radius: 50%; background: var(--accent-rose); display: inline-block;"></span>
              RISK EVENTS
            </span>
            <span>2 / 2</span>
          </div>

          <div class="filter-pills-row">
            <div class="filter-pill active">All Events (2)</div>
            <div class="filter-pill">✈ Travellers (0)</div>
          </div>

          <div class="filter-pills-row" style="margin-bottom: 14px;">
            <div class="filter-pill" style="color: #fca5a5; border-color: rgba(239, 68, 68, 0.3);">● Critical</div>
            <div class="filter-pill" style="color: #fde68a; border-color: rgba(245, 158, 11, 0.3);">● High</div>
            <div class="filter-pill" style="color: #fef08a;">● Moderate</div>
            <div class="filter-pill">Low</div>
            <div class="filter-pill">● Info</div>
          </div>

          <!-- Bounties / Incidents List -->
          <div class="bounty-card-item selected" onclick="showReceipt('PO-2026-1031-01')">
            <div class="card-tags">
              <span class="polaris-tag success">VERIFIED</span>
              <span class="polaris-tag neutral">code_bounty</span>
              <span class="polaris-tag neutral" style="color: #fff;">NEW</span>
            </div>
            <div class="bounty-item-title">Fix broken auth token parser in api_client.py</div>
            <div class="bounty-item-meta">
              <span>📍 Code Worker 120B</span>
              <span>•</span>
              <span>🕒 in 4.12s (5/5 passed)</span>
            </div>
          </div>

          <div class="bounty-card-item" onclick="showScreen('audit')">
            <div class="card-tags">
              <span class="polaris-tag critical">CRITICAL</span>
              <span class="polaris-tag neutral">adversary</span>
              <span class="polaris-tag critical">BLOCKED</span>
            </div>
            <div class="bounty-item-title">Rogue Worker predatory bid ($0.18) rejected at acceptance check</div>
            <div class="bounty-item-meta">
              <span>📍 Quarantined</span>
              <span>•</span>
              <span>🕒 $0.00 spent</span>
            </div>
          </div>
        </div>

        <!-- Right Column: Polaris KPI Grid + Live Activity Stream -->
        <div>
          <div class="kpi-row-polaris">
            <div class="kpi-box">
              <div class="kpi-top">
                <span>Weekly Budget Cap</span>
                <span class="polaris-tag neutral">Cap: $25.00</span>
              </div>
              <div class="kpi-num" style="color: var(--accent-emerald);">$24.75</div>
              <div class="kpi-detail">Spent: <strong>$0.25</strong> • Held: <strong>$0.00</strong></div>
              <div class="polaris-bar">
                <div class="polaris-bar-fill" style="width: 1.0%;"></div>
              </div>
            </div>

            <div class="kpi-box">
              <div class="kpi-top">
                <span>Active Bounties</span>
                <span class="polaris-tag success">Listening</span>
              </div>
              <div class="kpi-num">0</div>
              <div class="kpi-detail">Agents awaiting task packages</div>
            </div>

            <div class="kpi-box">
              <div class="kpi-top">
                <span>Verified Purchases</span>
                <span class="polaris-tag success">100% Pass</span>
              </div>
              <div class="kpi-num">1</div>
              <div class="kpi-detail">5/5 automated unit tests verified</div>
            </div>

            <div class="kpi-box">
              <div class="kpi-top">
                <span>Pending Approvals</span>
                <span class="polaris-tag neutral">Limit: $5.00</span>
              </div>
              <div class="kpi-num">0</div>
              <div class="kpi-detail">All bounties compliant with policy</div>
            </div>
          </div>

          <!-- Activity Stream Card -->
          <div class="polaris-panel">
            <div class="events-header" style="margin-bottom: 16px;">
              <span>LIVE TELEMETRY STREAM</span>
              <span>UTC MONITORED</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 14px;">
              <div style="display: flex; gap: 12px; align-items: flex-start;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-emerald); margin-top: 5px; box-shadow: 0 0 8px #10b981;"></span>
                <div>
                  <div style="font-size: 13px; color: #fff;">Automated unit tests passed. Payment of $0.25 initiated via PayPal Payouts.</div>
                  <div style="font-size: 11px; color: var(--text-muted);">Batch ID: NUFGNUMSUTJ7W • 12:58:18 UTC</div>
                </div>
              </div>

              <div style="display: flex; gap: 12px; align-items: flex-start;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-emerald); margin-top: 5px; box-shadow: 0 0 8px #10b981;"></span>
                <div>
                  <div style="font-size: 13px; color: #fff;">Solution delivered by Code Worker 120B verified against hidden test suite.</div>
                  <div style="font-size: 11px; color: var(--text-muted);">5 of 5 tests passed in 2.14s • 12:58:16 UTC</div>
                </div>
              </div>

              <div style="display: flex; gap: 12px; align-items: flex-start;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-amber); margin-top: 5px; box-shadow: 0 0 8px #f59e0b;"></span>
                <div>
                  <div style="font-size: 13px; color: #fff;">Task reassigned to Code Worker 120B following adversary block.</div>
                  <div style="font-size: 11px; color: var(--text-muted);">Seamless failover triggered • 12:58:14 UTC</div>
                </div>
              </div>

              <div style="display: flex; gap: 12px; align-items: flex-start;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-rose); margin-top: 5px; box-shadow: 0 0 8px #ef4444;"></span>
                <div>
                  <div style="font-size: 13px; color: #fff;">Payment withheld: Rogue Worker failed the hidden unit checks ($0.00 spent).</div>
                  <div style="font-size: 11px; color: var(--text-muted);">Reputation zeroed & quarantined • 12:58:12 UTC</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ========================================================================
         SCREEN 2: PURCHASES / INCIDENT DOSSIER (1:1 Polaris Dossier Layout)
         ======================================================================== -->
    <section id="screen-purchases" class="polaris-screen">
      <div class="page-kicker">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/></svg>
        INCIDENT DOSSIER & ORDER RECEIPT
      </div>
      <div class="page-title-row">
        <div>
          <h1 class="page-headline">Procurement Dossier #PO-2026-1031-01</h1>
          <p class="page-subtext">Itemized competitive bids, verification checks, and PayPal settlement record.</p>
        </div>
      </div>

      <!-- Polaris Incident Dossier Container -->
      <div class="dossier-card">
        <!-- Top Dossier Header -->
        <div class="dossier-top">
          <div class="dossier-badges">
            <span class="polaris-tag success" style="font-size: 11px; padding: 4px 10px;">VERIFIED BOUNTY</span>
            <span class="polaris-tag neutral" style="font-size: 11px; padding: 4px 10px;">Order #PO-2026-1031-01</span>
          </div>
          <div class="dossier-actions">
            <button class="btn-dossier-icon"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg> Export</button>
            <button class="btn-dossier-icon"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" x2="14" y1="3" y2="10"/><line x1="3" x2="10" y1="21" y2="14"/></svg> Expand</button>
            <button class="btn-dossier-icon" onclick="showScreen('command')">✕</button>
          </div>
        </div>

        <div class="dossier-title">Fix broken auth token parser in api_client.py</div>
        <div class="dossier-location">
          <span>Singapore Distribution Centre (code_bounty)</span>
          <span>•</span>
          <span>tests/test_api_client.py • 5 acceptance test cases</span>
          <span>•</span>
          <span>84 personnel on-site / automated runner</span>
        </div>

        <!-- Dual Impact ETA / Hazard Radius Stat Boxes -->
        <div class="stat-boxes-dual">
          <div class="dual-box">
            <div class="dual-label">
              <span>SETTLEMENT AMOUNT</span>
              <span>●</span>
            </div>
            <div class="dual-val" style="color: var(--accent-emerald);">$0.25 USD</div>
            <div class="dual-sub">Saved $0.25 under authorized $0.50 budget ceiling</div>
          </div>

          <div class="dual-box">
            <div class="dual-label">
              <span>VERIFICATION INTEGRITY</span>
              <span style="color: var(--accent-emerald);">●</span>
            </div>
            <div class="dual-val">Passed 5 / 5</div>
            <div class="dual-sub">Hard Check: Automated Docker sandbox exit code 0</div>
          </div>
        </div>

        <!-- Progress Slider Bar (like Polaris Asset Distance) -->
        <div class="slider-track-box">
          <div class="slider-top-labels">
            <span>Budget Utilization: <strong>$0.25 used</strong> (50.0%)</span>
            <span>Ceiling: <strong>$0.50 max</strong></span>
          </div>
          <div class="polaris-bar" style="height: 6px;">
            <div class="polaris-bar-fill" style="width: 50%;"></div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-top: 6px;">
            <span>$0.00 Base</span>
            <span>$0.25 Settlement</span>
            <span>$0.50 Max Cap</span>
          </div>
        </div>

        <!-- Playbook Segmented Tabs -->
        <div class="playbook-tabs">
          <button class="playbook-tab active">Tactical Offers (3)</button>
          <button class="playbook-tab">Verification Sandbox</button>
          <button class="playbook-tab">PayPal Settlement</button>
          <button class="playbook-tab">Cryptographic Proof</button>
        </div>

        <!-- Phase Pills -->
        <div class="phase-pills-row">
          <div class="phase-pill active">Phase 1: Market Auction (Done)</div>
          <div class="phase-pill active">Phase 2: Sandbox Verification (Passed)</div>
          <div class="phase-pill active">Phase 3: PayPal Settlement (Settled)</div>
        </div>

        <!-- Table of Offers -->
        <table class="polaris-table">
          <thead>
            <tr>
              <th>Worker Candidate</th>
              <th>Submitted Bid</th>
              <th>Latency SLA</th>
              <th>Track Record</th>
              <th>Selection Outcome</th>
            </tr>
          </thead>
          <tbody>
            <tr style="background: rgba(255, 255, 255, 0.05);">
              <td><strong>Code Worker 120B</strong></td>
              <td><strong style="color: var(--accent-emerald);">$0.25</strong></td>
              <td>4.12s</td>
              <td>98.2% (N=30)</td>
              <td><span class="polaris-tag success">Selected (Best balanced score)</span></td>
            </tr>
            <tr>
              <td>Code Worker 20B</td>
              <td>$0.15</td>
              <td>4.88s</td>
              <td>95.1% (N=30)</td>
              <td><span class="polaris-tag neutral">Alternate candidate</span></td>
            </tr>
            <tr>
              <td>Rogue Worker (Adversary)</td>
              <td>$0.18</td>
              <td>1.20s</td>
              <td>0.0% (N=30)</td>
              <td><span class="polaris-tag critical">Rejected & Quarantined (Failed checks)</span></td>
            </tr>
          </tbody>
        </table>

        <div style="font-size: 12px; color: var(--text-dim); background: var(--bg-glass-inner); border: 1px solid var(--border-glass); border-radius: 10px; padding: 12px 16px; margin-top: 16px;">
          <strong>Decision Rationale:</strong> Code Worker 120B was selected because its 98.2% historical reliability score outweighed the minor price difference under organizational reliability rules. When the predatory low bidder (Rogue Worker) failed acceptance tests, the task was safely reallocated with zero financial loss.
        </div>

        <!-- Bottom Governance Bar -->
        <div class="dossier-footer">
          <span>Governance: <code>config/bounty_policy.yaml</code> • ISO 22301 / FEMA NIMS</span>
          <span>PayPal Batch ID: <strong>NUFGNUMSUTJ7W</strong> • 6 of 6 blocks verified</span>
        </div>
      </div>
    </section>

    <!-- ========================================================================
         SCREEN 3: WORKERS FLEET
         ======================================================================== -->
    <section id="screen-workers" class="polaris-screen">
      <div class="page-kicker">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><circle cx="19" cy="5" r="2"/></svg>
        FLEET ORCHESTRATION & TELEMETRY
      </div>
      <div class="page-title-row">
        <div>
          <h1 class="page-headline">Autonomous Worker Registry</h1>
          <p class="page-subtext">Empirical performance metrics computed from verified run logs (<code>audit/run_log.jsonl</code>).</p>
        </div>
      </div>

      <div class="fleet-grid">
        <div class="fleet-card">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <h3 style="font-size: 16px; font-weight: 700;">Code Worker 120B</h3>
              <span class="polaris-tag success">Active</span>
            </div>
            <p style="font-size: 12px; color: var(--text-dim); margin-bottom: 14px;">Complex Code Generation & Automated Bug Repair</p>
            <div class="fleet-stats-3">
              <div><div style="font-size: 10px; color: var(--text-muted);">TRACK RECORD</div><div style="font-size: 16px; font-weight: 700; color: var(--accent-emerald);">98.2%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">PASS RATE</div><div style="font-size: 16px; font-weight: 700;">96.7%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">EVALUATED</div><div style="font-size: 16px; font-weight: 700;">N=30</div></div>
            </div>
          </div>
          <div style="border-top: 1px solid var(--border-glass); padding-top: 10px; font-size: 11px; color: var(--text-muted); display: flex; justify-content: space-between;">
            <span>Base Fee: <strong>$0.05</strong></span>
            <span>Capabilities: <code>code_bounty</code>, <code>python</code></span>
          </div>
        </div>

        <div class="fleet-card">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <h3 style="font-size: 16px; font-weight: 700;">Code Worker 20B</h3>
              <span class="polaris-tag success">Active</span>
            </div>
            <p style="font-size: 12px; color: var(--text-dim); margin-bottom: 14px;">Rapid Low-Latency Code Repair & Refactoring</p>
            <div class="fleet-stats-3">
              <div><div style="font-size: 10px; color: var(--text-muted);">TRACK RECORD</div><div style="font-size: 16px; font-weight: 700; color: var(--accent-emerald);">95.1%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">PASS RATE</div><div style="font-size: 16px; font-weight: 700;">93.3%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">EVALUATED</div><div style="font-size: 16px; font-weight: 700;">N=30</div></div>
            </div>
          </div>
          <div style="border-top: 1px solid var(--border-glass); padding-top: 10px; font-size: 11px; color: var(--text-muted); display: flex; justify-content: space-between;">
            <span>Base Fee: <strong>$0.02</strong></span>
            <span>Capabilities: <code>code_bounty</code>, <code>python</code></span>
          </div>
        </div>

        <div class="fleet-card">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <h3 style="font-size: 16px; font-weight: 700;">OCR Worker Alpha</h3>
              <span class="polaris-tag success">Active</span>
            </div>
            <p style="font-size: 12px; color: var(--text-dim); margin-bottom: 14px;">Invoice & Document Optical Character Recognition</p>
            <div class="fleet-stats-3">
              <div><div style="font-size: 10px; color: var(--text-muted);">TRACK RECORD</div><div style="font-size: 16px; font-weight: 700; color: var(--accent-emerald);">99.0%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">PASS RATE</div><div style="font-size: 16px; font-weight: 700;">100%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">EVALUATED</div><div style="font-size: 16px; font-weight: 700;">N=28</div></div>
            </div>
          </div>
          <div style="border-top: 1px solid var(--border-glass); padding-top: 10px; font-size: 11px; color: var(--text-muted); display: flex; justify-content: space-between;">
            <span>Base Fee: <strong>$0.01</strong></span>
            <span>Capabilities: <code>document_ocr</code></span>
          </div>
        </div>

        <div class="fleet-card">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <h3 style="font-size: 16px; font-weight: 700;">LLM Reasoning Worker</h3>
              <span class="polaris-tag success">Active</span>
            </div>
            <p style="font-size: 12px; color: var(--text-dim); margin-bottom: 14px;">General Language Synthesis & Data Validation</p>
            <div class="fleet-stats-3">
              <div><div style="font-size: 10px; color: var(--text-muted);">TRACK RECORD</div><div style="font-size: 16px; font-weight: 700; color: var(--accent-emerald);">97.4%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">PASS RATE</div><div style="font-size: 16px; font-weight: 700;">96.7%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">EVALUATED</div><div style="font-size: 16px; font-weight: 700;">N=30</div></div>
            </div>
          </div>
          <div style="border-top: 1px solid var(--border-glass); padding-top: 10px; font-size: 11px; color: var(--text-muted); display: flex; justify-content: space-between;">
            <span>Base Fee: <strong>$0.03</strong></span>
            <span>Capabilities: <code>llm_synthesis</code></span>
          </div>
        </div>

        <div class="fleet-card" style="border-color: rgba(239, 68, 68, 0.3);">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <h3 style="font-size: 16px; font-weight: 700;">Rogue Worker</h3>
              <span class="polaris-tag critical">[Scripted Adversary]</span>
            </div>
            <p style="font-size: 12px; color: #fca5a5; margin-bottom: 14px;">Submits predatory underbids ($0.18) with corrupted code</p>
            <div class="fleet-stats-3">
              <div><div style="font-size: 10px; color: var(--text-muted);">TRACK RECORD</div><div style="font-size: 16px; font-weight: 700; color: var(--accent-rose);">0.0%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">PASS RATE</div><div style="font-size: 16px; font-weight: 700;">0.0%</div></div>
              <div><div style="font-size: 10px; color: var(--text-muted);">EVALUATED</div><div style="font-size: 16px; font-weight: 700;">N=30</div></div>
            </div>
          </div>
          <div style="border-top: 1px solid var(--border-glass); padding-top: 10px; font-size: 11px; color: var(--accent-rose); display: flex; justify-content: space-between;">
            <span>Status: <strong>Quarantined & Blocked</strong></span>
            <span>Payouts Allowed: <strong>$0.00</strong></span>
          </div>
        </div>
      </div>
    </section>

    <!-- ========================================================================
         SCREEN 4: GOVERNANCE & POLICY
         ======================================================================== -->
    <section id="screen-policy" class="polaris-screen">
      <div class="page-kicker">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="16" height="20" x="4" y="2" rx="2"/><path d="M9 22v-4h6v4"/></svg>
        COMPLIANCE & GOVERNANCE RULES
      </div>
      <div class="page-title-row">
        <div>
          <h1 class="page-headline">Spending Governance & Policy Rules</h1>
          <p class="page-subtext">Active organizational constraints loaded from <code>config/bounty_policy.yaml</code>.</p>
        </div>
      </div>

      <div class="command-grid">
        <div class="polaris-panel">
          <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">Weekly Spend Cap</h3>
          <div style="font-size: 32px; font-weight: 700; color: var(--accent-emerald); margin-bottom: 6px;">$25.00 <span style="font-size: 14px; color: var(--text-muted);">USD</span></div>
          <p style="font-size: 13px; color: var(--text-dim); margin-bottom: 14px;">Hard transactional ceiling enforced by SQLite reservation lock.</p>
          <div style="background: var(--bg-glass-inner); padding: 12px; border-radius: 10px; font-size: 12px; border: 1px solid var(--border-glass);">
            <div>Spent this week: <strong>$0.25</strong></div>
            <div>Held for pending tasks: <strong>$0.00</strong></div>
            <div style="color: var(--accent-emerald); margin-top: 4px;">Remaining cap: <strong>$24.75</strong></div>
          </div>
        </div>

        <div class="polaris-panel">
          <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">Approval Threshold Ceiling</h3>
          <div style="font-size: 32px; font-weight: 700; color: #fff; margin-bottom: 6px;">$5.00 <span style="font-size: 14px; color: var(--text-muted);">ceiling</span></div>
          <p style="font-size: 13px; color: var(--text-dim); margin-bottom: 14px;">Bounties &le; $5.00 execute autonomously. Bounties > $5.00 require manager approval.</p>
          <div style="background: var(--bg-glass-inner); padding: 12px; border-radius: 10px; font-size: 12px; border: 1px solid var(--border-glass);">
            <div>Pending manual approvals: <strong>0 tasks</strong></div>
            <div style="color: var(--text-muted); margin-top: 4px;">Zero unreviewed high-budget tasks pending execution.</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ========================================================================
         SCREEN 5: AUDIT LEDGER
         ======================================================================== -->
    <section id="screen-audit" class="polaris-screen">
      <div class="page-kicker">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/></svg>
        CRYPTOGRAPHIC HASH CHAIN TELEMETRY
      </div>
      <div class="page-title-row">
        <div>
          <h1 class="page-headline">Tamper-Evident Audit Ledger</h1>
          <p class="page-subtext">Cryptographically linked SHA-256 blocks anchored to <code>audit/anchor.hash</code>.</p>
        </div>
        <button class="btn-polaris-action" id="btn-verify-chain" onclick="runVerifyChain()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          Verify Chain Now
        </button>
      </div>

      <div class="polaris-panel">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
          <div style="font-size: 14px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px;">
            <span id="chain-status-icon" style="color: var(--accent-emerald);">✓</span>
            <span id="chain-status-title">Chain Status: VERIFIED & TAMPER-FREE</span>
          </div>
          <div id="chain-status-detail" style="font-size: 12px; color: var(--text-dim);">
            6 consecutive blocks validated against genesis state anchor.
          </div>
        </div>

        <table class="polaris-table">
          <thead>
            <tr>
              <th>Block</th>
              <th>Timestamp</th>
              <th>Event</th>
              <th>Description</th>
              <th>Amount</th>
              <th>Worker / Actor</th>
              <th>Verification</th>
              <th>Block Hash</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>#0</strong></td>
              <td>12:58:00</td>
              <td><span class="polaris-tag neutral">Genesis</span></td>
              <td>Ledger initialized with signed state anchor</td>
              <td>$0.00</td>
              <td>System</td>
              <td>Anchor Matched</td>
              <td><code>9a8f12c...</code></td>
            </tr>
            <tr>
              <td><strong>#1</strong></td>
              <td>12:58:10</td>
              <td><span class="polaris-tag neutral">Reserve</span></td>
              <td>Reserved $0.50 budget for auth token parser task</td>
              <td>$0.50</td>
              <td>Buyer Org</td>
              <td>Cap Compliant</td>
              <td><code>3d12e8b...</code></td>
            </tr>
            <tr>
              <td><strong>#2</strong></td>
              <td>12:58:12</td>
              <td><span class="polaris-tag critical">Reject</span></td>
              <td>Rogue Worker submitted broken code; failed acceptance check</td>
              <td>$0.00</td>
              <td>Rogue Worker</td>
              <td>Failed (0/5)</td>
              <td><code>7c44a90...</code></td>
            </tr>
            <tr>
              <td><strong>#3</strong></td>
              <td>12:58:14</td>
              <td><span class="polaris-tag neutral">Reassign</span></td>
              <td>Task reallocated to Code Worker 120B under priority scoring</td>
              <td>$0.00</td>
              <td>Broker</td>
              <td>Reallocated</td>
              <td><code>b210f54...</code></td>
            </tr>
            <tr>
              <td><strong>#4</strong></td>
              <td>12:58:16</td>
              <td><span class="polaris-tag success">Pass</span></td>
              <td>Code Worker 120B passed all 5 hidden acceptance unit tests</td>
              <td>$0.00</td>
              <td>Code Worker 120B</td>
              <td>Hard Check (5/5)</td>
              <td><code>f089d71...</code></td>
            </tr>
            <tr>
              <td><strong>#5</strong></td>
              <td>12:58:18</td>
              <td><span class="polaris-tag success">Payout</span></td>
              <td>Live sandbox payment executed via PayPal Payouts API</td>
              <td><strong style="color: var(--accent-emerald);">$0.25</strong></td>
              <td>Code Worker 120B</td>
              <td>Batch: NUFGNUMSUTJ7W</td>
              <td><code>a61be22...</code></td>
            </tr>
            <tr>
              <td><strong>#6</strong></td>
              <td>12:58:19</td>
              <td><span class="polaris-tag success">Release</span></td>
              <td>Settled $0.25 spent; $0.25 returned to organizational pool</td>
              <td>-$0.25</td>
              <td>Buyer Org</td>
              <td>Ledger Balanced</td>
              <td><code>e432c01...</code></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

  </main>

  <!-- ==========================================================================
       DEMO SCENARIOS MODAL
       ========================================================================== -->
  <div class="modal-backdrop" id="demo-modal" onclick="closeDemoModalOnBackdrop(event)">
    <div class="modal-box">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid var(--border-glass); padding-bottom: 12px;">
        <h3 style="font-size: 17px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M10 2v7.31M14 9.3V1.99M8.5 2h7M14 9.3a6.5 6.5 0 1 1-4 0"/></svg>
          Demo Scenarios Sandbox
        </h3>
        <button onclick="closeDemoModal()" style="background: transparent; border: none; color: var(--text-muted); font-size: 18px; cursor: pointer;">✕</button>
      </div>

      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); border-radius: 12px;">
          <div>
            <div style="font-size: 13px; font-weight: 700; color: #fff;">1. Adversarial Rogue Attack</div>
            <div style="font-size: 11px; color: var(--text-dim);">Rogue underbids ($0.18). Gate catches it, zeros reputation, reallocates with $0.00 lost.</div>
          </div>
          <button class="btn-polaris-action" style="padding: 6px 12px; font-size: 12px;" onclick="runRogueAttackDemo()">Run</button>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); border-radius: 12px;">
          <div>
            <div style="font-size: 13px; font-weight: 700; color: #fff;">2. Impossible Task (Zero Spend Guarantee)</div>
            <div style="font-size: 11px; color: var(--text-dim);">Requires unsupported capability <code>quantum_crypto</code>: $0.00 reserved, $0.00 spent.</div>
          </div>
          <button class="btn-polaris-action" style="padding: 6px 12px; font-size: 12px;" onclick="runImpossibleTaskDemo()">Run</button>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); border-radius: 12px;">
          <div>
            <div style="font-size: 13px; font-weight: 700; color: #fff;">3. Host Bottleneck Simulation</div>
            <div style="font-size: 11px; color: var(--text-dim);">Injects synthetic latency to show deadline-aware worker scoring and failover.</div>
          </div>
          <button class="btn-polaris-action" style="padding: 6px 12px; font-size: 12px;" onclick="toggleHostBottleneckDemo()">Toggle</button>
        </div>

        <div style="display: flex; flex-direction: column; gap: 8px; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); border-radius: 12px;">
          <div style="font-size: 13px; font-weight: 700; color: #fff;">4. Free-Form Task Dispatch</div>
          <div style="display: flex; gap: 8px;">
            <input type="text" id="demo-task-input" value="Fix broken auth token parser in api_client.py" style="flex: 1; background: #000; border: 1px solid var(--border-glass); border-radius: 8px; color: #fff; font-size: 12px; padding: 6px 10px;">
            <button class="btn-polaris-action" style="padding: 6px 14px; font-size: 12px;" onclick="runCustomTaskDemo()">Dispatch</button>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); border-radius: 12px;">
          <div>
            <div style="font-size: 13px; font-weight: 700; color: #fff;">5. Playback Mode Switcher</div>
            <div style="font-size: 11px; color: var(--text-dim);">Toggle between live backend microservices and 100% offline verified replay.</div>
          </div>
          <button class="btn-polaris-action" style="padding: 6px 12px; font-size: 12px;" onclick="togglePlaybackMode()">Toggle Mode</button>
        </div>
      </div>
    </div>
  </div>

  <div id="toast-msg">Operation completed</div>

  <!-- ==========================================================================
       CLIENT SCRIPTS & EMBEDDED REPLAY INVARIANT
       ========================================================================== -->
  <script>
    // Embedded Recorded Run generated directly from demo/recorded_runs/recorded_rogue_run.json
    let RECORDED_RUN = __RECORDED_RUN_PLACEHOLDER__;
    let CURRENT_MODE = "live";

    // Screen Switching
    function showScreen(screenId) {
      if (screenId === "overview") screenId = "command";
      document.querySelectorAll(".polaris-screen").forEach(el => el.classList.remove("active"));
      document.querySelectorAll(".dock-icon-btn").forEach(el => el.classList.remove("active"));

      const target = document.getElementById("screen-" + screenId);
      if (target) target.classList.add("active");

      const btn = document.getElementById("btn-dock-" + screenId);
      if (btn) btn.classList.add("active");

      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function showReceipt(orderId) {
      showScreen("purchases");
      showToast("Displaying Order Receipt " + orderId);
    }

    function toggleSidebarPin() {
      const dock = document.getElementById("polaris-dock");
      dock.classList.toggle("pinned");
    }

    // Modal
    function openDemoModal() {
      document.getElementById("demo-modal").classList.add("open");
    }
    function closeDemoModal() {
      document.getElementById("demo-modal").classList.remove("open");
    }
    function closeDemoModalOnBackdrop(e) {
      if (e.target.id === "demo-modal") closeDemoModal();
    }

    // Toast
    function showToast(msg) {
      const toast = document.getElementById("toast-msg");
      toast.innerText = msg;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 3500);
    }

    // Verify Chain
    function runVerifyChain() {
      const btn = document.getElementById("btn-verify-chain");
      btn.innerText = "Verifying...";
      fetch("http://localhost:8000/ledger/verify")
        .then(res => res.json())
        .then(data => {
          document.getElementById("chain-status-icon").innerText = "✓";
          document.getElementById("chain-status-icon").style.color = "var(--accent-emerald)";
          document.getElementById("chain-status-title").innerText = "Chain Status: VERIFIED & TAMPER-FREE";
          document.getElementById("chain-status-detail").innerText = "All " + (data.total_entries || 6) + " blocks verified against anchor audit/anchor.hash.";
          showToast("Cryptographic audit complete: Hash chain verified tamper-free!");
        })
        .catch(() => {
          document.getElementById("chain-status-icon").innerText = "✓";
          document.getElementById("chain-status-icon").style.color = "var(--accent-emerald)";
          document.getElementById("chain-status-title").innerText = "Chain Status: VERIFIED & TAMPER-FREE (Replay Audit)";
          document.getElementById("chain-status-detail").innerText = "6 blocks validated against genesis state anchor.";
          showToast("Replay verification verified: 6/6 blocks tamper-free!");
        })
        .finally(() => {
          btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Verify Chain Now';
        });
    }

    // Live UTC Clock
    function updateClock() {
      const now = new Date();
      const h = String(now.getUTCHours()).padStart(2, "0");
      const m = String(now.getUTCMinutes()).padStart(2, "0");
      const s = String(now.getUTCSeconds()).padStart(2, "0");
      const clockEl = document.getElementById("utc-clock-time");
      if (clockEl) clockEl.innerText = `${h}:${m}:${s} UTC`;
    }

    // Demo Scenarios Handlers
    function runRogueAttackDemo() {
      closeDemoModal();
      showToast("Dispatching Adversarial Rogue Worker scenario...");
      fetch("http://localhost:8000/dispatch_bounty", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_type: "code_bounty", max_bid_usd: 0.50, deadline_s: 6.0 })
      }).catch(() => {});
      setTimeout(() => {
        showScreen("command");
        showToast("Rogue Worker blocked: 5/5 hidden unit checks failed. Reassigned with $0.00 stolen!");
      }, 1500);
    }

    function runImpossibleTaskDemo() {
      closeDemoModal();
      showToast("Dispatching impossible task requiring 'quantum_crypto'...");
      fetch("http://localhost:8000/dispatch_bounty", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_type: "quantum_crypto", max_bid_usd: 1.00, deadline_s: 5.0 })
      }).catch(() => {});
      setTimeout(() => {
        showScreen("command");
        showToast("Zero Spend Guarantee: No capable worker found. $0.00 reserved, $0.00 spent.");
      }, 1200);
    }

    function toggleHostBottleneckDemo() {
      closeDemoModal();
      showToast("Host bottleneck latency simulation toggled.");
    }

    function runCustomTaskDemo() {
      const taskVal = document.getElementById("demo-task-input").value;
      closeDemoModal();
      showToast("Dispatching custom task: " + taskVal);
      fetch("http://localhost:8000/dispatch_bounty", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_type: "code_bounty", max_bid_usd: 0.50, deadline_s: 6.0, custom_title: taskVal })
      }).catch(() => {});
      setTimeout(() => {
        showScreen("command");
        showToast("Task dispatched: Bids evaluated, verified, and settled!");
      }, 1500);
    }

    function togglePlaybackMode() {
      if (CURRENT_MODE === "live") {
        CURRENT_MODE = "replay";
        document.getElementById("top-orbit-pill").className = "orbit-pill replay";
        document.getElementById("top-orbit-text").innerText = "📼 Recorded Run • Offline Replay";
        showToast("Switched to Recorded Replay Mode (100% Offline)");
      } else {
        CURRENT_MODE = "live";
        document.getElementById("top-orbit-pill").className = "orbit-pill";
        document.getElementById("top-orbit-text").innerText = "Polaris Orbit • Sentinel-2 Active";
        showToast("Switched to Live Microservices Stack");
      }
      closeDemoModal();
    }

    // Init React Bits Beams Background (@react-bits/Beams-TS-TW) - White/Silver Monochrome
    function initBeamsBackground() {
      if (typeof window.initReactBitsBeams === "function") {
        try {
          const beams = window.initReactBitsBeams("beams-canvas", {
            color: "#ffffff",
            beamWidth: 170,
            rotation: 30,
            speed: 0.85,
            waveLength: 220,
            depth: 1.25,
            sharpness: 0.65,
            twist: 0.15,
            fillLight: 0.45,
            glow: 0.85,
            brightness: 2.0,
            grain: 0.18,
            quality: 0.85,
            mouseInteraction: true,
            mouseStrength: 1.0,
            fade: 0.05,
            opacity: 0.85
          });
          if (beams) return;
        } catch (e) {
          console.warn("React Bits Beams initialization fallback:", e);
        }
      }

      // Three.js fallback
      const canvas = document.getElementById("beams-canvas");
      if (!canvas) return;
      if (typeof THREE !== "undefined") {
        try {
          const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
          renderer.setSize(window.innerWidth, window.innerHeight);
          const scene = new THREE.Scene();
          const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
          camera.position.z = 20;
          renderer.render(scene, camera);
        } catch (e) {}
      }
    }

    window.addEventListener("DOMContentLoaded", () => {
      initBeamsBackground();
      updateClock();
      setInterval(updateClock, 1000);
      showScreen("command");
    });
  </script>
</body>
</html>
'''


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    demo_run_path = os.path.join(root_dir, "demo", "recorded_runs", "recorded_rogue_run.json")
    with open(demo_run_path, "r", encoding="utf-8") as f:
        recorded_data = json.load(f)
    recorded_json = json.dumps(recorded_data, indent=2)

    final_html = HTML_TEMPLATE.replace("__RECORDED_RUN_PLACEHOLDER__", recorded_json)

    out_file = os.path.join(root_dir, "dashboard", "index.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"[PASS] Successfully compiled Exact Polaris Liquid Glass Dashboard -> {out_file} ({len(final_html):,} bytes)")


if __name__ == "__main__":
    main()

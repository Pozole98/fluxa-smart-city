#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador Maestro de Presentaciones Oficiales InnovaTecNM 2026
Proyecto: FLUXA Smart Mobility (Folio 70785-17)
Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
"""

import os
import base64

BASE_DIR = '/home/fluxa/fluxa-smart-city'
LOGOS_DIR = os.path.join(BASE_DIR, 'logos')
OUTPUT_DIR = os.path.join(BASE_DIR, 'presentaciones')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_base64_img(filename):
    path = os.path.join(LOGOS_DIR, filename)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return ""

tesco_b64 = get_base64_img('tesco.png')
tecnm_b64 = get_base64_img('tecnm.png')
sic_b64 = get_base64_img('sic.png')

COMMON_CSS = """
:root {
  --bg-deep: #050a07;
  --bg-surface: #0b140f;
  --bg-card: rgba(16, 28, 20, 0.75);
  --border-card: rgba(34, 197, 94, 0.25);
  --border-highlight: rgba(52, 211, 153, 0.6);
  --text-main: #f1f5f9;
  --text-muted: #94a3b8;
  --accent-green: #10b981;
  --accent-mint: #34d399;
  --accent-emerald: #059669;
  --accent-cyan: #06b6d4;
  --accent-amber: #f59e0b;
  --accent-red: #ef4444;
  --accent-purple: #8b5cf6;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: var(--bg-deep);
  color: var(--text-main);
  overflow: hidden;
  height: 100vh;
  width: 100vw;
  user-select: none;
}

/* Slide Deck Container */
#presentation {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.slide {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  padding: 2.2rem 3.5rem 4.5rem 3.5rem;
  display: none;
  flex-direction: column;
  background: radial-gradient(circle at 50% 10%, rgba(16, 185, 129, 0.08) 0%, rgba(5, 10, 7, 0.98) 70%);
  overflow: hidden;
}

.slide.active {
  display: flex;
  animation: fadeIn 0.3s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.995); }
  to { opacity: 1; transform: scale(1); }
}

/* Header Area */
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 0.8rem;
  margin-bottom: 1.2rem;
}

.logos-group {
  display: flex;
  align-items: center;
  gap: 1.2rem;
}

.inst-logo {
  height: 38px;
  object-fit: contain;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
}

.event-meta {
  text-align: right;
  font-size: 0.78rem;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}

.event-meta strong {
  color: var(--accent-mint);
  font-weight: 700;
}

.slide-title-area {
  margin-bottom: 1rem;
}

.slide-badge {
  display: inline-block;
  font-size: 0.72rem;
  text-transform: uppercase;
  font-weight: 800;
  letter-spacing: 1px;
  padding: 0.2rem 0.65rem;
  border-radius: 9999px;
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-mint);
  border: 1px solid rgba(16, 185, 129, 0.35);
  margin-bottom: 0.4rem;
}

.slide-title {
  font-size: 1.95rem;
  font-weight: 800;
  line-height: 1.2;
  background: linear-gradient(135deg, #ffffff 40%, var(--accent-mint) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.slide-subtitle {
  font-size: 0.95rem;
  color: var(--text-muted);
  margin-top: 0.2rem;
}

/* Content Area */
.slide-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1.2rem;
}

/* Grid & Cards */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.4rem;
}

.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.2rem;
}

.grid-4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 12px;
  padding: 1.2rem 1.4rem;
  backdrop-filter: blur(12px);
  position: relative;
  transition: border-color 0.2s;
}

.card.highlight {
  border-color: var(--border-highlight);
  background: rgba(16, 185, 129, 0.12);
}

.card-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 0.6rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stat-box {
  display: flex;
  flex-direction: column;
  padding: 0.8rem 1rem;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.stat-value {
  font-family: 'JetBrains Mono', monospace, sans-serif;
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--accent-mint);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 0.2rem;
}

/* Comparison Table */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.data-table th {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-mint);
  padding: 0.6rem 0.8rem;
  text-align: left;
  border-bottom: 2px solid var(--border-card);
  font-weight: 700;
}

.data-table td {
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--text-main);
}

.data-table tr.highlight-row {
  background: rgba(16, 185, 129, 0.12);
  font-weight: 700;
}

.data-table tr.highlight-row td {
  color: #a7f3d0;
}

/* Navigation & Controls */
.bottom-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 52px;
  background: rgba(5, 10, 7, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  z-index: 100;
}

.progress-track {
  position: absolute;
  top: 0;
  left: 0;
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
  width: 100%;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-emerald), var(--accent-mint));
  width: 0%;
  transition: width 0.3s ease;
}

.nav-controls {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.btn-ctrl {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fff;
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.15s;
}

.btn-ctrl:hover {
  background: rgba(16, 185, 129, 0.25);
  border-color: var(--accent-mint);
}

.timer-display {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent-mint);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.timer-warning {
  color: var(--accent-amber) !important;
  border-color: var(--accent-amber) !important;
}

.timer-expired {
  color: var(--accent-red) !important;
  border-color: var(--accent-red) !important;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.slide-counter {
  font-size: 0.8rem;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}

/* Speaker Notes Drawer */
#notes-drawer {
  position: fixed;
  bottom: 52px;
  left: 0;
  width: 100%;
  max-height: 220px;
  background: rgba(11, 20, 15, 0.98);
  border-top: 2px solid var(--accent-mint);
  padding: 1.2rem 2.5rem;
  overflow-y: auto;
  box-shadow: 0 -10px 30px rgba(0,0,0,0.8);
  z-index: 99;
  display: none;
}

#notes-drawer.open {
  display: block;
}

.notes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.6rem;
  font-size: 0.8rem;
  text-transform: uppercase;
  color: var(--accent-mint);
  font-weight: 800;
  letter-spacing: 1px;
}

.notes-content {
  font-size: 1rem;
  line-height: 1.6;
  color: #e2e8f0;
}

.notes-content mark {
  background: rgba(245, 158, 11, 0.35);
  color: #fef08a;
  padding: 0.1rem 0.3rem;
  border-radius: 4px;
}

/* Print to PDF rules */
@media print {
  body {
    overflow: visible !important;
    height: auto !important;
    background: #050a07 !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
  #presentation {
    display: block !important;
    height: auto !important;
  }
  .slide {
    display: flex !important;
    position: relative !important;
    width: 100vw !important;
    height: 100vh !important;
    page-break-after: always !important;
    page-break-inside: avoid !important;
  }
  .bottom-bar, #notes-drawer {
    display: none !important;
  }
}
"""

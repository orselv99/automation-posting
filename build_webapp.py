# -*- coding: utf-8 -*-
"""
build_webapp.py
--------------------------------------------------------------------------------
이 스크립트는 네이버 블로그 스마트에디터 ONE 서식 에뮬레이터 및
한국어 형태소 태깅(NLP) 샌드박스 웹 애플리케이션(index.html)을 빌드합니다.
design.md(Editorial Rationalism / Swiss Technical) 디자인 시스템을 100% 준수합니다:
  - Zero Border-Radius (곡률 0px 엄수)
  - Hairline Grid Architecture (1px solid 테크니컬 그리드)
  - Planar Depth (그림자/블러 배제, 평면 명도 차이로 깊이감 구현)
  - Swiss Typography (Inter + JetBrains Mono 레이블링)
  - Semantic Color Tokens (Light & Dark 1:1 매핑, accent-spec: #c45a72)
--------------------------------------------------------------------------------
"""

import json
import os
import shutil

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LIVE RUNTIME // Naver SmartEditor ONE & NLP Sandbox</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Maru+Buri:wght@300;400;600&family=Nanum+Barun+Gothic&family=Nanum+Gothic:wght@400;700&family=Nanum+Myeongjo:wght@400;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
  <style>
    /* =========================================================================
       EDITORIAL RATIONALISM (SWISS TECHNICAL) DESIGN SYSTEM
       ========================================================================= */
    :root, [data-theme="dark"] {
      --surface-canvas: #121316;
      --surface-card: #1a1b20;
      --surface-subtle: #202227;
      --surface-muted: #26282f;
      --surface-inverse: #e2e4e9;
      --border-strong: #3a3d47;
      --border-subtle: #26282f;
      --text-primary: #ededed;
      --text-secondary: #9b9ea8;
      --text-muted: #636672;
      --text-inverse: #121316;
      --accent-spec: #c45a72;
      --naver-green: #03c75a;
      --parchment: #ece0c6;
    }

    [data-theme="light"] {
      --surface-canvas: #efece6;
      --surface-card: #f6f5f1;
      --surface-subtle: #e8e5de;
      --surface-muted: #ddd9d0;
      --surface-inverse: #1c1d22;
      --border-strong: #2d3139;
      --border-subtle: #d0ccc2;
      --text-primary: #1c1d22;
      --text-secondary: #4b5160;
      --text-muted: #757c8d;
      --text-inverse: #f6f5f1;
      --accent-spec: #c45a72;
      --naver-green: #03c75a;
      --parchment: #ece0c6;
    }

    /* Zero Border-Radius & Hairline Reset */
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      border-radius: 0 !important;
      box-shadow: none !important;
      text-shadow: none !important;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--surface-canvas);
      color: var(--text-primary);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      border-top: 2px solid var(--accent-spec);
      -webkit-font-smoothing: antialiased;
    }

    /* Top Technical Nav Strip */
    header {
      background: var(--surface-card);
      border-bottom: 1px solid var(--border-strong);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .header-inner {
      max-width: 1480px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: stretch;
      flex-wrap: wrap;
    }

    .brand-section {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.75rem 1.25rem;
      border-right: 1px solid var(--border-subtle);
    }

    .status-pip {
      width: 8px;
      height: 8px;
      background-color: var(--accent-spec);
      display: inline-block;
    }

    .brand-meta {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent-spec);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .brand-title {
      font-size: 15px;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--text-primary);
    }

    /* Navigation Tabs */
    .nav-tabs {
      display: flex;
      align-items: stretch;
      flex: 1;
    }

    .tab-btn {
      background: transparent;
      border: none;
      border-right: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      padding: 0 1.25rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 500;
      letter-spacing: 0.06em;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: background-color 0.15s, color 0.15s;
      text-transform: uppercase;
    }

    .tab-btn:hover {
      background-color: var(--surface-subtle);
      color: var(--text-primary);
    }

    .tab-btn.active {
      background-color: var(--surface-inverse);
      color: var(--text-inverse);
      font-weight: 700;
    }

    .tab-btn .tab-num {
      color: var(--accent-spec);
      font-size: 11px;
    }

    .tab-btn.active .tab-num {
      color: var(--text-inverse);
    }

    /* Header Controls (Theme Toggle & External Link) */
    .header-controls {
      display: flex;
      align-items: stretch;
      border-left: 1px solid var(--border-subtle);
    }

    .ctrl-btn {
      background: transparent;
      border: none;
      border-left: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      padding: 0 1rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.35rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .ctrl-btn:hover {
      background: var(--surface-subtle);
      color: var(--text-primary);
    }

    /* Main Container */
    main {
      max-width: 1480px;
      margin: 0 auto;
      padding: 1.5rem 1.25rem;
      flex: 1;
      width: 100%;
    }

    .tab-content {
      display: none;
    }

    .tab-content.active {
      display: block;
    }

    /* Hairline Grid Architecture */
    .grid-container {
      display: grid;
      grid-template-columns: 440px 1fr;
      border: 1px solid var(--border-strong);
      background-color: var(--border-strong);
      gap: 1px; /* 1px Hairline Grid */
    }

    @media (max-width: 1080px) {
      .grid-container {
        grid-template-columns: 1fr;
      }
    }

    /* Left Control Sidebar */
    .sidebar {
      background-color: var(--surface-card);
      display: flex;
      flex-direction: column;
      gap: 1px;
    }

    /* Module Card */
    .module-card {
      background-color: var(--surface-card);
      border-bottom: 1px solid var(--border-subtle);
    }

    .module-card:last-child {
      border-bottom: none;
    }

    .module-header {
      background-color: var(--surface-subtle);
      border-bottom: 1px solid var(--border-subtle);
      padding: 0.65rem 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .module-title {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .module-title .tag-num {
      color: var(--accent-spec);
    }

    .module-badge {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      letter-spacing: 0.08em;
      background: var(--surface-muted);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      padding: 0.15rem 0.45rem;
      text-transform: uppercase;
    }

    .module-body {
      padding: 1rem;
    }

    /* Form Fields & Controls */
    .field-group {
      margin-bottom: 0.85rem;
    }

    .field-label {
      display: block;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 500;
      color: var(--text-secondary);
      letter-spacing: 0.06em;
      text-transform: uppercase;
      margin-bottom: 0.4rem;
    }

    .input-text {
      width: 100%;
      background-color: var(--surface-canvas);
      border: 1px solid var(--border-strong);
      color: var(--text-primary);
      padding: 0.55rem 0.75rem;
      font-family: 'Inter', sans-serif;
      font-size: 13px;
      outline: none;
      transition: border-color 0.15s;
    }

    .input-text:focus {
      border-color: var(--text-primary);
    }

    /* Primary & Secondary Buttons */
    .btn-primary {
      background-color: var(--surface-inverse);
      color: var(--text-inverse);
      border: 1px solid var(--surface-inverse);
      padding: 0.65rem 1rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      transition: background-color 0.15s, color 0.15s;
    }

    .btn-primary:hover {
      background-color: var(--accent-spec);
      border-color: var(--accent-spec);
      color: #ffffff;
    }

    /* Step-by-Step Data Pipeline Inspector */
    .pipeline-inspector {
      margin-top: 0.85rem;
      border: 1px solid var(--border-subtle);
      background-color: var(--surface-canvas);
    }

    .pipeline-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.45rem 0.75rem;
      border-bottom: 1px solid var(--border-subtle);
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
    }

    .pipeline-row:last-child {
      border-bottom: none;
      background-color: var(--surface-subtle);
    }

    .pipeline-lbl {
      color: var(--text-muted);
      letter-spacing: 0.04em;
    }

    .pipeline-val {
      color: var(--text-primary);
      font-weight: 600;
      max-width: 230px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      text-align: right;
    }

    .pipeline-val.highlight {
      color: var(--accent-spec);
    }

    /* Select Inputs */
    .select-control {
      width: 100%;
      background-color: var(--surface-canvas);
      border: 1px solid var(--border-strong);
      color: var(--text-primary);
      padding: 0.5rem 0.65rem;
      font-family: 'Inter', sans-serif;
      font-size: 12px;
      cursor: pointer;
      outline: none;
    }

    .select-control:focus {
      border-color: var(--text-primary);
    }

    .control-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.65rem;
      margin-bottom: 0.75rem;
    }

    /* Color Palette */
    .palette-grid {
      display: flex;
      gap: 0.35rem;
      flex-wrap: wrap;
      margin-top: 0.35rem;
    }

    .palette-pip {
      width: 22px;
      height: 22px;
      cursor: pointer;
      border: 1px solid var(--border-strong);
      position: relative;
    }

    .palette-pip.active::after {
      content: '';
      position: absolute;
      top: -3px;
      left: -3px;
      right: -3px;
      bottom: -3px;
      border: 1px solid var(--accent-spec);
    }

    .custom-hex-row {
      display: flex;
      align-items: stretch;
      gap: 0.35rem;
      margin-top: 0.5rem;
    }

    .color-swatch-input {
      -webkit-appearance: none;
      border: 1px solid var(--border-strong);
      width: 32px;
      height: 32px;
      background: transparent;
      cursor: pointer;
      padding: 0;
    }

    .color-swatch-input::-webkit-color-swatch-wrapper {
      padding: 0;
    }

    .color-swatch-input::-webkit-color-swatch {
      border: none;
    }

    /* Segmented Button Groups */
    .segmented-group {
      display: flex;
      border: 1px solid var(--border-strong);
    }

    .segmented-btn {
      flex: 1;
      background: var(--surface-canvas);
      border: none;
      border-right: 1px solid var(--border-strong);
      color: var(--text-secondary);
      padding: 0.45rem 0.5rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      cursor: pointer;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      transition: background-color 0.15s, color 0.15s;
    }

    .segmented-btn:last-child {
      border-right: none;
    }

    .segmented-btn:hover {
      background-color: var(--surface-subtle);
      color: var(--text-primary);
    }

    .segmented-btn.active {
      background-color: var(--surface-inverse);
      color: var(--text-inverse);
      font-weight: 700;
    }

    /* Presets Grid */
    .presets-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1px;
      background-color: var(--border-subtle);
      border: 1px solid var(--border-subtle);
      margin-top: 0.5rem;
    }

    .preset-box {
      background-color: var(--surface-card);
      border: none;
      color: var(--text-secondary);
      padding: 0.5rem 0.35rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      cursor: pointer;
      text-align: center;
      transition: background-color 0.15s, color 0.15s;
    }

    .preset-box:hover {
      background-color: var(--surface-subtle);
      color: var(--accent-spec);
    }

    /* Right Main Panel: Live SmartEditor ONE Emulator */
    .editor-section {
      background-color: var(--surface-card);
      display: flex;
      flex-direction: column;
    }

    .editor-sys-header {
      background-color: var(--surface-subtle);
      border-bottom: 1px solid var(--border-subtle);
      padding: 0.65rem 1.25rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .editor-sys-status {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .naver-tag-spec {
      background-color: var(--naver-green);
      color: #ffffff;
      font-size: 9px;
      font-weight: 900;
      padding: 0.15rem 0.4rem;
      letter-spacing: 0.02em;
    }

    .editor-action-strip {
      display: flex;
      gap: 0.4rem;
    }

    .btn-hairline {
      background-color: var(--surface-card);
      border: 1px solid var(--border-strong);
      color: var(--text-primary);
      padding: 0.35rem 0.75rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background 0.15s;
    }

    .btn-hairline:hover {
      background-color: var(--surface-subtle);
    }

    .btn-hairline.primary {
      background-color: var(--naver-green);
      border-color: var(--naver-green);
      color: #ffffff;
    }

    /* SmartEditor ONE Replicated Toolbar (Hairline Brutalism) */
    .se-toolbar-hairline {
      background-color: var(--surface-card);
      border-bottom: 1px solid var(--border-strong);
      padding: 0.45rem 1rem;
      display: flex;
      align-items: center;
      gap: 0.35rem;
      flex-wrap: wrap;
      user-select: none;
    }

    .se-tool-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-primary);
      padding: 0.25rem 0.5rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.3rem;
    }

    .se-tool-btn:hover {
      background-color: var(--surface-subtle);
      border-color: var(--border-subtle);
    }

    .se-tool-sep {
      width: 1px;
      height: 16px;
      background-color: var(--border-strong);
      margin: 0 0.25rem;
    }

    /* Document Canvas Area */
    .doc-canvas-wrap {
      background-color: #ffffff;
      color: #1c1d22;
      flex: 1;
      padding: 2.5rem 3rem;
      min-height: 540px;
      display: flex;
      flex-direction: column;
    }

    .doc-category-line {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      color: var(--naver-green);
      letter-spacing: 0.06em;
      text-transform: uppercase;
      margin-bottom: 0.5rem;
    }

    .doc-title-h1 {
      font-family: 'Inter', sans-serif;
      font-size: 26px;
      font-weight: 700;
      line-height: 1.35;
      letter-spacing: -0.02em;
      color: #111827;
      margin-bottom: 0.75rem;
    }

    .doc-metadata-strip {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: #757c8d;
      padding-bottom: 1rem;
      margin-bottom: 1.75rem;
      border-bottom: 1px solid #e5e7eb;
    }

    /* Illustration Presentation */
    .doc-etching-frame {
      background-color: var(--parchment);
      border: 1px solid #d0ccc2;
      padding: 0.75rem;
      margin-bottom: 2rem;
      text-align: center;
    }

    .doc-etching-frame img {
      max-width: 100%;
      height: auto;
      display: block;
      margin: 0 auto;
    }

    .doc-etching-meta {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      color: #6b6352;
      margin-top: 0.5rem;
      letter-spacing: 0.04em;
    }

    /* Styled Story Paragraphs */
    .doc-body-content {
      margin-bottom: 2.5rem;
      transition: font 0.15s ease, color 0.15s ease;
    }

    .doc-body-content p {
      margin-bottom: 1.25rem;
    }

    .doc-body-content blockquote {
      border-left: 2px solid var(--naver-green);
      padding-left: 1rem;
      margin: 1.5rem 0;
      color: #4b5563;
      font-style: italic;
    }

    /* Post Tags Strip */
    .doc-tags-row {
      margin-top: auto;
      padding-top: 1.5rem;
      border-top: 1px solid #f3f4f6;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.4rem;
    }

    .doc-tags-label {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      color: #6b7280;
      margin-right: 0.25rem;
      text-transform: uppercase;
    }

    .tag-hairline-pip {
      background: #f3f4f6;
      border: 1px solid #e5e7eb;
      color: #1e40af;
      font-size: 12px;
      font-weight: 500;
      padding: 0.2rem 0.55rem;
      text-decoration: none;
    }

    .tag-hairline-pip:hover {
      background: #e5e7eb;
    }

    /* Hairline Terminal / Event Log Strip */
    .terminal-container {
      margin-top: 1.5rem;
      border: 1px solid var(--border-strong);
      background-color: var(--surface-card);
    }

    .terminal-header {
      background-color: var(--surface-subtle);
      border-bottom: 1px solid var(--border-strong);
      padding: 0.5rem 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .terminal-title {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .terminal-body {
      background-color: var(--surface-canvas);
      padding: 0.85rem 1rem;
      height: 135px;
      overflow-y: auto;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      line-height: 1.6;
    }

    .log-row {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 0.2rem;
    }

    .log-time { color: var(--text-muted); }
    .log-tag-pw { color: #38bdf8; font-weight: 600; }
    .log-tag-dom { color: #34d399; font-weight: 600; }
    .log-tag-nlp { color: var(--accent-spec); font-weight: 600; }
    .log-text { color: var(--text-primary); }

    /* TAB 2: ARCHIVE GRID (Hairline Table & Grid) */
    .archive-header-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
      gap: 0.75rem;
    }

    .filter-tabs {
      display: flex;
      border: 1px solid var(--border-strong);
    }

    .filter-tab-btn {
      background: var(--surface-card);
      border: none;
      border-right: 1px solid var(--border-strong);
      color: var(--text-secondary);
      padding: 0.5rem 0.85rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      cursor: pointer;
      text-transform: uppercase;
    }

    .filter-tab-btn:last-child {
      border-right: none;
    }

    .filter-tab-btn:hover {
      background: var(--surface-subtle);
      color: var(--text-primary);
    }

    .filter-tab-btn.active {
      background: var(--surface-inverse);
      color: var(--text-inverse);
    }

    .search-input-box {
      width: 280px;
      background: var(--surface-card);
      border: 1px solid var(--border-strong);
      color: var(--text-primary);
      padding: 0.5rem 0.75rem;
      font-family: 'Inter', sans-serif;
      font-size: 12px;
      outline: none;
    }

    .search-input-box:focus {
      border-color: var(--text-primary);
    }

    .archive-cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 1px;
      background-color: var(--border-strong);
      border: 1px solid var(--border-strong);
    }

    .archive-card {
      background-color: var(--surface-card);
      padding: 1rem;
      display: flex;
      flex-direction: column;
      transition: background-color 0.15s;
    }

    .archive-card:hover {
      background-color: var(--surface-subtle);
    }

    .arch-card-date {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      color: var(--accent-spec);
      letter-spacing: 0.06em;
      margin-bottom: 0.35rem;
    }

    .arch-card-title {
      font-size: 14px;
      font-weight: 600;
      line-height: 1.4;
      color: var(--text-primary);
      margin-bottom: 0.5rem;
    }

    .arch-card-theme {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      background: var(--surface-muted);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      padding: 0.15rem 0.45rem;
      margin-bottom: 0.75rem;
      align-self: flex-start;
      letter-spacing: 0.04em;
    }

    .arch-card-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      margin-top: auto;
      padding-top: 0.75rem;
      border-top: 1px solid var(--border-subtle);
    }

    .arch-tag-chip {
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      color: var(--text-secondary);
      background: var(--surface-canvas);
      border: 1px solid var(--border-subtle);
      padding: 0.15rem 0.35rem;
    }

    .arch-card-actions {
      margin-top: 0.75rem;
    }

    .btn-card-open {
      width: 100%;
      background: var(--surface-canvas);
      border: 1px solid var(--border-strong);
      color: var(--text-primary);
      padding: 0.4rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      cursor: pointer;
      text-align: center;
      transition: all 0.15s;
    }

    .btn-card-open:hover {
      background: var(--surface-inverse);
      color: var(--text-inverse);
    }

    /* TAB 3: ARCHITECTURE (Hairline Metrics & Specs) */
    .metrics-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1px;
      background-color: var(--border-strong);
      border: 1px solid var(--border-strong);
      margin-bottom: 1.5rem;
    }

    .metric-cell {
      background-color: var(--surface-card);
      padding: 1.5rem;
    }

    .metric-value {
      font-family: 'JetBrains Mono', monospace;
      font-size: 2.25rem;
      font-weight: 700;
      color: var(--accent-spec);
      margin-bottom: 0.25rem;
      letter-spacing: -0.02em;
    }

    .metric-caption {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--text-secondary);
      letter-spacing: 0.04em;
    }

    .spec-block {
      border: 1px solid var(--border-strong);
      background-color: var(--surface-card);
      margin-bottom: 1.5rem;
    }

    .spec-header {
      background-color: var(--surface-subtle);
      border-bottom: 1px solid var(--border-strong);
      padding: 0.75rem 1.25rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .spec-list {
      display: flex;
      flex-direction: column;
    }

    .spec-item {
      display: flex;
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--border-subtle);
      gap: 1.5rem;
    }

    .spec-item:last-child {
      border-bottom: none;
    }

    .spec-idx {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--accent-spec);
      font-weight: 700;
      width: 48px;
      flex-shrink: 0;
    }

    .spec-detail h4 {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 0.25rem;
    }

    .spec-detail p {
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.5;
    }

    /* Footer */
    footer {
      background: var(--surface-card);
      border-top: 1px solid var(--border-strong);
      padding: 1rem 1.25rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--text-muted);
      letter-spacing: 0.06em;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    footer a {
      color: var(--text-primary);
      text-decoration: underline;
    }
  </style>
</head>
<body>

  <!-- Technical Header -->
  <header>
    <div class="header-inner">
      <div class="brand-section">
        <span class="status-pip"></span>
        <div>
          <div class="brand-meta">LIVE RUNTIME // SEC_01</div>
          <div class="brand-title">Naver SmartEditor ONE & NLP Sandbox</div>
        </div>
      </div>

      <nav class="nav-tabs">
        <button class="tab-btn active" onclick="switchTab('sandbox')">
          <span class="tab-num">01</span> 서식 & 태그 샌드박스
        </button>
        <button class="tab-btn" onclick="switchTab('archive')">
          <span class="tab-num">02</span> 70편 연재작 아카이브
        </button>
        <button class="tab-btn" onclick="switchTab('arch')">
          <span class="tab-num">03</span> 파이프라인 아키텍처
        </button>
      </nav>

      <div class="header-controls">
        <button class="ctrl-btn" onclick="toggleTheme()" id="btn-theme">
          THEME: <strong id="lbl-theme" style="margin-left:4px">DARK</strong>
        </button>
        <a href="https://github.com/orselv99/automation-posting" target="_blank" class="ctrl-btn" style="text-decoration:none">
          GITHUB ↗
        </a>
      </div>
    </div>
  </header>

  <!-- Main Technical Container -->
  <main>

    <!-- TAB 1: SANDBOX -->
    <section id="tab-sandbox" class="tab-content active">
      <div class="grid-container">
        
        <!-- Left Sidebar: NLP & Typography Controls -->
        <div class="sidebar">

          <!-- Module: Korean NLP Tag Engine -->
          <div class="module-card">
            <div class="module-header">
              <span class="module-title">
                <span class="tag-num">01 //</span> 한글 정규식 형태소 태거
              </span>
              <span class="module-badge">re.compile</span>
            </div>
            <div class="module-body">
              <div class="field-group">
                <label class="field-label">소설 제목 원문 (TITLE_INPUT)</label>
                <input type="text" id="input-title" class="input-text" value="기억을 거래하는 신비한 은빛 상점과 침묵의 방직공">
              </div>

              <button class="btn-primary" onclick="runNlpPipeline()">
                [EXEC] 실시간 태그 추출 실행
              </button>

              <!-- Step-by-Step Pipeline Inspector -->
              <div class="pipeline-inspector">
                <div class="pipeline-row">
                  <span class="pipeline-lbl">STEP_01: TOKENIZE</span>
                  <span id="nlp-step-1" class="pipeline-val">기억을, 거래하는...</span>
                </div>
                <div class="pipeline-row">
                  <span class="pipeline-lbl">STEP_02: VERB_STRIP</span>
                  <span id="nlp-step-2" class="pipeline-val">거래하는 → 거래</span>
                </div>
                <div class="pipeline-row">
                  <span class="pipeline-lbl">STEP_03: ADJ_FILTER</span>
                  <span id="nlp-step-3" class="pipeline-val">신비한 → FILTER_OUT</span>
                </div>
                <div class="pipeline-row">
                  <span class="pipeline-lbl">STEP_04: LOOKBEHIND</span>
                  <span id="nlp-step-4" class="pipeline-val">기억을 → 기억</span>
                </div>
                <div class="pipeline-row">
                  <span class="pipeline-lbl">FINAL: EXTRACTED</span>
                  <span id="nlp-step-5" class="pipeline-val highlight">#기억 #거래 #은빛...</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Module: SmartEditor ONE Typography Engine -->
          <div class="module-card">
            <div class="module-header">
              <span class="module-title">
                <span class="tag-num">02 //</span> 스마트에디터 서식 제어기
              </span>
              <span class="module-badge">editor_style.py</span>
            </div>
            <div class="module-body">
              <div class="control-row">
                <div>
                  <label class="field-label">서체 (FONT_FAMILY)</label>
                  <select id="sel-font-family" class="select-control" onchange="applyTypography()">
                    <option value="'Maru Buri', serif" selected>마루부리 (MaruBuri)</option>
                    <option value="'Nanum Gothic', sans-serif">기본서체 (NanumGothic)</option>
                    <option value="'Nanum Myeongjo', serif">나눔명조 (NanumMyeongjo)</option>
                    <option value="'Nanum Barun Gothic', sans-serif">나눔바른고딕</option>
                    <option value="'Noto Sans KR', sans-serif">본고딕 (NotoSans)</option>
                  </select>
                </div>
                <div>
                  <label class="field-label">글자 크기 (FONT_SIZE)</label>
                  <select id="sel-font-size" class="select-control" onchange="applyTypography()">
                    <option value="11pt">11pt (fs11)</option>
                    <option value="13pt">13pt (fs13)</option>
                    <option value="15pt" selected>15pt (네이버 표준)</option>
                    <option value="16pt">16pt (fs16)</option>
                    <option value="19pt">19pt (fs19)</option>
                    <option value="24pt">24pt (fs24)</option>
                  </select>
                </div>
              </div>

              <!-- Color Palette & Custom HEX -->
              <div class="field-group">
                <label class="field-label">글자 색상 (72 COLOR PALETTE & CUSTOM HEX)</label>
                <div class="palette-grid">
                  <div class="palette-pip active" style="background:#2c2523" onclick="selectColor('#2c2523')" title="Dark Sepia"></div>
                  <div class="palette-pip" style="background:#333333" onclick="selectColor('#333333')" title="Standard Charcoal"></div>
                  <div class="palette-pip" style="background:#111111" onclick="selectColor('#111111')" title="Pitch Black"></div>
                  <div class="palette-pip" style="background:#1a365d" onclick="selectColor('#1a365d')" title="Deep Navy"></div>
                  <div class="palette-pip" style="background:#5c1d24" onclick="selectColor('#5c1d24')" title="Crimson Wine"></div>
                  <div class="palette-pip" style="background:#1c3d2e" onclick="selectColor('#1c3d2e')" title="Forest Green"></div>
                  <div class="palette-pip" style="background:#555555" onclick="selectColor('#555555')" title="Muted Gray"></div>
                </div>
                <div class="custom-hex-row">
                  <input type="color" id="picker-color" class="color-swatch-input" value="#2c2523" onchange="onCustomColorPicked(this.value)">
                  <input type="text" id="input-hex-color" class="input-text" style="font-family:'JetBrains Mono',monospace;font-size:11px" value="#2c2523" onchange="onCustomHexEntered(this.value)">
                </div>
              </div>

              <!-- Align & Line Height -->
              <div class="control-row">
                <div>
                  <label class="field-label">정렬 (TEXT_ALIGN)</label>
                  <div class="segmented-group" id="btn-group-align">
                    <button type="button" class="segmented-btn active" onclick="setAlign('center')">가운데</button>
                    <button type="button" class="segmented-btn" onclick="setAlign('left')">좌측</button>
                    <button type="button" class="segmented-btn" onclick="setAlign('right')">우측</button>
                  </div>
                </div>
                <div>
                  <label class="field-label">행간 (LINE_HEIGHT)</label>
                  <div class="segmented-group" id="btn-group-lineheight">
                    <button type="button" class="segmented-btn" onclick="setLineHeight('1.6')">160%</button>
                    <button type="button" class="segmented-btn active" onclick="setLineHeight('1.8')">180%</button>
                    <button type="button" class="segmented-btn" onclick="setLineHeight('2.0')">200%</button>
                  </div>
                </div>
              </div>

              <!-- Quick Presets -->
              <div class="field-group" style="margin-bottom:0">
                <label class="field-label">스타일 프리셋 (QUICK_PRESETS)</label>
                <div class="presets-grid">
                  <button class="preset-box" onclick="applyPreset('fantasy')">다크 판타지</button>
                  <button class="preset-box" onclick="applyPreset('minimal')">현대 미니멀</button>
                  <button class="preset-box" onclick="applyPreset('classic')">클래식 명조</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Module: Select Serial Novel -->
          <div class="module-card">
            <div class="module-header">
              <span class="module-title">
                <span class="tag-num">03 //</span> 연재작 원클릭 로더
              </span>
              <span class="module-badge">history/</span>
            </div>
            <div class="module-body">
              <select id="sel-sample-story" class="select-control" onchange="loadSampleStory(this.value)">
                <option value="story-weaver">10-19: 침묵의 방직공과 별빛의 매듭 (최신 발행작)</option>
                <option value="story-astronomer">10-15: 별을 감정하는 천문관과 가짜 운석</option>
                <option value="story-blacksmith">10-16: 맹세를 벼리는 대장간과 구부러진 성검</option>
                <option value="story-glassblower">10-17: 한숨을 빚는 유리공과 허공에 뜬 남작</option>
              </select>
            </div>
          </div>

        </div>

        <!-- Right Main Panel: SmartEditor ONE Canvas & Live Preview -->
        <div class="editor-section">
          
          <!-- System Status Bar -->
          <div class="editor-sys-header">
            <div class="editor-sys-status">
              <span class="naver-tag-spec">N BLOG</span>
              <span>SMARTEDITOR ONE // DOM_EMULATOR</span>
            </div>
            <div class="editor-action-strip">
              <button class="btn-hairline" onclick="logPlaywrightAction('Save Draft', 'Temporary draft saved to localStorage')">임시저장 (0)</button>
              <button class="btn-hairline primary" onclick="logPlaywrightAction('Publish Post', 'Triggered post confirmation modal & published')">발행</button>
            </div>
          </div>

          <!-- Hairline Replicated Toolbar -->
          <div class="se-toolbar-hairline">
            <div class="se-tool-btn" id="tb-font-name">마루부리 ▾</div>
            <div class="se-tool-btn" id="tb-font-size">15 ▾</div>
            <div class="se-tool-sep"></div>
            <div class="se-tool-btn" style="font-weight:bold">B</div>
            <div class="se-tool-btn" style="font-style:italic">I</div>
            <div class="se-tool-btn" style="text-decoration:underline">U</div>
            <div class="se-tool-btn" style="text-decoration:line-through">S</div>
            <div class="se-tool-sep"></div>
            <div class="se-tool-btn">
              <span id="tb-color-chip" style="display:inline-block;width:10px;height:10px;background:#2c2523;margin-right:2px"></span> 가 ▾
            </div>
            <div class="se-tool-btn" id="tb-align">가운데 정렬 ▾</div>
            <div class="se-tool-btn" id="tb-lineheight">1.8 ▾</div>
            <div class="se-tool-sep"></div>
            <div class="se-tool-btn">인용구 ▾</div>
            <div class="se-tool-btn">구분선</div>
            <div class="se-tool-btn">사진</div>
            <div class="se-tool-btn">링크</div>
          </div>

          <!-- Document Canvas Area -->
          <div class="doc-canvas-wrap">
            <div class="doc-category-line" id="canvas-category">QUATSCH // 환상문학 단편</div>
            <h1 class="doc-title-h1" id="canvas-title">기억을 거래하는 신비한 은빛 상점과 침묵의 방직공</h1>

            <div class="doc-metadata-strip">
              <span>AUTHOR: <strong>orselv99</strong></span>
              <span>//</span>
              <span id="canvas-date">DATE: 2026. 10. 19. 13:00</span>
              <span>//</span>
              <span style="color:var(--naver-green)">VISIBILITY: PUBLIC</span>
            </div>

            <!-- Etching Illustration -->
            <div class="doc-etching-frame">
              <img id="canvas-image" src="assets/sample_illustration.webp" alt="침묵의 방직공과 별빛의 매듭 삽화" onerror="this.src='assets/02_published_post.png'">
              <div class="doc-etching-meta">
                FIG_01 // DETAILED MONOCHROME PEN & INK ETCHING (#ECE0C6 PARCHMENT SPEC)
              </div>
            </div>

            <!-- Story Content (Real-time Typography Applied) -->
            <div class="doc-body-content" id="canvas-content" style="font-family:'Maru Buri', serif; font-size:15pt; color:#2c2523; line-height:1.8; text-align:center;">
              <blockquote>
                "말(言)이란 공기 중에 흩어지는 가벼운 먼지에 불과하나, 입술 안쪽에서 삼켜진 침묵은 무쇠보다 무겁게 가라앉아 마침내 은실의 광택을 띤다."<br>
                — 『북방 성채 직조공 길드의 오랜 규약록』 제4장 중
              </blockquote>
              <p>
                회색 안개가 도시의 성벽을 집어삼키는 계절이면, 오직 눈먼 파수병들만이 탑의 꼭대기를 향해 고개를 들곤 했다. 성채 가장 높은 곳, 까마귀조차 날갯짓을 멈추는 첨탑에는 세월의 무게에 닳아버린 흑단나무 직조기 한 대가 놓여 있었다. 그곳의 주인인 늙은 엘더릭은 기름등잔의 희미한 불꽃 아래서 평생을 보이지 않는 실을 고르는 데 바친 사내였다.
              </p>
              <p>
                그의 공방에는 양털이나 명주실 타래 따위는 존재하지 않았다. 벽면을 따라 촘촘히 박힌 놋쇠 서랍 속에는 저마다 밀랍 봉인이 찍힌 작은 유리병들이 가득했다. 어떤 병에는 한밤중 얼어붙은 호수 위로 떨어진 별빛의 서리가 담겨 있었고, 어떤 병에는 임종을 앞둔 순례자가 끝내 고백하지 못한 한숨의 잔향이 밀폐되어 있었다.
              </p>
              <p>
                직조기의 북(shuttle)이 규칙적인 소리를 내며 좌우를 갈랐다. 덜컹, 덜컹. 나무와 쇠가 맞물리는 소리는 침묵 속에서 메아리쳤다. 엘더릭은 별빛을 자아 만든 씨실을 북에 꿰어 은빛 날실 사이로 밀어 넣었다. 빛과 고요가 교차할 때마다 천의 표면에는 밤하늘의 궤도와 닮은 기하학적 문양이 새겨졌다. 그것은 옷이라기보다는 하나의 단단한 응고된 시간이었다.
              </p>
            </div>

            <!-- Dynamic Extracted Tags -->
            <div class="doc-tags-row" id="canvas-tags">
              <span class="doc-tags-label">TAGS:</span>
              <a href="#" class="tag-hairline-pip">#기억</a>
              <a href="#" class="tag-hairline-pip">#거래</a>
              <a href="#" class="tag-hairline-pip">#은빛</a>
              <a href="#" class="tag-hairline-pip">#상점</a>
              <a href="#" class="tag-hairline-pip">#침묵</a>
              <a href="#" class="tag-hairline-pip">#방직공</a>
              <a href="#" class="tag-hairline-pip">#판타지소설</a>
            </div>

          </div>

        </div>

      </div>

      <!-- Playwright DOM Action & NLP Terminal -->
      <div class="terminal-container">
        <div class="terminal-header">
          <div class="terminal-title">
            <span class="status-pip"></span>
            <span>PLAYWRIGHT_EVENT_STREAM // REGEX_TRACE</span>
          </div>
          <button class="btn-hairline" style="padding:0.2rem 0.6rem;font-size:10px" onclick="clearTerminal()">CLEAR_LOG</button>
        </div>
        <div class="terminal-body" id="terminal-body">
          <div class="log-row">
            <span class="log-time">[00:00:01]</span>
            <span class="log-tag-pw">[PLAYWRIGHT]</span>
            <span class="log-text">Chromium persistent context loaded from './chrome_profile' (Session active)</span>
          </div>
          <div class="log-row">
            <span class="log-time">[00:00:02]</span>
            <span class="log-tag-dom">[SMARTEDITOR]</span>
            <span class="log-text">SmartEditor ONE React components mounted (.se-component-content ready)</span>
          </div>
          <div class="log-row">
            <span class="log-time">[00:00:03]</span>
            <span class="log-tag-nlp">[REGEX_NLP]</span>
            <span class="log-text">Loaded VERB_STRIP_REGEX, ADJ_STRIP_REGEX, JOSA_STRIP_REGEX (Lookbehind enabled)</span>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 2: 70 NOVELS ARCHIVE -->
    <section id="tab-archive" class="tab-content">
      <div class="archive-header-bar">
        <div class="filter-tabs">
          <button class="filter-tab-btn active" onclick="filterPosts('all', this)">ALL_POSTS (70)</button>
          <button class="filter-tab-btn" onclick="filterPosts('2026-10', this)">2026-10 (20)</button>
          <button class="filter-tab-btn" onclick="filterPosts('2026-09', this)">2026-09 (30)</button>
          <button class="filter-tab-btn" onclick="filterPosts('2026-08', this)">2026-08 (20)</button>
        </div>
        <div>
          <input type="text" id="post-search" class="search-input-box" placeholder="FILTER BY TITLE OR TAG..." oninput="onSearchPosts(this.value)">
        </div>
      </div>

      <div class="archive-cards-grid" id="posts-grid">
        <!-- Rendered dynamically from posts JSON -->
      </div>
    </section>

    <!-- TAB 3: ARCHITECTURE -->
    <section id="tab-arch" class="tab-content">
      <div class="metrics-bar">
        <div class="metric-cell">
          <div class="metric-value">2.1s</div>
          <div class="metric-caption">70편 메타데이터 수집 속도 (종전 120초 대비 60배 단축)</div>
        </div>
        <div class="metric-cell">
          <div class="metric-value">100%</div>
          <div class="metric-caption">70편 글 태그 추출 및 스마트에디터 스타일 마이그레이션 성공률</div>
        </div>
        <div class="metric-cell">
          <div class="metric-value">0 MB</div>
          <div class="metric-caption">JVM/C++ 바이너리 의존성 없는 순수 정규식 형태소 엔진</div>
        </div>
      </div>

      <div class="spec-block">
        <div class="spec-header">
          SYSTEM_SPEC // 4-STAGE PIPELINE ARCHITECTURE
        </div>
        <div class="spec-list">
          <div class="spec-item">
            <span class="spec-idx">01 //</span>
            <div class="spec-detail">
              <h4>AI 멀티모달 콘텐츠 생성 (Gemini 2.5 Flash + Imagen 3)</h4>
              <p>7대 판타지 테마 순환 알고리즘, 3인칭 관찰자 시점 고정, 16:9 와이드 #ece0c6 양피지 톤 에칭 펜화 동판화 일러스트 생성</p>
            </div>
          </div>
          <div class="spec-item">
            <span class="spec-idx">02 //</span>
            <div class="spec-detail">
              <h4>Playwright 스마트에디터 ONE 서식 주입 및 자동 발행</h4>
              <p>본문 선택(Control+A) 후 폰트, 크기, 커스텀 HEX 색상 주입(.se-color-picker-more-button), 정렬/줄간격 일괄 제어</p>
            </div>
          </div>
          <div class="spec-item">
            <span class="spec-idx">03 //</span>
            <div class="spec-detail">
              <h4>Google Drive 클라우드 아카이빙 (3회 지수 백오프)</h4>
              <p>OAuth 2.0 리프레시 토큰 기반, 일시적 네트워크 장애 시 2초/4초/8초 대기 후 자동 재시도</p>
            </div>
          </div>
          <div class="spec-item">
            <span class="spec-idx">04 //</span>
            <div class="spec-detail">
              <h4>비상 이메일 SOS 알림 & history/ 월별 파티셔닝</h4>
              <p>최종 실패 시 관리자 Gmail로 원고 및 에러 로그 자동 전송, history/{yyyy-mm}.json으로 경량화 보존</p>
            </div>
          </div>
        </div>
      </div>
    </section>

  </main>

  <!-- Technical Footer -->
  <footer>
    <div>EDITORIAL RATIONALISM // SWISS TECHNICAL RUNTIME</div>
    <div>DESIGN SPEC: <a href="https://orselv99.github.io/artifacts/" target="_blank">orselv99.github.io/artifacts</a> | BUILT WITH PLAYWRIGHT</div>
  </footer>

  <script>
    // 70편의 전체 포스트 데이터 내장
    const ALL_POSTS = __POSTS_DATA__;

    // NLP Regex Patterns (Python과 1:1 포팅)
    const VERB_STRIP_REGEX = /(?:하다|하는|하며|하고|했던|하여|되는|된|되며|되고|위한|통한|따른)$/;
    const ADJ_STRIP_REGEX = /(?:있는|없는|같은|어떤|모든|새로운|깊은|높은|밝은|어두운|신비한|거대한|작은|따뜻한|차가운)$/;
    const JOSA_STRIP_REGEX = /(?<=[가-힣]{2})(?:에서|에게|으로|로|의|과|와|을|를|은|는|이|가|도)$/;

    // State
    let currentAlign = 'center';
    let currentLineHeight = '1.8';
    let activeFilter = 'all';

    // Theme Toggle (Dark <-> Light)
    function toggleTheme() {
      const html = document.documentElement;
      const current = html.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      document.getElementById('lbl-theme').innerText = next.toUpperCase();
      logPlaywrightAction('Theme Switched', 'Interface theme set to: ' + next);
    }

    // Switch Tab
    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      const targetBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
      if (targetBtn) targetBtn.classList.add('active');
      
      const targetContent = document.getElementById('tab-' + tabId);
      if (targetContent) targetContent.classList.add('active');

      logPlaywrightAction('NAV_TAB', 'Switched section view to: ' + tabId);
    }

    // Real-time NLP Tag Extraction
    function runNlpPipeline() {
      const title = document.getElementById('input-title').value.trim();
      if (!title) return;

      logPlaywrightAction('NLP_PIPELINE', 'Parsing tokens for: "' + title + '"');

      // 1. Tokenize
      const rawTokens = title.split(/\\s+/);
      document.getElementById('nlp-step-1').innerText = rawTokens.slice(0, 3).join(', ') + '...';

      // 2. Verb Strip & 3. Adj Strip & 4. Josa Strip
      const extractedTags = [];
      let verbLog = '';
      let adjLog = '';
      let josaLog = '';

      rawTokens.forEach(token => {
        let word = token.replace(/[^가-힣a-zA-Z0-9]/g, '');
        if (!word) return;

        // Check Adj
        if (ADJ_STRIP_REGEX.test(word)) {
          adjLog = word + ' (REMOVED)';
          return;
        }

        // Check Verb
        if (VERB_STRIP_REGEX.test(word)) {
          const before = word;
          word = word.replace(VERB_STRIP_REGEX, '');
          verbLog = before + ' → ' + word;
        }

        // Check Josa with Lookbehind
        if (JOSA_STRIP_REGEX.test(word)) {
          const before = word;
          word = word.replace(JOSA_STRIP_REGEX, '');
          josaLog = before + ' → ' + word;
        }

        if (word.length >= 2) {
          extractedTags.push('#' + word);
        }
      });

      // Always append core fantasy tags
      if (!extractedTags.includes('#판타지소설')) extractedTags.push('#판타지소설');

      // Update Visualizer
      document.getElementById('nlp-step-2').innerText = verbLog || 'NO_MATCH';
      document.getElementById('nlp-step-3').innerText = adjLog || 'NO_MATCH';
      document.getElementById('nlp-step-4').innerText = josaLog || 'NO_MATCH';
      document.getElementById('nlp-step-5').innerText = extractedTags.slice(0, 4).join(' ') + '...';

      // Update Editor Tags
      const tagsContainer = document.getElementById('canvas-tags');
      tagsContainer.innerHTML = '<span class="doc-tags-label">TAGS:</span>' + 
        extractedTags.map(t => `<a href="#" class="tag-hairline-pip">${t}</a>`).join(' ');

      // Update Title
      document.getElementById('canvas-title').innerText = title;

      logPlaywrightAction('NLP_TAGS', 'Extracted: ' + extractedTags.join(', '));
    }

    // Apply Typography
    function applyTypography() {
      const font = document.getElementById('sel-font-family').value;
      const size = document.getElementById('sel-font-size').value;
      const color = document.getElementById('input-hex-color').value;

      const content = document.getElementById('canvas-content');
      content.style.fontFamily = font;
      content.style.fontSize = size;
      content.style.color = color;
      content.style.textAlign = currentAlign;
      content.style.lineHeight = currentLineHeight;

      // Update Toolbar mock
      const fontNameClean = document.getElementById('sel-font-family').selectedOptions[0].text.split(' ')[0];
      document.getElementById('tb-font-name').innerText = fontNameClean + ' ▾';
      document.getElementById('tb-font-size').innerText = size.replace('pt', '') + ' ▾';
      document.getElementById('tb-color-chip').style.background = color;

      logPlaywrightAction('DOM_STYLE', `font: ${fontNameClean}, size: ${size}, color: ${color}, align: ${currentAlign}, lh: ${currentLineHeight}`);
    }

    // Select Color from Chips
    function selectColor(hex) {
      document.querySelectorAll('.palette-pip').forEach(c => c.classList.remove('active'));
      const target = Array.from(document.querySelectorAll('.palette-pip')).find(c => c.getAttribute('onclick').includes(hex));
      if (target) target.classList.add('active');

      document.getElementById('picker-color').value = hex;
      document.getElementById('input-hex-color').value = hex;
      applyTypography();
    }

    function onCustomColorPicked(hex) {
      document.getElementById('input-hex-color').value = hex;
      document.querySelectorAll('.palette-pip').forEach(c => c.classList.remove('active'));
      applyTypography();
    }

    function onCustomHexEntered(hex) {
      if (!hex.startsWith('#')) hex = '#' + hex;
      document.getElementById('picker-color').value = hex;
      applyTypography();
    }

    // Align & Line Height
    function setAlign(align) {
      currentAlign = align;
      const group = document.getElementById('btn-group-align');
      group.querySelectorAll('.segmented-btn').forEach(b => b.classList.remove('active'));
      const target = Array.from(group.querySelectorAll('.segmented-btn')).find(b => b.getAttribute('onclick').includes(align));
      if (target) target.classList.add('active');
      document.getElementById('tb-align').innerText = (align === 'center' ? '가운데 정렬' : align === 'left' ? '좌측 정렬' : '우측 정렬') + ' ▾';
      applyTypography();
    }

    function setLineHeight(lh) {
      currentLineHeight = lh;
      const group = document.getElementById('btn-group-lineheight');
      group.querySelectorAll('.segmented-btn').forEach(b => b.classList.remove('active'));
      const target = Array.from(group.querySelectorAll('.segmented-btn')).find(b => b.getAttribute('onclick').includes(lh));
      if (target) target.classList.add('active');
      document.getElementById('tb-lineheight').innerText = lh + ' ▾';
      applyTypography();
    }

    // Presets
    function applyPreset(type) {
      if (type === 'fantasy') {
        document.getElementById('sel-font-family').value = "'Maru Buri', serif";
        document.getElementById('sel-font-size').value = "15pt";
        selectColor('#2c2523');
        setAlign('center');
        setLineHeight('1.8');
      } else if (type === 'minimal') {
        document.getElementById('sel-font-family').value = "'Nanum Barun Gothic', sans-serif";
        document.getElementById('sel-font-size').value = "15pt";
        selectColor('#333333');
        setAlign('left');
        setLineHeight('1.6');
      } else if (type === 'classic') {
        document.getElementById('sel-font-family').value = "'Nanum Myeongjo', serif";
        document.getElementById('sel-font-size').value = "16pt";
        selectColor('#111111');
        setAlign('center');
        setLineHeight('2.0');
      }
    }

    // Load Sample Story
    function loadSampleStory(storyKey) {
      if (storyKey === 'story-weaver') {
        document.getElementById('input-title').value = "침묵의 방직공과 별빛의 매듭";
        document.getElementById('canvas-date').innerText = "DATE: 2026. 10. 19. 09:30";
      } else if (storyKey === 'story-astronomer') {
        document.getElementById('input-title').value = "별을 감정하는 천문관과 가짜 운석";
        document.getElementById('canvas-date').innerText = "DATE: 2026. 10. 15. 09:30";
      } else if (storyKey === 'story-blacksmith') {
        document.getElementById('input-title').value = "맹세를 벼리는 대장간과 구부러진 성검";
        document.getElementById('canvas-date').innerText = "DATE: 2026. 10. 16. 09:30";
      } else if (storyKey === 'story-glassblower') {
        document.getElementById('input-title').value = "한숨을 빚는 유리공과 허공에 뜬 남작";
        document.getElementById('canvas-date').innerText = "DATE: 2026. 10. 17. 09:30";
      }
      runNlpPipeline();
    }

    // Playwright Action Terminal Logging
    function logPlaywrightAction(action, detail) {
      const terminal = document.getElementById('terminal-body');
      const time = new Date().toTimeString().split(' ')[0];
      const div = document.createElement('div');
      div.className = 'log-row';
      div.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-tag-pw">[PLAYWRIGHT]</span>
        <span class="log-text"><strong style="color:var(--accent-spec)">${action}</strong>: ${detail}</span>
      `;
      terminal.appendChild(div);
      terminal.scrollTop = terminal.scrollHeight;
    }

    function clearTerminal() {
      document.getElementById('terminal-body').innerHTML = '';
    }

    // Tab 2: Render Posts
    function renderPostsGrid(posts) {
      const grid = document.getElementById('posts-grid');
      if (posts.length === 0) {
        grid.innerHTML = '<div style="color:var(--text-muted);padding:2.5rem;text-align:center;grid-column:1/-1;font-family:JetBrains Mono,monospace;font-size:12px">// NO_MATCHING_POSTS_FOUND</div>';
        return;
      }
      grid.innerHTML = posts.map(p => `
        <div class="archive-card">
          <div class="arch-card-date">DATE // ${p.date || '2026-10'}</div>
          <div class="arch-card-title">${p.title}</div>
          <div class="arch-card-theme">${p.theme || 'FANTASY_SHORT'}</div>
          <div class="arch-card-tags">
            ${(p.tags || []).map(t => `<span class="arch-tag-chip">${t}</span>`).join('')}
          </div>
          <div class="arch-card-actions">
            <button class="btn-card-open" onclick="loadPostIntoEditor('${encodeURIComponent(p.title)}')">[LOAD INTO EDITOR]</button>
          </div>
        </div>
      `).join('');
    }

    function filterPosts(month, btn) {
      activeFilter = month;
      document.querySelectorAll('.filter-tab-btn').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');

      let filtered = ALL_POSTS;
      if (month !== 'all') {
        filtered = ALL_POSTS.filter(p => (p.date || '').startsWith(month));
      }
      renderPostsGrid(filtered);
    }

    function onSearchPosts(query) {
      query = query.toLowerCase().trim();
      let filtered = ALL_POSTS;
      if (activeFilter !== 'all') {
        filtered = filtered.filter(p => (p.date || '').startsWith(activeFilter));
      }
      if (query) {
        filtered = filtered.filter(p => 
          (p.title || '').toLowerCase().includes(query) ||
          (p.tags || []).some(t => t.toLowerCase().includes(query)) ||
          (p.theme || '').toLowerCase().includes(query)
        );
      }
      renderPostsGrid(filtered);
    }

    function loadPostIntoEditor(encodedTitle) {
      const title = decodeURIComponent(encodedTitle);
      switchTab('sandbox');
      document.getElementById('input-title').value = title;
      runNlpPipeline();
    }

    // Init on Load
    window.addEventListener('DOMContentLoaded', () => {
      runNlpPipeline();
      renderPostsGrid(ALL_POSTS);
    });
  </script>
</body>
</html>
"""

def build():
    # 1. 70편의 포스트 데이터 로드
    posts_path = os.path.join("assets", "posts_data.json")
    with open(posts_path, "r", encoding="utf-8") as f:
        posts = json.load(f)
    
    posts_json_str = json.dumps(posts, ensure_ascii=False)
    html_content = HTML_TEMPLATE.replace("__POSTS_DATA__", posts_json_str)

    # 2. Write index.html to repository root
    root_index_path = "index.html"
    with open(root_index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Generated {root_index_path}")

    # 3. Create docs/ directory and copy index.html & assets into docs/
    docs_dir = "docs"
    os.makedirs(docs_dir, exist_ok=True)
    docs_index_path = os.path.join(docs_dir, "index.html")
    with open(docs_index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Generated {docs_index_path}")

    docs_assets_dir = os.path.join(docs_dir, "assets")
    if os.path.exists(docs_assets_dir):
        shutil.rmtree(docs_assets_dir)
    shutil.copytree("assets", docs_assets_dir)
    print(f"[OK] Copied assets to {docs_assets_dir}")

if __name__ == "__main__":
    build()

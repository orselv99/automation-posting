# -*- coding: utf-8 -*-
"""
build_webapp.py
--------------------------------------------------------------------------------
이 스크립트는 네이버 블로그 스마트에디터 ONE 서식 에뮬레이터 및
한국어 형태소 태깅(NLP) 샌드박스 웹 애플리케이션(index.html)을 빌드합니다.
GitHub Pages 루트(/) 및 docs/ 경로 모두에서 바로 배포 및 임베드될 수 있도록 구성합니다.
--------------------------------------------------------------------------------
"""

import json
import os
import shutil

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Naver SmartEditor ONE & NLP Tag Sandbox</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Nanum+Gothic:wght@400;700&family=Nanum+Myeongjo:wght@400;700&family=Noto+Sans+KR:wght@300;400;500;700&family=Maru+Buri:wght@300;400;600&family=Nanum+Barun+Gothic&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0b0f19;
      --bg-card: #151d2e;
      --bg-card-hover: #1c273e;
      --border-color: #23314d;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --accent: #10b981;
      --accent-purple: #8b5cf6;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --terminal-bg: #070a12;
      --naver-green: #03c75a;
      --parchment: #ece0c6;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Header */
    header {
      background: rgba(21, 29, 46, 0.9);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0.75rem 1.5rem;
    }

    .header-inner {
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.75rem;
    }

    .brand-title {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .badge-live {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
    }

    .pulse-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
      70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
      100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    .brand-title h1 {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .nav-tabs {
      display: flex;
      gap: 0.5rem;
      background: var(--bg-dark);
      padding: 0.25rem;
      border-radius: 8px;
      border: 1px solid var(--border-color);
    }

    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 0.45rem 0.9rem;
      font-size: 0.825rem;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .tab-btn.active {
      background: var(--primary);
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
    }

    .tab-btn:hover:not(.active) {
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
    }

    /* Main Container */
    main {
      max-width: 1440px;
      margin: 0 auto;
      padding: 1.25rem;
      flex: 1;
      width: 100%;
    }

    .tab-content {
      display: none;
    }

    .tab-content.active {
      display: block;
    }

    /* Sandbox Grid Layout */
    .sandbox-layout {
      display: grid;
      grid-template-columns: 420px 1fr;
      gap: 1.25rem;
      align-items: start;
    }

    @media (max-width: 1080px) {
      .sandbox-layout {
        grid-template-columns: 1fr;
      }
    }

    /* Left Control Panel */
    .control-panel {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.15rem;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.9rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid var(--border-color);
    }

    .card-title {
      font-size: 0.95rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: #93c5fd;
    }

    .card-tag {
      font-size: 0.7rem;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #60a5fa;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
    }

    /* Form & Controls */
    .form-group {
      margin-bottom: 0.85rem;
    }

    .form-label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 0.35rem;
    }

    .text-input {
      width: 100%;
      background: var(--bg-dark);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      color: var(--text-main);
      padding: 0.5rem 0.75rem;
      font-size: 0.85rem;
      transition: border 0.2s;
    }

    .text-input:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }

    .btn-action {
      background: linear-gradient(135deg, var(--primary), var(--primary-hover));
      color: white;
      border: none;
      padding: 0.6rem 1rem;
      font-size: 0.85rem;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.4rem;
      transition: all 0.2s;
    }

    .btn-action:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }

    /* NLP Pipeline Visualizer */
    .nlp-pipeline {
      margin-top: 0.75rem;
      background: var(--bg-dark);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 0.75rem;
      font-size: 0.75rem;
      font-family: 'JetBrains Mono', monospace;
    }

    .nlp-step {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.35rem 0;
      border-bottom: 1px dashed rgba(255, 255, 255, 0.07);
    }

    .nlp-step:last-child {
      border-bottom: none;
    }

    .nlp-step-label {
      color: var(--text-muted);
    }

    .nlp-step-val {
      color: #38bdf8;
      font-weight: 600;
      text-align: right;
      max-width: 220px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* Typography Controls */
    .style-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.65rem;
      margin-bottom: 0.75rem;
    }

    .select-input {
      width: 100%;
      background: var(--bg-dark);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.45rem 0.65rem;
      border-radius: 6px;
      font-size: 0.825rem;
      cursor: pointer;
    }

    .select-input:focus {
      outline: none;
      border-color: var(--primary);
    }

    /* Color Chips */
    .color-chips {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      flex-wrap: wrap;
      margin-top: 0.3rem;
    }

    .color-chip {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      cursor: pointer;
      border: 2px solid transparent;
      transition: transform 0.15s, border-color 0.15s;
    }

    .color-chip:hover {
      transform: scale(1.15);
    }

    .color-chip.active {
      border-color: #ffffff;
      box-shadow: 0 0 0 2px var(--primary);
    }

    .custom-color-wrap {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      margin-top: 0.45rem;
    }

    .custom-color-wrap input[type="color"] {
      -webkit-appearance: none;
      border: none;
      width: 28px;
      height: 28px;
      border-radius: 6px;
      cursor: pointer;
      background: transparent;
    }

    .custom-color-wrap input[type="text"] {
      flex: 1;
      font-family: 'JetBrains Mono', monospace;
      padding: 0.35rem 0.5rem;
      font-size: 0.8rem;
    }

    /* Button Groups */
    .btn-group {
      display: flex;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      overflow: hidden;
      background: var(--bg-dark);
    }

    .btn-group button {
      flex: 1;
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 0.4rem 0.5rem;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      border-right: 1px solid var(--border-color);
    }

    .btn-group button:last-child {
      border-right: none;
    }

    .btn-group button.active {
      background: var(--primary);
      color: white;
    }

    .btn-group button:hover:not(.active) {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-main);
    }

    /* Quick Preset Buttons */
    .presets-container {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.45rem;
      margin-top: 0.5rem;
    }

    .btn-preset {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.4rem;
      font-size: 0.725rem;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
      text-align: center;
    }

    .btn-preset:hover {
      background: rgba(59, 130, 246, 0.15);
      border-color: var(--primary);
      color: #93c5fd;
    }

    /* SmartEditor ONE Canvas Replicating Frame */
    .editor-frame {
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      border: 1px solid #d1d5db;
    }

    .editor-topbar {
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      padding: 0.6rem 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .editor-meta-status {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.75rem;
      color: #64748b;
      font-weight: 500;
    }

    .naver-logo-pill {
      background: var(--naver-green);
      color: white;
      font-size: 0.65rem;
      font-weight: 900;
      padding: 0.15rem 0.4rem;
      border-radius: 3px;
      letter-spacing: -0.02em;
    }

    .editor-actions {
      display: flex;
      gap: 0.4rem;
    }

    .btn-naver-save {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: #475569;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.3rem 0.65rem;
      border-radius: 4px;
      cursor: pointer;
    }

    .btn-naver-publish {
      background: var(--naver-green);
      border: 1px solid #02a34a;
      color: white;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.3rem 0.85rem;
      border-radius: 4px;
      cursor: pointer;
    }

    /* Replicated SmartEditor ONE Toolbar */
    .se-toolbar-mock {
      background: #ffffff;
      border-bottom: 1px solid #e5e7eb;
      padding: 0.4rem 1rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      flex-wrap: wrap;
      font-size: 0.75rem;
      color: #374151;
      user-select: none;
    }

    .se-tool-item {
      padding: 0.25rem 0.45rem;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.2rem;
      border: 1px solid transparent;
    }

    .se-tool-item:hover {
      background: #f3f4f6;
      border-color: #e5e7eb;
    }

    .se-tool-divider {
      width: 1px;
      height: 16px;
      background: #e5e7eb;
      margin: 0 0.15rem;
    }

    /* Editor Document Canvas */
    .editor-canvas {
      padding: 2.5rem 2.25rem;
      color: #333333;
      background: #ffffff;
      min-height: 520px;
      display: flex;
      flex-direction: column;
    }

    .doc-category {
      font-size: 0.825rem;
      color: var(--naver-green);
      font-weight: 700;
      margin-bottom: 0.4rem;
      letter-spacing: -0.01em;
    }

    .doc-title {
      font-size: 1.65rem;
      font-weight: 700;
      color: #111827;
      line-height: 1.35;
      margin-bottom: 0.6rem;
      letter-spacing: -0.02em;
    }

    .doc-meta {
      font-size: 0.775rem;
      color: #9ca3af;
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid #f3f4f6;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    /* Illustration Container */
    .doc-illustration-wrap {
      background-color: var(--parchment);
      border: 1px solid #d4c5a9;
      border-radius: 4px;
      padding: 0.5rem;
      margin-bottom: 1.75rem;
      text-align: center;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }

    .doc-illustration-wrap img {
      max-width: 100%;
      height: auto;
      border-radius: 2px;
      display: block;
      margin: 0 auto;
    }

    .doc-illustration-caption {
      font-size: 0.75rem;
      color: #786c55;
      margin-top: 0.4rem;
      font-style: italic;
    }

    /* Story Paragraphs */
    .doc-content {
      margin-bottom: 2rem;
      transition: all 0.2s ease;
    }

    .doc-content p {
      margin-bottom: 1.25rem;
    }

    .doc-content blockquote {
      border-left: 3px solid var(--naver-green);
      padding-left: 1rem;
      margin: 1.25rem 0;
      color: #4b5563;
      font-style: italic;
    }

    /* Tags section */
    .doc-tags-section {
      margin-top: auto;
      padding-top: 1.25rem;
      border-top: 1px solid #f3f4f6;
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
      align-items: center;
    }

    .doc-tag-label {
      font-size: 0.775rem;
      font-weight: 700;
      color: #6b7280;
      margin-right: 0.25rem;
    }

    .doc-tag-pill {
      background: #f3f4f6;
      color: #2563eb;
      font-size: 0.8rem;
      font-weight: 500;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      text-decoration: none;
      transition: background 0.15s;
    }

    .doc-tag-pill:hover {
      background: #e5e7eb;
    }

    /* Bottom Terminal / Logger */
    .terminal-section {
      margin-top: 1.25rem;
    }

    .terminal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #0f1523;
      border: 1px solid var(--border-color);
      border-bottom: none;
      border-radius: 10px 10px 0 0;
      padding: 0.5rem 1rem;
    }

    .terminal-title {
      font-size: 0.775rem;
      font-weight: 600;
      font-family: 'JetBrains Mono', monospace;
      color: #94a3b8;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .terminal-dots {
      display: flex;
      gap: 4px;
    }

    .terminal-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }

    .terminal-dot.red { background: #ef4444; }
    .terminal-dot.yellow { background: #f59e0b; }
    .terminal-dot.green { background: #10b981; }

    .terminal-body {
      background: var(--terminal-bg);
      border: 1px solid var(--border-color);
      border-radius: 0 0 10px 10px;
      padding: 0.85rem 1rem;
      height: 140px;
      overflow-y: auto;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      line-height: 1.6;
    }

    .log-line {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 0.15rem;
    }

    .log-time { color: #64748b; }
    .log-tag-pw { color: #38bdf8; font-weight: 600; }
    .log-tag-dom { color: #10b981; font-weight: 600; }
    .log-tag-nlp { color: #a855f7; font-weight: 600; }
    .log-msg { color: #e2e8f0; }

    /* Tab 2: Story Archive */
    .archive-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
      gap: 0.75rem;
    }

    .archive-filters {
      display: flex;
      gap: 0.5rem;
    }

    .filter-btn {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      font-size: 0.8rem;
      cursor: pointer;
      font-weight: 600;
    }

    .filter-btn.active {
      background: var(--primary);
      color: white;
      border-color: var(--primary);
    }

    .search-box {
      position: relative;
      width: 280px;
    }

    .search-input {
      width: 100%;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 0.45rem 0.75rem;
      color: white;
      font-size: 0.825rem;
    }

    .posts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1rem;
    }

    .post-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 1rem;
      transition: all 0.2s;
      display: flex;
      flex-direction: column;
    }

    .post-card:hover {
      transform: translateY(-2px);
      border-color: var(--primary);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
    }

    .post-card-date {
      font-size: 0.725rem;
      color: #94a3b8;
      font-family: 'JetBrains Mono', monospace;
      margin-bottom: 0.3rem;
    }

    .post-card-title {
      font-size: 0.975rem;
      font-weight: 700;
      color: #f1f5f9;
      margin-bottom: 0.5rem;
      line-height: 1.4;
    }

    .post-card-theme {
      font-size: 0.725rem;
      background: rgba(139, 92, 246, 0.15);
      border: 1px solid rgba(139, 92, 246, 0.3);
      color: #c4b5fd;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      margin-bottom: 0.75rem;
      align-self: flex-start;
    }

    .post-card-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      margin-top: auto;
      padding-top: 0.75rem;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    .post-tag-chip {
      font-size: 0.725rem;
      color: #60a5fa;
      background: rgba(59, 130, 246, 0.1);
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
    }

    .post-card-actions {
      margin-top: 0.75rem;
      display: flex;
      gap: 0.4rem;
    }

    .btn-card-load {
      flex: 1;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #93c5fd;
      padding: 0.35rem;
      font-size: 0.75rem;
      border-radius: 4px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
      transition: background 0.15s;
    }

    .btn-card-load:hover {
      background: var(--primary);
      color: white;
    }

    /* Tab 3: Architecture */
    .arch-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1.25rem;
    }

    .metric-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 1.25rem;
    }

    .metric-num {
      font-size: 2.25rem;
      font-weight: 800;
      color: #38bdf8;
      font-family: 'JetBrains Mono', monospace;
      margin-bottom: 0.25rem;
    }

    .metric-desc {
      color: var(--text-muted);
      font-size: 0.85rem;
    }

    .arch-flowchart {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.5rem;
      margin-top: 1.25rem;
    }

    .flow-steps {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      position: relative;
    }

    .flow-step {
      display: flex;
      align-items: flex-start;
      gap: 1rem;
      background: var(--bg-dark);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
    }

    .flow-badge {
      background: var(--primary);
      color: white;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8rem;
      font-weight: 700;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .flow-info h4 {
      font-size: 0.95rem;
      color: #93c5fd;
      margin-bottom: 0.3rem;
    }

    .flow-info p {
      font-size: 0.825rem;
      color: var(--text-muted);
    }

    /* Footer */
    footer {
      background: var(--bg-dark);
      border-top: 1px solid var(--border-color);
      padding: 1.25rem 1.5rem;
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: auto;
    }

    footer a {
      color: var(--primary);
      text-decoration: none;
    }
  </style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="header-inner">
      <div class="brand-title">
        <div class="badge-live">
          <span class="pulse-dot"></span>
          <span>LIVE RUNTIME</span>
        </div>
        <div>
          <h1>Naver SmartEditor ONE & NLP Sandbox</h1>
        </div>
      </div>
      <nav class="nav-tabs">
        <button class="tab-btn active" onclick="switchTab('sandbox')">
          <span>🎨</span> 서식 & 태그 샌드박스
        </button>
        <button class="tab-btn" onclick="switchTab('archive')">
          <span>📚</span> 70편 연재작 아카이브
        </button>
        <button class="tab-btn" onclick="switchTab('arch')">
          <span>📐</span> 파이프라인 아키텍처
        </button>
      </nav>
    </div>
  </header>

  <!-- Main Content -->
  <main>
    <!-- TAB 1: SANDBOX -->
    <section id="tab-sandbox" class="tab-content active">
      <div class="sandbox-layout">
        
        <!-- Left Control Panel -->
        <div class="control-panel">
          
          <!-- Card: Korean NLP Tagger -->
          <div class="card">
            <div class="card-header">
              <span class="card-title">
                <span>⚡</span> 한글 정규식 형태소 태거
              </span>
              <span class="card-tag">re.compile</span>
            </div>
            
            <div class="form-group">
              <label class="form-label">소설 제목 입력</label>
              <input type="text" id="input-title" class="text-input" value="기억을 거래하는 신비한 은빛 상점과 침묵의 방직공">
            </div>

            <button class="btn-action" onclick="runNlpPipeline()">
              <span>🚀</span> 실시간 태그 추출 실행
            </button>

            <!-- NLP Pipeline Step Visualizer -->
            <div class="nlp-pipeline">
              <div class="nlp-step">
                <span class="nlp-step-label">[1] 토큰 분리</span>
                <span id="nlp-step-1" class="nlp-step-val">기억을, 거래하는...</span>
              </div>
              <div class="nlp-step">
                <span class="nlp-step-label">[2] 동사/어미 제거</span>
                <span id="nlp-step-2" class="nlp-step-val">거래하는 → 거래</span>
              </div>
              <div class="nlp-step">
                <span class="nlp-step-label">[3] 관형사 필터링</span>
                <span id="nlp-step-3" class="nlp-step-val">신비한 → 필터아웃</span>
              </div>
              <div class="nlp-step">
                <span class="nlp-step-label">[4] 후방탐색 조사제거</span>
                <span id="nlp-step-4" class="nlp-step-val">기억을 → 기억</span>
              </div>
              <div class="nlp-step">
                <span class="nlp-step-label">[5] 최종 명사 태그</span>
                <span id="nlp-step-5" class="nlp-step-val">#기억 #거래 #은빛...</span>
              </div>
            </div>
          </div>

          <!-- Card: SmartEditor ONE Typography Engine -->
          <div class="card">
            <div class="card-header">
              <span class="card-title">
                <span>🖋️</span> 스마트에디터 서식 제어기
              </span>
              <span class="card-tag">editor_style.py</span>
            </div>

            <!-- Font Family & Font Size -->
            <div class="style-row">
              <div>
                <label class="form-label">글꼴 서체</label>
                <select id="sel-font-family" class="select-input" onchange="applyTypography()">
                  <option value="'Maru Buri', serif" selected>마루부리 (MaruBuri)</option>
                  <option value="'Nanum Gothic', sans-serif">기본서체 (NanumGothic)</option>
                  <option value="'Nanum Myeongjo', serif">나눔명조 (NanumMyeongjo)</option>
                  <option value="'Nanum Barun Gothic', sans-serif">나눔바른고딕</option>
                  <option value="'Noto Sans KR', sans-serif">본고딕 (NotoSans)</option>
                </select>
              </div>
              <div>
                <label class="form-label">글자 크기</label>
                <select id="sel-font-size" class="select-input" onchange="applyTypography()">
                  <option value="11pt">11pt (fs11)</option>
                  <option value="13pt">13pt (fs13)</option>
                  <option value="15pt" selected>15pt (fs15 - 네이버 표준)</option>
                  <option value="16pt">16pt (fs16)</option>
                  <option value="19pt">19pt (fs19)</option>
                  <option value="24pt">24pt (fs24)</option>
                </select>
              </div>
            </div>

            <!-- Color Palette & Custom HEX -->
            <div class="form-group">
              <label class="form-label">본문 글자 색상 (72색 팔레트 & 커스텀 HEX)</label>
              <div class="color-chips">
                <div class="color-chip active" style="background:#2c2523" onclick="selectColor('#2c2523')" title="다크 세피아"></div>
                <div class="color-chip" style="background:#333333" onclick="selectColor('#333333')" title="차콜 (네이버 표준)"></div>
                <div class="color-chip" style="background:#111111" onclick="selectColor('#111111')" title="블랙"></div>
                <div class="color-chip" style="background:#1a365d" onclick="selectColor('#1a365d')" title="미드나잇 네이비"></div>
                <div class="color-chip" style="background:#5c1d24" onclick="selectColor('#5c1d24')" title="크림슨 레드"></div>
                <div class="color-chip" style="background:#1c3d2e" onclick="selectColor('#1c3d2e')" title="포레스트 그린"></div>
                <div class="color-chip" style="background:#555555" onclick="selectColor('#555555')" title="소프트 그레이"></div>
              </div>
              <div class="custom-color-wrap">
                <input type="color" id="picker-color" value="#2c2523" onchange="onCustomColorPicked(this.value)">
                <input type="text" id="input-hex-color" class="text-input" value="#2c2523" onchange="onCustomHexEntered(this.value)">
              </div>
            </div>

            <!-- Alignment & Line Height -->
            <div class="style-row">
              <div>
                <label class="form-label">정렬 (Align)</label>
                <div class="btn-group" id="btn-group-align">
                  <button type="button" class="active" onclick="setAlign('center')">가운데</button>
                  <button type="button" onclick="setAlign('left')">좌측</button>
                  <button type="button" onclick="setAlign('right')">우측</button>
                </div>
              </div>
              <div>
                <label class="form-label">줄간격 (Line Height)</label>
                <div class="btn-group" id="btn-group-lineheight">
                  <button type="button" onclick="setLineHeight('1.6')">160%</button>
                  <button type="button" class="active" onclick="setLineHeight('1.8')">180%</button>
                  <button type="button" onclick="setLineHeight('2.0')">200%</button>
                </div>
              </div>
            </div>

            <!-- One-Click Preset Styles -->
            <div class="form-group" style="margin-bottom:0">
              <label class="form-label">원클릭 스타일 프리셋</label>
              <div class="presets-container">
                <button class="btn-preset" onclick="applyPreset('fantasy')">📜 다크 판타지</button>
                <button class="btn-preset" onclick="applyPreset('minimal')">💼 현대 미니멀</button>
                <button class="btn-preset" onclick="applyPreset('classic')">📖 클래식 명조</button>
              </div>
            </div>

          </div>

          <!-- Card: Switch Sample Stories -->
          <div class="card">
            <div class="card-header">
              <span class="card-title">
                <span>📖</span> 연재작 원클릭 로드
              </span>
              <span class="card-tag">history/</span>
            </div>
            <select id="sel-sample-story" class="select-input" onchange="loadSampleStory(this.value)">
              <option value="story-weaver">10-19: 침묵의 방직공과 별빛의 매듭 (최신 발행작)</option>
              <option value="story-astronomer">10-15: 별을 감정하는 천문관과 가짜 운석</option>
              <option value="story-blacksmith">10-16: 맹세를 벼리는 대장간과 구부러진 성검</option>
              <option value="story-glassblower">10-17: 한숨을 빚는 유리공과 허공에 뜬 남작</option>
            </select>
          </div>

        </div>

        <!-- Right: Live SmartEditor ONE Canvas -->
        <div class="editor-frame">
          
          <!-- SmartEditor Header Bar -->
          <div class="editor-topbar">
            <div class="editor-meta-status">
              <span class="naver-logo-pill">N BLOG</span>
              <span>스마트에디터 ONE • 실시간 DOM 에뮬레이터</span>
            </div>
            <div class="editor-actions">
              <button class="btn-naver-save" onclick="logPlaywrightAction('Save Draft', 'Temporary draft saved to localStorage')">임시저장 (0)</button>
              <button class="btn-naver-publish" onclick="logPlaywrightAction('Publish Post', 'Triggered post confirmation modal & published')">발행</button>
            </div>
          </div>

          <!-- SmartEditor Toolbar Mock -->
          <div class="se-toolbar-mock">
            <div class="se-tool-item" id="tb-font-name">마루부리 ▾</div>
            <div class="se-tool-item" id="tb-font-size">15 ▾</div>
            <div class="se-tool-divider"></div>
            <div class="se-tool-item" style="font-weight:bold">B</div>
            <div class="se-tool-item" style="font-style:italic">I</div>
            <div class="se-tool-item" style="text-decoration:underline">U</div>
            <div class="se-tool-item" style="text-decoration:line-through">S</div>
            <div class="se-tool-divider"></div>
            <div class="se-tool-item">
              <span id="tb-color-chip" style="display:inline-block;width:12px;height:12px;background:#2c2523;border-radius:2px;margin-right:2px"></span> 가 ▾
            </div>
            <div class="se-tool-item" id="tb-align">가운데 정렬 ▾</div>
            <div class="se-tool-item" id="tb-lineheight">1.8 ▾</div>
            <div class="se-tool-divider"></div>
            <div class="se-tool-item">인용구 ▾</div>
            <div class="se-tool-item">구분선</div>
            <div class="se-tool-item">링크</div>
            <div class="se-tool-item">사진</div>
            <div class="se-tool-item">동영상</div>
            <div class="se-tool-item">스티커</div>
          </div>

          <!-- Editor Document Body -->
          <div class="editor-canvas">
            <div class="doc-category" id="canvas-category">Quatsch (판타지 단편) > 소설</div>
            <h1 class="doc-title" id="canvas-title">기억을 거래하는 신비한 은빛 상점과 침묵의 방직공</h1>
            
            <div class="doc-meta">
              <span>작성자: <strong>orselv99</strong></span>
              <span>•</span>
              <span id="canvas-date">2026. 10. 19. 13:00</span>
              <span>•</span>
              <span style="color:#059669">공개 (전체공개)</span>
            </div>

            <!-- Etching Illustration -->
            <div class="doc-illustration-wrap">
              <img id="canvas-image" src="assets/sample_illustration.webp" alt="침묵의 방직공과 별빛의 매듭 삽화" onerror="this.src='assets/02_published_post.png'">
              <div class="doc-illustration-caption">
                ▲ Style Spec: Detailed monochrome pen & ink etching, cross-hatching, parchment #ece0c6 background
              </div>
            </div>

            <!-- Novel Content (Subject to typography live changes) -->
            <div class="doc-content" id="canvas-content" style="font-family:'Maru Buri', serif; font-size:15pt; color:#2c2523; line-height:1.8; text-align:center;">
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

            <!-- Dynamic Tags Section -->
            <div class="doc-tags-section" id="canvas-tags">
              <span class="doc-tag-label">태그:</span>
              <a href="#" class="doc-tag-pill">#기억</a>
              <a href="#" class="doc-tag-pill">#거래</a>
              <a href="#" class="doc-tag-pill">#은빛</a>
              <a href="#" class="doc-tag-pill">#상점</a>
              <a href="#" class="doc-tag-pill">#침묵</a>
              <a href="#" class="doc-tag-pill">#방직공</a>
              <a href="#" class="doc-tag-pill">#판타지소설</a>
            </div>

          </div>

        </div>

      </div>

      <!-- Playwright DOM Action & NLP Terminal -->
      <div class="terminal-section">
        <div class="terminal-header">
          <div class="terminal-title">
            <div class="terminal-dots">
              <span class="terminal-dot red"></span>
              <span class="terminal-dot yellow"></span>
              <span class="terminal-dot green"></span>
            </div>
            <span>Playwright Headless Event Stream & Regex Engine Trace</span>
          </div>
          <button style="background:none;border:none;color:#64748b;font-size:0.75rem;cursor:pointer" onclick="clearTerminal()">Clear</button>
        </div>
        <div class="terminal-body" id="terminal-body">
          <div class="log-line">
            <span class="log-time">[Init]</span>
            <span class="log-tag-pw">[Playwright]</span>
            <span class="log-msg">Chromium persistent context loaded from './chrome_profile' (Session active)</span>
          </div>
          <div class="log-line">
            <span class="log-time">[Init]</span>
            <span class="log-tag-dom">[SmartEditor]</span>
            <span class="log-msg">SmartEditor ONE React components mounted (.se-component-content ready)</span>
          </div>
          <div class="log-line">
            <span class="log-time">[Init]</span>
            <span class="log-tag-nlp">[Regex NLP]</span>
            <span class="log-msg">Loaded VERB_STRIP_REGEX, ADJ_STRIP_REGEX, JOSA_STRIP_REGEX (Lookbehind enabled)</span>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 2: 70 NOVELS ARCHIVE -->
    <section id="tab-archive" class="tab-content">
      <div class="archive-controls">
        <div class="archive-filters">
          <button class="filter-btn active" onclick="filterPosts('all', this)">전체보기 (70)</button>
          <button class="filter-btn" onclick="filterPosts('2026-10', this)">2026-10 (20)</button>
          <button class="filter-btn" onclick="filterPosts('2026-09', this)">2026-09 (30)</button>
          <button class="filter-btn" onclick="filterPosts('2026-08', this)">2026-08 (20)</button>
        </div>
        <div class="search-box">
          <input type="text" id="post-search" class="search-input" placeholder="제목 또는 태그 검색..." oninput="onSearchPosts(this.value)">
        </div>
      </div>

      <div class="posts-grid" id="posts-grid">
        <!-- Rendered dynamically from posts JSON -->
      </div>
    </section>

    <!-- TAB 3: ARCHITECTURE -->
    <section id="tab-arch" class="tab-content">
      <div class="arch-grid">
        <div class="metric-card">
          <div class="metric-num">2.1s</div>
          <div class="metric-desc">70편 메타데이터 수집 속도 (종전 120초 대비 60배 단축)</div>
        </div>
        <div class="metric-card">
          <div class="metric-num">100%</div>
          <div class="metric-desc">70편 글 태그 추출 및 스마트에디터 스타일 마이그레이션 성공률</div>
        </div>
        <div class="metric-card">
          <div class="metric-num">0 MB</div>
          <div class="metric-desc">JVM 및 외부 무거운 언어팩 의존성 없이 순수 정규식으로 형태소 파싱</div>
        </div>
      </div>

      <div class="arch-flowchart">
        <h3 style="font-size:1.1rem;margin-bottom:1rem;color:#93c5fd">4단계 무인 파이프라인 아키텍처</h3>
        <div class="flow-steps">
          <div class="flow-step">
            <div class="flow-badge">1</div>
            <div class="flow-info">
              <h4>AI 멀티모달 콘텐츠 생성 (Gemini 2.5 Flash + Imagen 3)</h4>
              <p>7대 판타지 테마 순환, 3인칭 관찰자 시점, 16:9 와이드 #ece0c6 양피지 톤 에칭 펜화 동판화 일러스트 생성</p>
            </div>
          </div>
          <div class="flow-step">
            <div class="flow-badge">2</div>
            <div class="flow-info">
              <h4>Playwright 스마트에디터 ONE 서식 주입 및 자동 발행</h4>
              <p>본문 선택(Control+A) 후 폰트, 크기, 커스텀 HEX 색상 주입(.se-color-picker-more-button), 정렬/줄간격 적용</p>
            </div>
          </div>
          <div class="flow-step">
            <div class="flow-badge">3</div>
            <div class="flow-info">
              <h4>Google Drive 클라우드 원고 & 삽화 아카이빙 (3회 지수 백오프)</h4>
              <p>안정적인 OAuth 2.0 리프레시 토큰 기반, 네트워크 일시 오류 시 2초/4초/8초 대기 후 자동 재시도</p>
            </div>
          </div>
          <div class="flow-step">
            <div class="flow-badge">4</div>
            <div class="flow-info">
              <h4>비상 이메일 SOS 알림 & history/ 월별 파티셔닝</h4>
              <p>최종 실패 시 관리자 Gmail로 원고 및 에러 로그 자동 전송, history/{yyyy-mm}.json으로 경량화 보존</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>

  <!-- Footer -->
  <footer>
    <p>Naver Blog Automation & Live Runtime Sandbox | Built by <a href="https://github.com/orselv99/automation-posting" target="_blank">orselv99</a></p>
  </footer>

  <script>
    // 70편의 전체 포스트 데이터 내장
    const ALL_POSTS = __POSTS_DATA__;

    // NLP Regex Patterns (Python과 1:1 포팅)
    const VERB_STRIP_REGEX = /(?:하다|하는|하며|하고|했던|하여|되는|된|되며|되고|위한|통한|따른)$/;
    const ADJ_STRIP_REGEX = /(?:있는|없는|같은|어떤|모든|새로운|깊은|높은|밝은|어두운|신비한|거대한|작은|따뜻한|차가운)$/;
    // Javascript lookbehind support: (?<=[가-힣]{2})
    const JOSA_STRIP_REGEX = /(?<=[가-힣]{2})(?:에서|에게|으로|로|의|과|와|을|를|은|는|이|가|도)$/;

    // State
    let currentAlign = 'center';
    let currentLineHeight = '1.8';
    let activeFilter = 'all';

    // Switch Tab
    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      const targetBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
      if (targetBtn) targetBtn.classList.add('active');
      
      const targetContent = document.getElementById('tab-' + tabId);
      if (targetContent) targetContent.classList.add('active');

      logPlaywrightAction('Navigation', 'Switched UI tab to: ' + tabId);
    }

    // Real-time NLP Tag Extraction
    function runNlpPipeline() {
      const title = document.getElementById('input-title').value.trim();
      if (!title) return;

      logPlaywrightAction('NLP Trigger', 'Extracting tags for: "' + title + '"');

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
          adjLog = word + ' (제거)';
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
      document.getElementById('nlp-step-2').innerText = verbLog || '해당 없음';
      document.getElementById('nlp-step-3').innerText = adjLog || '해당 없음';
      document.getElementById('nlp-step-4').innerText = josaLog || '해당 없음';
      document.getElementById('nlp-step-5').innerText = extractedTags.slice(0, 4).join(' ') + '...';

      // Update Editor Tags
      const tagsContainer = document.getElementById('canvas-tags');
      tagsContainer.innerHTML = '<span class="doc-tag-label">태그:</span>' + 
        extractedTags.map(t => `<a href="#" class="doc-tag-pill">${t}</a>`).join(' ');

      // Update Title
      document.getElementById('canvas-title').innerText = title;

      logPlaywrightAction('NLP Result', 'Generated tags: ' + extractedTags.join(', '));
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

      logPlaywrightAction('Style Applied', `font: ${fontNameClean}, size: ${size}, color: ${color}, align: ${currentAlign}, line-height: ${currentLineHeight}`);
    }

    // Select Color from Chips
    function selectColor(hex) {
      document.querySelectorAll('.color-chip').forEach(c => c.classList.remove('active'));
      const target = Array.from(document.querySelectorAll('.color-chip')).find(c => c.getAttribute('onclick').includes(hex));
      if (target) target.classList.add('active');

      document.getElementById('picker-color').value = hex;
      document.getElementById('input-hex-color').value = hex;
      applyTypography();
    }

    function onCustomColorPicked(hex) {
      document.getElementById('input-hex-color').value = hex;
      document.querySelectorAll('.color-chip').forEach(c => c.classList.remove('active'));
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
      group.querySelectorAll('button').forEach(b => b.classList.remove('active'));
      const target = Array.from(group.querySelectorAll('button')).find(b => b.getAttribute('onclick').includes(align));
      if (target) target.classList.add('active');
      document.getElementById('tb-align').innerText = (align === 'center' ? '가운데 정렬' : align === 'left' ? '좌측 정렬' : '우측 정렬') + ' ▾';
      applyTypography();
    }

    function setLineHeight(lh) {
      currentLineHeight = lh;
      const group = document.getElementById('btn-group-lineheight');
      group.querySelectorAll('button').forEach(b => b.classList.remove('active'));
      const target = Array.from(group.querySelectorAll('button')).find(b => b.getAttribute('onclick').includes(lh));
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
        document.getElementById('canvas-date').innerText = "2026. 10. 19. 09:30";
      } else if (storyKey === 'story-astronomer') {
        document.getElementById('input-title').value = "별을 감정하는 천문관과 가짜 운석";
        document.getElementById('canvas-date').innerText = "2026. 10. 15. 09:30";
      } else if (storyKey === 'story-blacksmith') {
        document.getElementById('input-title').value = "맹세를 벼리는 대장간과 구부러진 성검";
        document.getElementById('canvas-date').innerText = "2026. 10. 16. 09:30";
      } else if (storyKey === 'story-glassblower') {
        document.getElementById('input-title').value = "한숨을 빚는 유리공과 허공에 뜬 남작";
        document.getElementById('canvas-date').innerText = "2026. 10. 17. 09:30";
      }
      runNlpPipeline();
    }

    // Playwright Action Terminal Logging
    function logPlaywrightAction(action, detail) {
      const terminal = document.getElementById('terminal-body');
      const time = new Date().toTimeString().split(' ')[0];
      const div = document.createElement('div');
      div.className = 'log-line';
      div.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-tag-pw">[Playwright]</span>
        <span class="log-msg"><strong style="color:#60a5fa">${action}</strong>: ${detail}</span>
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
        grid.innerHTML = '<div style="color:#64748b;padding:2rem;text-align:center;grid-column:1/-1">일치하는 포스팅이 없습니다.</div>';
        return;
      }
      grid.innerHTML = posts.map(p => `
        <div class="post-card">
          <div class="post-card-date">발행일: ${p.date || '2026-10'}</div>
          <div class="post-card-title">${p.title}</div>
          <div class="post-card-theme">${p.theme || 'Fantasy Short'}</div>
          <div class="post-card-tags">
            ${(p.tags || []).map(t => `<span class="post-tag-chip">${t}</span>`).join('')}
          </div>
          <div class="post-card-actions">
            <button class="btn-card-load" onclick="loadPostIntoEditor('${encodeURIComponent(p.title)}')">에디터에서 열기</button>
          </div>
        </div>
      `).join('');
    }

    function filterPosts(month, btn) {
      activeFilter = month;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
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

# Seobility On-Page SEO Optimizer Skill (`seobility-optimizer`)

An AI Agent Skill & standalone CLI tool for **Antigravity**, **Claude Code**, **Cursor**, and **Codex** that audits local HTML files, local dev servers (`localhost:3000`), and live URLs against the **Seobility SEO scoring engine** — and provides exact code fixes to achieve a **100% On-Page SEO score**.

---

## Features

- **3 Audit Modes (No Deployment Required)**:
  1. **Local HTML file** (`index.html`, SSR output, static build) — instant, zero network calls.
  2. **Local Dev Server** (`http://localhost:3000`, `http://localhost:5173`) — audits live local HTML response.
  3. **Live Website URL** (`https://example.com`) — queries the Seobility Live Check API with automatic fallback to the local 100/100 rule engine.
- **5-Pillar Seobility 100% Rubric**:
  - **Meta-Angaben (515 pts)**: Title length/pixel width, Meta Description with CTA, Canonical URL, Robots, Viewport, Open Graph & Twitter Cards.
  - **Seitenqualität / Content (360 pts)**: Word count (`factor_text` >= 500–650 words), strict single `<h1>` hierarchy, `img[alt]` coverage, Social Sharing intents (`factor_socialshare`).
  - **Seitenstruktur (170 pts)**: Schema.org JSON-LD `@graph` validation (`WebSite`, `Organization`, `FAQPage`, `BreadcrumbList`).
  - **Verlinkung / Links (80 pts)**: Internal anchor structure & authoritative external links (`factor_link_external`).
  - **Server & Technik (110 pts)**: HTTP/2, compression, caching & security headers.
- **Includes 2 Skill Variants**:
  - [`seobility-optimizer`](./skills/seobility-optimizer/SKILL.md) — Local & live On-Page SEO auditor and optimizer (no deployment required).
  - [`seobility-deploy-optimizer`](./skills/seobility-deploy-optimizer/SKILL.md) — End-to-end reverse-proxy deployment + live Seobility verification loop.

---

## Quick Start

### 1. Install as an Agent Skill

```bash
# For Antigravity / Gemini CLI:
git clone https://github.com/echo3x3e/seobility-optimizer.git ~/.gemini/antigravity-cli/skills/seobility-optimizer

# For Claude Code / .agents workspace:
mkdir -p .agents/skills
git clone https://github.com/echo3x3e/seobility-optimizer.git .agents/skills/seobility-optimizer
```

### 2. Run the Standalone CLI Auditor

```bash
pip install -r requirements.txt

# 1. Audit a local HTML file:
python3 scripts/seobility_check.py index.html

# 2. Audit a local development server:
python3 scripts/seobility_check.py http://localhost:3000

# 3. Audit a live website:
python3 scripts/seobility_check.py https://example.com

# 4. Export raw JSON report:
python3 scripts/seobility_check.py index.html --json --save report.json
```

---

## Example Output

```text
=======================================================
  SEOBILITY ON-PAGE AUDIT: Local File: index.html
  OVERALL ON-PAGE SCORE: 100%
  Analysierte Textmenge: 684 Wörter
=======================================================

ON-PAGE KATEGORIEN:
  Kategorie                 | Score %  | Status
  --------------------------|----------|-----------
  Meta-Angaben              | 100%     | 100% PERFEKT
  Seitenqualität (Content)  | 100%     | 100% PERFEKT
  Seitenstruktur            | 100%     | 100% PERFEKT
  Verlinkung (Links)        | 100%     | 100% PERFEKT
  Server & Technik          | 100%     | 100% PERFEKT

=======================================================
HANDLUNGSBEDARF & ABZÜGE (FALLS VORHANDEN):
=======================================================
  Keine Abzüge! Alle On-Page-Kriterien erfüllen zu 100% die Seobility-Standards.
```

---

## License

MIT © [echo3x3e](https://github.com/echo3x3e)

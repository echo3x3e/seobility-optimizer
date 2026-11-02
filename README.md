# Seobility & Google PageSpeed Insights SEO Optimizer Skill (`seobility-optimizer`)

An AI Agent Skill & standalone CLI tool for **Antigravity**, **Claude Code**, **Cursor**, and **Codex** that audits local HTML files, local dev servers (`localhost:3000`), and live URLs against **both** the **Seobility SEO scoring engine** and **Google PageSpeed Insights (Lighthouse v5 API + Core Web Vitals)** — providing exact code fixes to achieve **100% On-Page SEO & Lighthouse scores**.

---

## Features

- **Dual Engine Audit (Seobility + Google PageSpeed Insights)**:
  - **Seobility 5-Pillar Rubric**: Meta-Angaben (515 pts), Seitenqualität/Content (360 pts), Seitenstruktur/JSON-LD (170 pts), Verlinkung (80 pts), Server & Technik (110 pts).
  - **Google PageSpeed Insights v5 API & Lighthouse**: Performance, Accessibility, Best Practices, SEO (0–100%) + Core Web Vitals (**LCP**, **FCP**, **TBT/INP**, **CLS**, **Speed Index**, **TTFB**) for both **Mobile** and **Desktop**.
  - **Zero-Deployment Local Mode**: Audits local `.html` files and `localhost` dev servers with instant static Seobility + Core Web Vitals heuristics (detecting render-blocking scripts, unsized images/CLS risks, missing `fetchpriority`, missing `display=swap`, and Lighthouse A11y issues).

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

# 1. Audit a local HTML file (Seobility + Core Web Vitals static check):
python3 scripts/seobility_check.py index.html

# 2. Audit a local development server:
python3 scripts/seobility_check.py http://localhost:3000

# 3. Audit a live website (Seobility API + Google PageSpeed Insights API for Mobile & Desktop):
python3 scripts/seobility_check.py https://example.com --strategy both

# 4. Optional: Pass a Google PageSpeed API Key (or set PAGESPEED_API_KEY env var):
python3 scripts/seobility_check.py https://example.com --strategy both --psi-key YOUR_API_KEY

# 5. Export combined Seobility + PageSpeed JSON report:
python3 scripts/seobility_check.py index.html --json --save report.json
```

---

## License

MIT © [echo3x3e](https://github.com/echo3x3e)

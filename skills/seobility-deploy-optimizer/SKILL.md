---
name: seobility-deploy-optimizer
description: Automates production deployments behind reverse proxies (Nginx Proxy Manager, Docker, PM2) and executes comprehensive live audits against the Seobility SEO engine. Diagnoses deductions across Meta, Page Quality, Structure, Internal/External Links, and Server pillars, applies 100% on-page compliance fixes, and re-verifies in an automated feedback loop.
---

# Seobility Deploy & SEO Optimizer

## Overview

This skill automates the complete cycle of **safe proxy-based production deployment** and **live Seobility SEO scoring to reach 100% on-page performance**. It provides the tooling, diagnosis heuristics, and exact technical patterns needed to deploy web applications sitting behind reverse proxies (such as Nginx Proxy Manager, Cloudflare, Traefik, or OpenResty) and audit them directly against Seobility's live engine.

## When to Use

- Deploying code updates to remote production environments via SSH/SCP and reverse proxy.
- Auditing web pages against Seobility (`seobility.net`) to detect ranking and crawlability issues.
- Aiming for **100% scores** in Seobility's on-page pillars: Meta-Angaben, Seitenqualität, Seitenstruktur, Verlinkung, and Server.
- Diagnosing Seobility warnings like `text_short`, `link_external_none`, `socialshare_no_plugin`, `title_toolong`, or missing schema.
- Iterative review-and-fix deployment loops ("deploy via proxy and verify on Seobility").

---

## Architecture & Deployment Workflow

```
[Local Workspace]
  ├── 1. Pre-Flight: tsc --noEmit check
  ├── 2. Package: tar -czf (excluding heavy dirs: android/, node_modules/)
  └── 3. SCP: Transfer to Remote Host
           │
           ▼
[Remote Host (e.g. 192.168.1.7)]
  ├── 4. Unpack to target directory (/home/service/...)
  ├── 5. Frontend Build (Vite/Rollup -> dist/)
  ├── 6. Backend Sync & DB Seeders (MongoDB/PostgreSQL)
  └── 7. PM2 Zero-Downtime Reload
           │
           ▼
[Reverse Proxy (Nginx Proxy Manager / Docker)]
  ├── 8. Port 80/443 SSL (Let's Encrypt / HTTP/2) -> Backend Port (3005)
           │
           ▼
[Live Site & Seobility Live Engine]
  ├── 9. HTTP/2 Health check (curl -sI https://domain.com)
  └── 10. Seobility Live Audit (python3 scripts/seobility_check.py https://domain.com)
```

---

## 1. Safe Proxy-Aware Deployment Protocol

When running deployments through `deploy.sh` or similar bash routines:

1. **Non-Interactive Execution:**
   - Ensure deployment scripts fail fast (`set -e`) without interactive prompts (avoid `read -p` which hangs non-interactive agent sessions).
2. **Exclude Heavy Non-Production Directories:**
   - Always exclude mobile native folders (`--exclude=android`, `--exclude=ios`), `.git`, test videos, and local build artifacts to keep upload packages fast (< 20MB vs > 200MB).
3. **Remote ext4 Build:**
   - On hosts with restricted local filesystems (e.g. NTFS mounts mounted `noexec`), execute frontend build (`npm run build`) remotely on the destination server's native filesystem.
4. **PM2 Zero-Downtime Reload:**
   - Use `pm2 restart <service-name>` or `pm2 reload <service-name>` and capture PID to confirm process stability.
5. **Proxy Health Verification:**
   - Always run `curl -sI https://<domain>/` after restart to confirm `HTTP/2 200` through the proxy before triggering SEO audits.

---

## 2. The Seobility 100/100 On-Page Rubric

Seobility evaluates on-page performance across five strict core pillars:

### Pillar 1: Meta-Angaben (515 Points — 100%)
- **Meta Title:**
  - Optimal length: 45–60 characters (max 580px width).
  - Frontload primary keyword (e.g. `Lost Place Map — Urbex Database & Abandoned Places`).
- **Meta Description:**
  - Optimal length: 120–160 characters.
  - Must contain primary keywords and an active Call-to-Action (e.g. *"Try it free!"* or *"Jetzt kostenlos entdecken"*).
- **Canonical Tag:**
  - Self-referencing, absolute URL without query parameters: `<link rel="canonical" href="https://example.com/" />`.
- **Social Metadata (Open Graph & Twitter Cards):**
  - `og:title`, `og:description`, `og:type="website"`, `og:image` (absolute URL, min 512x512px).
  - `twitter:card="summary_large_image"`, `twitter:title`, `twitter:description`, `twitter:image`.
- **Robots & Viewport:**
  - `<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />`.
  - `<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />`.
- **Language & Hreflang:**
  - Explicit `<html lang="...">` plus reciprocal `<link rel="alternate" hreflang="..." href="..." />` for all supported languages and `x-default`.

### Pillar 2: Seitenqualität & Content (360 Points — 100%)
- **Word Count & Content Volume (`factor_text`):**
  - **Critical Rule:** Seobility flags `text_short` with a 50% point deduction if the visible/SSR text is under 500 words.
  - **Optimal:** Minimum 600–700 words of relevant, original content in the SSR fallback / noscript body.
- **Headings Structure:**
  - Strictly **one** `<h1>` tag matching page intent.
  - Logical hierarchy: `<h1>` -> `<h2>` -> `<h3>` (no skipped levels, e.g. avoid `<h1>` directly followed by `<h3>`).
- **Image Optimization:**
  - Every `<img>` tag **must** have an descriptive `alt` attribute.
  - Set explicit `width` and `height` attributes to prevent Cumulative Layout Shift (CLS).
- **Social Sharing Integration (`factor_socialshare`):**
  - Seobility detects whether the page offers social sharing functionality.
  - Include native share intent links for major platforms (X/Twitter, Facebook, Reddit, Telegram, WhatsApp):
    ```html
    <a href="https://twitter.com/intent/tweet?url=https%3A%2F%2Fexample.com&text=..." target="_blank" rel="noopener noreferrer">Share on X</a>
    <a href="https://www.facebook.com/sharer/sharer.php?u=https%3A%2F%2Fexample.com" target="_blank" rel="noopener noreferrer">Share on Facebook</a>
    ```

### Pillar 3: Seitenstruktur (170 Points — 100%)
- **Schema.org Structured Data (JSON-LD):**
  - Include `@context: "https://schema.org"` with an `@graph` array linking:
    1. `WebSite`: URL, name, description, `potentialAction: SearchAction`.
    2. `Organization`: name, url, logo.
    3. `WebApplication` / `SoftwareApplication`: name, operatingSystem, applicationCategory, offers (`price: "0"`).
    4. `FAQPage`: Rich snippet questions (`Question` & `acceptedAnswer`).
    5. `BreadcrumbList`: Hierarchical `ListItem` trail on subpages/categories.

### Pillar 4: Verlinkung / Links (80 Points — 100%)
- **Internal Links:**
  - Min. 10–20 crawlable internal links with meaningful anchor text (e.g. navigation links to categories, legal pages, directory).
- **External Authority Links (`factor_link_external`):**
  - **Critical Rule:** Seobility penalizes pages with 0 external outbound links (`link_external_none`, 0% score).
  - Include 2–3 authoritative, relevant external links with `target="_blank" rel="noopener noreferrer"` (e.g. OpenStreetMap, Wikipedia, or official industry/ethics bodies like Leave No Trace).

### Pillar 5: Server & Technik (110 Points — 100%)
- **HTTP/2 & HTTPS:** Enforced via reverse proxy / Nginx.
- **Security & Caching Headers:**
  - `Cache-Control: public, max-age=0, s-maxage=300, stale-while-revalidate=600`.
  - `Strict-Transport-Security: max-age=34560000; includeSubDomains`.
  - `X-Content-Type-Options: nosniff`.
- **Response Time:** Fast TTFB (< 200ms) with gzip/brotli compression.

---

## 3. Automated Seobility CLI Tool

The skill includes a dedicated script to trigger Seobility audits programmatically:

```bash
# Run full live audit against Seobility engine
python3 scripts/seobility_check.py https://lostfoundations.org

# Output raw JSON or save to file
python3 scripts/seobility_check.py https://lostfoundations.org --save /tmp/audit.json
```

### Interpreting the Output Ledger

The script outputs a structured scorecard:
```
=======================================================
  SEOBILITY AUDIT REPORT: https://lostfoundations.org/
  OVERALL SEO SCORE: 97%
=======================================================

CATEGORY BREAKDOWN:
  Kategorie                 | Punkte       | Score %  | Status
  --------------------------|--------------|----------|-----------
  Meta-Angaben              | 515 / 515    | 100%     | PERFEKT
  Seitenqualität (Content)  | 360 / 360    | 100%     | PERFEKT
  Seitenstruktur            | 170 / 170    | 100%     | PERFEKT
  Verlinkung (Links)        | 80 / 80      | 100%     | PERFEKT
  Server & Technik          | 110 / 110    | 100%     | PERFEKT
  Off-Page (Backlinks)      | 60 / 100     | 60%      | OPTIMIEREN
```

> [!NOTE]
> All On-Page categories (Meta, Page Quality, Structure, Links, Server) are directly controlled by the codebase and should reach **100%**. The remaining points in the overall score (e.g. 97% vs 100%) stem from the `extern` category (SEOKicks backlink index), which tracks third-party domain age and external referring domains.

---

## 4. Remediation Quick Reference

| Seobility Warning | Root Cause | Exact Solution |
| :--- | :--- | :--- |
| `text_short` | Word count < 500 words | Expand SSR/noscript body with informative topic content to reach 650+ words. |
| `link_external_none` | 0 outgoing links on page | Add 2–3 authoritative outbound links (OpenStreetMap, Wikipedia, standards organizations). |
| `socialshare_no_plugin` | No social share widgets | Add share links for X, Facebook, Reddit, Telegram, WhatsApp. |
| `title_toolong` | Title > 60 chars or > 580px | Trim title to 50–58 chars; frontload primary keyword. |
| `description_short` / `description_toolong` | Description < 120 or > 160 chars | Adjust description to 145–158 characters with an active CTA. |
| `h1_missing` or `h1_multiple` | 0 or >1 `<h1>` tags | Enforce exactly one `<h1>` per page. |
| `img_altmissing` | Images missing `alt` attribute | Add descriptive `alt="Description of image"` to every `<img>`. |

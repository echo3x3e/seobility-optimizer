---
name: seobility-optimizer
description: Audits HTML files, local development servers, or live websites against both the Seobility SEO engine and Google PageSpeed Insights (Lighthouse / Core Web Vitals) to reach 100% On-Page SEO & Performance scores. No deployment required.
---

# Seobility & Google PageSpeed Insights (Lighthouse) Optimizer

## Overview

The `seobility-optimizer` skill analyzes web pages and source templates against **both** the official **Seobility SEO scoring rubric** and **Google PageSpeed Insights (Lighthouse v5 API + Core Web Vitals)**, providing the exact code modifications required to reach a **100% On-Page SEO & Lighthouse score**. It operates on **local HTML files**, **local development servers** (`localhost:3000`), or **live URLs**, without requiring any server deployment or remote SSH access.

## When to Use

- When the user asks to *"check Seobility score"*, *"check Google PageSpeed Insights"*, *"optimize Core Web Vitals"*, *"reach 100% on Seobility and PageSpeed"*, or *"audit SEO without deploying"*.
- Analyzing local template files (`index.html`, SSR templates, React/Vite/Next.js components).
- Diagnosing Seobility warnings (`text_short`, `link_external_none`, `socialshare_no_plugin`, `title_toolong`, `description_short`) **and** Google PageSpeed / Lighthouse warnings (`render-blocking-resources`, `unsized-images`, `largest-contentful-paint`, `cumulative-layout-shift`, `total-blocking-time`, `font-display`, `meta-viewport`).

---

## 1. Quick Start: Auditing Any Target (Seobility + Google PageSpeed Insights)

The skill includes the unified CLI tool `scripts/seobility_check.py` which runs **Seobility On-Page checks + Google PageSpeed Insights (Mobile/Desktop)** in a single command:

```bash
# 1. Audit a local HTML file (Seobility + static Core Web Vitals / Lighthouse check):
python3 ~/.gemini/antigravity-cli/skills/seobility-optimizer/scripts/seobility_check.py index.html

# 2. Audit a local dev server:
python3 ~/.gemini/antigravity-cli/skills/seobility-optimizer/scripts/seobility_check.py http://localhost:3000

# 3. Audit a live website (Seobility Live API + Google PageSpeed Insights v5 API for Mobile & Desktop):
python3 ~/.gemini/antigravity-cli/skills/seobility-optimizer/scripts/seobility_check.py https://example.com --strategy both

# 4. Optional: Pass a Google PageSpeed API Key (or set PAGESPEED_API_KEY env var) for higher quota:
python3 ~/.gemini/antigravity-cli/skills/seobility-optimizer/scripts/seobility_check.py https://example.com --strategy both --psi-key YOUR_API_KEY
```

---

## 2. The Seobility 100% On-Page Compliance Blueprint

Seobility awards full on-page points (100% across all pillars) when the following exact specifications are met:

### 1. Meta-Angaben (Target: 100% / 515 Points)
- **Title Tag:**
  - Length: Between 45 and 60 characters (max 580 pixels).
  - Structure: Primary Keyword frontloaded + secondary keyword or brand:
    ```html
    <title>Primary Keyword — Secondary Keyword &amp; Brand</title>
    ```
- **Meta Description:**
  - Length: Strictly between 120 and 160 characters.
  - Must include primary search term and a clear Call-to-Action (CTA).
- **Canonical Tag:**
  - Self-referencing, absolute URL: `<link rel="canonical" href="https://example.com/" />`.
- **Meta Robots & Viewport:**
  - `<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />`
  - `<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />` *(Never add `user-scalable=no` or `maximum-scale=1`, as that fails Google Lighthouse Accessibility!)*
- **Social Metadata (Open Graph & Twitter):**
  - `og:title`, `og:description`, `og:url`, `og:image` (min. 512x512px).
  - `twitter:card="summary_large_image"`, `twitter:title`, `twitter:description`, `twitter:image`.

### 2. Seitenqualität & Content (Target: 100% / 360 Points)
- **Text Volume (`factor_text`):**
  - **Rule:** If visible/SSR text is under 500 words, Seobility triggers `text_short` (50% deduction).
  - **Solution:** Provide at least 600–750 words of rich, relevant editorial or informative text in the SSR fallback body or noscript block.
- **Heading Structure:**
  - Strictly **one** `<h1>` tag per page reflecting the main topic.
  - Logical hierarchy: `<h1>` followed by `<h2>`, then `<h3>`. Never skip heading levels.
- **Image Optimization:**
  - Every single `<img>` must have a non-empty `alt="..."` attribute and explicit `width` and `height` attributes.
- **Social Sharing Integration (`factor_socialshare`):**
  - Include social sharing intent links (e.g. for X/Twitter, Facebook, Telegram, WhatsApp, Reddit) to clear the `socialshare_no_plugin` check.

### 3. Seitenstruktur (Target: 100% / 170 Points)
- **Schema.org Structured Data (JSON-LD):**
  - Add an `@graph` array within `<script type="application/ld+json">` containing `WebSite`, `Organization`, `FAQPage`, and `BreadcrumbList`.

### 4. Verlinkung / Links (Target: 100% / 80 Points)
- **Internal Links:** 10–25 clean internal links with unique descriptive anchor text.
- **External Authority Links (`factor_link_external`):** Add 2–3 authoritative external outbound links relevant to your topic with `target="_blank" rel="noopener noreferrer"`.

### 5. Server & Technik (Target: 100% / 110 Points)
- **HTTP/2 & Compression:** Ensure gzip/brotli is enabled.
- **Caching & Security Headers:** `Cache-Control`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`.

---

## 3. Google PageSpeed Insights & Core Web Vitals Blueprint (Target: 95–100)

Google PageSpeed Insights (Lighthouse) evaluates 4 categories (`Performance`, `Accessibility`, `Best Practices`, `SEO`) and Core Web Vitals:

| Metric / Audit | Green Target | Code Fix for 100/100 |
| :--- | :--- | :--- |
| **LCP (Largest Contentful Paint)** | `<= 2.5 s` | Preload hero image (`<link rel="preload" as="image" href="..." fetchpriority="high">`), inline critical CSS, eliminate render-blocking `<script>`/`<link>` in `<head>`. |
| **FCP (First Contentful Paint)** | `<= 1.8 s` | Add `<link rel="preconnect">` for critical origins (`fonts.gstatic.com`), use `&display=swap` on Google Fonts, enable Brotli/Gzip. |
| **TBT / INP (Interactivity)** | `<= 200 ms` | Mark all scripts with `defer` or `type="module"`, code-split heavy bundles (e.g., OpenCV, PDF, charts) via dynamic `import()`. |
| **CLS (Cumulative Layout Shift)** | `<= 0.10` | Add explicit `width="..."` and `height="..."` (or CSS `aspect-ratio`) to **every** `<img>`, `<video>`, and `<iframe>`. |
| **Modern Image Formats** | `100%` | Convert `.png`/`.jpg` assets to `.webp` or `.avif`; add `loading="lazy" decoding="async"` to all below-the-fold images. |
| **Accessibility (`meta-viewport` & `html-has-lang`)** | `100%` | Ensure `<html lang="de">`, never use `user-scalable=no` or `maximum-scale=1`, and provide `aria-label` on icon-only buttons. |

---

## 4. Systematic Optimization Workflow

```
1. AUDIT (SEOBILITY + GOOGLE PAGESPEED INSIGHTS)
   Run: python3 scripts/seobility_check.py <target> --strategy both
   Capture all Seobility deductions + Google PageSpeed / Lighthouse opportunities.

2. FIX
   Apply code fixes to source files:
   - Seobility:
     * Word count < 500? -> Expand SSR/noscript text to 650+ words.
     * Missing external links? -> Add 2-3 authoritative outbound links.
     * Missing social share? -> Add X, Facebook, Telegram, WhatsApp share links.
     * Title / Description lengths? -> Adjust to 50-58 chars and 140-155 chars.
   - Google PageSpeed Insights:
     * Render-blocking scripts? -> Add defer / type="module" or dynamic import().
     * Unsized images (CLS)? -> Add explicit width & height attributes.
     * Hero image slow (LCP)? -> Add fetchpriority="high" and WebP format.
     * Fonts blocking text? -> Add rel="preconnect" and display=swap.

3. RE-AUDIT
   Run seobility_check.py again to verify 100% Seobility On-Page score and 90-100 Google PageSpeed scores.
```

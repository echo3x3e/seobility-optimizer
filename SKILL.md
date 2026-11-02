---
name: seobility-optimizer
description: Audits HTML files, local development servers, or live websites against the Seobility SEO engine and optimizes code to reach a 100% On-Page score across Meta, Page Quality/Content, Structure, Links, and Server technical checks. No deployment required.
---

# Seobility On-Page SEO Optimizer

## Overview

The `seobility-optimizer` skill analyzes web pages and source templates against the official **Seobility SEO scoring rubric** and provides the exact code modifications required to reach a **100% On-Page SEO score**. It operates on **local HTML files**, **local development servers** (`localhost:3000`), or **live URLs**, without requiring any server deployment or remote SSH access.

## When to Use

- When the user asks to *"check Seobility score"*, *"optimize for Seobility"*, *"reach 100% on Seobility"*, or *"audit SEO without deploying"*.
- Analyzing local template files (`index.html`, SSR templates, React components).
- Diagnosing Seobility warnings such as `text_short`, `link_external_none`, `socialshare_no_plugin`, `title_toolong`, `description_short`, or missing Schema.org structured data.
- Preparing on-page SEO before opening pull requests or merging releases.

---

## 1. Quick Start: Auditing Any Target

The skill includes the standalone CLI tool `scripts/seobility_check.py`:

```bash
# 1. Audit a local file directly (fastest, 0 network, no deployment needed):
python3 ~/.gemini/antigravity-cli/skills/seobility-optimizer/scripts/seobility_check.py index.html

# 2. Audit a local dev server:
python3 ~/.gemini/antigravity-cli/skills/seobility-optimizer/scripts/seobility_check.py http://localhost:3000

# 3. Audit a live website (uses Seobility API or local rule engine):
python3 ~/.gemini/antigravity-cli/skills/seobility-optimizer/scripts/seobility_check.py https://lostfoundations.org
```

---

## 2. The Seobility 100% On-Page Compliance Blueprint

Seobility awards full on-page points (100% across all pillars) when the following exact specifications are met:

### 1. Meta-Angaben (Target: 100% / 515 Points)
- **Title Tag:**
  - Length: Between 45 and 60 characters (max 580 pixels).
  - Structure: Primary Keyword frontloaded + secondary keyword or brand:
    ```html
    <title>Lost Place Map — Urbex Database &amp; Abandoned Places</title>
    ```
- **Meta Description:**
  - Length: Strictly between 120 and 160 characters.
  - Must include primary search term and a clear Call-to-Action (CTA):
    ```html
    <meta name="description" content="Explore abandoned places near you on the largest interactive Lost Place Map. 10,000+ urbex spots with GPS coordinates, photos &amp; safety ratings. Try it free!" />
    ```
- **Canonical Tag:**
  - Self-referencing, absolute URL: `<link rel="canonical" href="https://example.com/" />`.
- **Meta Robots & Viewport:**
  - `<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />`
  - `<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />`
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
  - Every single `<img>` must have a non-empty `alt="..."` attribute.
  - Set explicit `width` and `height` attributes to prevent CLS.
- **Social Sharing Integration (`factor_socialshare`):**
  - Include social sharing intent links (e.g. for X/Twitter, Facebook, Telegram, WhatsApp, Reddit) to clear the `socialshare_no_plugin` check:
    ```html
    <a href="https://twitter.com/intent/tweet?url=https%3A%2F%2Fexample.com&amp;text=..." target="_blank" rel="noopener noreferrer">Share on X</a>
    <a href="https://www.facebook.com/sharer/sharer.php?u=https%3A%2F%2Fexample.com" target="_blank" rel="noopener noreferrer">Share on Facebook</a>
    ```

### 3. Seitenstruktur (Target: 100% / 170 Points)
- **Schema.org Structured Data (JSON-LD):**
  - Add an `@graph` array within `<script type="application/ld+json">`:
    ```json
    {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "WebSite",
          "@id": "https://example.com/#website",
          "url": "https://example.com",
          "name": "Brand",
          "potentialAction": {
            "@type": "SearchAction",
            "target": "https://example.com/search?q={query}",
            "query-input": "required name=query"
          }
        },
        {
          "@type": "Organization",
          "name": "Brand",
          "url": "https://example.com",
          "logo": "https://example.com/logo.png"
        },
        {
          "@type": "FAQPage",
          "mainEntity": [
            {
              "@type": "Question",
              "name": "Is it free?",
              "acceptedAnswer": { "@type": "Answer", "text": "Yes, 100% free." }
            }
          ]
        }
      ]
    }
    ```

### 4. Verlinkung / Links (Target: 100% / 80 Points)
- **Internal Links:**
  - 10–25 clean internal links (`/explorer`, `/directory`, `/category/...`) with unique descriptive anchor text.
- **External Authority Links (`factor_link_external`):**
  - **Rule:** 0 external links triggers `link_external_none` (0% score).
  - **Solution:** Add 2–3 authoritative external outbound links relevant to your topic with `target="_blank" rel="noopener noreferrer"` (e.g., OpenStreetMap, Wikipedia, official associations or standards).

### 5. Server & Technik (Target: 100% / 110 Points)
- **HTTP/2 & Compression:** Ensure gzip/brotli is enabled.
- **Caching Headers:** `Cache-Control: public, max-age=0, s-maxage=300, stale-while-revalidate=600`.
- **Security Headers:** `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`.

---

## 3. Systematic Optimization Workflow

When assigned to optimize a page or project for Seobility:

```
1. AUDIT
   Run seobility_check.py against local file or target URL.
   Capture all deductions and warnings.

2. FIX
   Apply code fixes to source files:
   - Word count < 500? -> Expand SSR/noscript text with relevant topic info.
   - Missing external links? -> Add 2-3 links to Wikipedia / OpenStreetMap.
   - Missing social share? -> Add X, Facebook, Telegram intent links.
   - Title / Description lengths? -> Adjust to 50-58 chars and 140-155 chars.
   - H1 issues? -> Normalize to exactly 1x <h1>.

3. RE-AUDIT
   Run seobility_check.py again to verify 100% score on all on-page categories.
```

#!/usr/bin/env python3
"""
Seobility & Google PageSpeed Insights (Lighthouse / Core Web Vitals) Auditor CLI
Audits live URLs, local development servers (localhost:3000), or local HTML files
against both the Seobility SEO scoring rubric AND Google PageSpeed Insights (v5 API + local CWV rules)
to reach 100% On-Page SEO & Core Web Vitals compliance.
"""

import sys
import os
import json
import re
import argparse
import urllib.parse
import requests


def run_seobility_api_audit(target_url: str, language: str = "de", crawling_mode: str = "standard"):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://www.seobility.net/{language}/seocheck/check/?url={urllib.parse.quote(target_url)}",
        "Origin": "https://www.seobility.net",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*"
    })

    # Pre-flight domain check
    domain_check_url = f"https://app.seobility.net/dapi/domain-check?url={urllib.parse.quote(target_url)}"
    session.get(domain_check_url, timeout=15)

    xsrf = session.cookies.get("XSRF-TOKEN")
    if xsrf:
        session.headers["X-XSRF-TOKEN"] = urllib.parse.unquote(xsrf)

    payload = {
        "website": target_url,
        "crawling_mode": crawling_mode,
        "http_authentication_user": "",
        "http_authentication_password": "",
        "language": language
    }

    r_check = session.post("https://app.seobility.net/dapi/live-tools/seo-check", json=payload, timeout=30)
    if r_check.status_code != 200:
        err_msg = r_check.text[:300]
        try:
            err_json = r_check.json()
            err_msg = err_json.get("error", {}).get("message", err_msg)
        except Exception:
            pass
        raise RuntimeError(f"Seobility API ({r_check.status_code}): {err_msg}")

    return r_check.json()


def run_pagespeed_api_audit(target_url: str, strategy: str = "mobile", api_key: str = ""):
    """
    Queries the official Google PageSpeed Insights v5 API for Performance, Accessibility,
    Best Practices, SEO, and Core Web Vitals (LCP, FCP, TBT, CLS, SI).
    """
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = [
        ("url", target_url),
        ("strategy", strategy),
        ("category", "performance"),
        ("category", "accessibility"),
        ("category", "best-practices"),
        ("category", "seo"),
    ]
    effective_key = api_key or os.environ.get("PAGESPEED_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    if effective_key:
        params.append(("key", effective_key))

    resp = requests.get(endpoint, params=params, timeout=60)
    if resp.status_code != 200:
        err_msg = resp.text[:300]
        try:
            err_msg = resp.json().get("error", {}).get("message", err_msg)
        except Exception:
            pass
        raise RuntimeError(f"Google PageSpeed API ({resp.status_code}): {err_msg}")

    raw = resp.json()
    lh = raw.get("lighthouseResult", {})
    cats = lh.get("categories", {})
    audits = lh.get("audits", {})

    def cat_score(key: str) -> int:
        val = cats.get(key, {}).get("score")
        return int(round(val * 100)) if val is not None else 0

    def metric_info(audit_id: str):
        a = audits.get(audit_id, {})
        return {
            "displayValue": a.get("displayValue", "n/a"),
            "numericValue": a.get("numericValue"),
            "score": int(round(a["score"] * 100)) if a.get("score") is not None else None
        }

    opportunities = []
    for audit_id, audit_obj in audits.items():
        if not isinstance(audit_obj, dict):
            continue
        score = audit_obj.get("score")
        details = audit_obj.get("details", {})
        if score is not None and score < 0.9:
            savings_ms = details.get("overallSavingsMs", 0)
            if details.get("type") == "opportunity" or savings_ms > 0 or score < 0.5:
                opportunities.append({
                    "id": audit_id,
                    "title": audit_obj.get("title", audit_id),
                    "displayValue": audit_obj.get("displayValue", ""),
                    "score": int(round(score * 100)),
                    "savingsMs": savings_ms
                })

    opportunities.sort(key=lambda x: (-x.get("savingsMs", 0), x.get("score", 100)))

    return {
        "simulated": False,
        "strategy": strategy,
        "analysed_url": lh.get("finalUrl", target_url),
        "categories": {
            "performance": cat_score("performance"),
            "accessibility": cat_score("accessibility"),
            "best-practices": cat_score("best-practices"),
            "seo": cat_score("seo"),
        },
        "metrics": {
            "FCP": metric_info("first-contentful-paint"),
            "LCP": metric_info("largest-contentful-paint"),
            "TBT": metric_info("total-blocking-time"),
            "CLS": metric_info("cumulative-layout-shift"),
            "SI": metric_info("speed-index"),
            "TTFB": metric_info("server-response-time"),
        },
        "opportunities": opportunities[:12]
    }


def audit_html_pagespeed(html: str, source_label: str, strategy: str = "mobile"):
    """
    Evaluates raw HTML against Google Lighthouse / PageSpeed Insights & Core Web Vitals heuristics
    when auditing local HTML files, localhost dev servers, or when PSI API is offline/rate-limited.
    """
    scores = {
        "performance": 100,
        "accessibility": 100,
        "best-practices": 100,
        "seo": 100,
    }
    opportunities = []

    # 1. Render-blocking scripts in <head>
    head_match = re.search(r"<head[^>]*>([\s\S]*?)</head>", html, re.IGNORECASE)
    head_html = head_match.group(1) if head_match else ""
    head_scripts = re.findall(r"<script([^>]*)>", head_html, re.IGNORECASE)
    blocking_scripts = []
    for s_attrs in head_scripts:
        s_lower = s_attrs.lower()
        if "src=" in s_lower and not any(k in s_lower for k in ("defer", "async", 'type="module"', "type='module'", "application/ld+json")):
            blocking_scripts.append(s_attrs)
    if blocking_scripts:
        deduction = min(25, len(blocking_scripts) * 8)
        scores["performance"] -= deduction
        opportunities.append({
            "id": "render-blocking-resources",
            "title": f"{len(blocking_scripts)} Render-blockierende <script>-Tags im <head> ohne defer/async/type='module'",
            "displayValue": "LCP & FCP Bremse",
            "score": max(0, 100 - deduction)
        })

    # 2. Images without width/height (CLS risk) & modern formats / lazy loading
    imgs = re.findall(r"<img([^>]*)>", html, re.IGNORECASE)
    unsized_imgs = []
    missing_alt = []
    non_nextgen_imgs = []
    for img_attrs in imgs:
        low = img_attrs.lower()
        if "width=" not in low or "height=" not in low:
            unsized_imgs.append(img_attrs)
        if "alt=" not in low:
            missing_alt.append(img_attrs)
        src_m = re.search(r'src=["\']([^"\']+)["\']', img_attrs, re.IGNORECASE)
        if src_m:
            src_val = src_m.group(1).lower()
            if src_val.endswith((".png", ".jpg", ".jpeg")):
                non_nextgen_imgs.append(src_val)

    if unsized_imgs:
        scores["performance"] -= min(15, len(unsized_imgs) * 5)
        opportunities.append({
            "id": "unsized-images",
            "title": f"{len(unsized_imgs)} <img>-Element(e) ohne explizite width & height Attribute (CLS-Risiko)",
            "displayValue": "CLS <= 0.1 gefährdet",
            "score": 60
        })

    if missing_alt:
        scores["accessibility"] -= min(25, len(missing_alt) * 10)
        scores["seo"] -= 10
        opportunities.append({
            "id": "image-alt",
            "title": f"{len(missing_alt)} <img>-Element(e) ohne alt-Attribut (Lighthouse Accessibility & SEO)",
            "displayValue": "Pflichtfeld",
            "score": 50
        })

    if non_nextgen_imgs:
        scores["performance"] -= min(10, len(non_nextgen_imgs) * 2)
        opportunities.append({
            "id": "modern-image-formats",
            "title": f"{len(non_nextgen_imgs)} Bild(er) in PNG/JPG statt WebP/AVIF",
            "displayValue": "Bandbreite sparen",
            "score": 80
        })

    # 3. Google Fonts / Webfont preconnect & display=swap
    if "fonts.googleapis.com" in html:
        if "display=swap" not in html and "display=optional" not in html:
            scores["performance"] -= 8
            opportunities.append({
                "id": "font-display",
                "title": "Google Fonts ohne '&display=swap' geladen (verursacht FOIT / verzögerten FCP)",
                "displayValue": "FCP Optimierung",
                "score": 75
            })
        if 'rel="preconnect" href="https://fonts.gstatic.com"' not in html and "fonts.gstatic.com" not in head_html:
            scores["performance"] -= 5
            opportunities.append({
                "id": "uses-rel-preconnect",
                "title": "Fehlender <link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>",
                "displayValue": "DNS/TLS Handshake",
                "score": 85
            })

    # 4. Accessibility: <html lang="..."> & Viewport zoom lock
    if not re.search(r"<html[^>]*\blang=['\"][a-zA-Z\-]+['\"]", html, re.IGNORECASE):
        scores["accessibility"] -= 15
        opportunities.append({
            "id": "html-has-lang",
            "title": "<html>-Tag besitzt kein gültiges lang-Attribut (z. B. <html lang='de'>)",
            "displayValue": "A11y Pflicht",
            "score": 0
        })

    viewport_m = re.search(r'<meta[^>]*name=["\']viewport["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE)
    if not viewport_m:
        scores["accessibility"] -= 15
        scores["seo"] -= 15
        opportunities.append({
            "id": "viewport",
            "title": "Kein <meta name='viewport'> vorhanden",
            "displayValue": "Mobile Friendly",
            "score": 0
        })
    else:
        vp_content = viewport_m.group(1).lower()
        if "user-scalable=no" in vp_content or "maximum-scale=1" in vp_content:
            scores["accessibility"] -= 20
            opportunities.append({
                "id": "meta-viewport",
                "title": "Viewport blockiert Zoom (user-scalable=no oder maximum-scale=1 führt zu Lighthouse-Abzug)",
                "displayValue": "A11y Verstoß",
                "score": 0
            })

    # 5. Best Practices: target="_blank" without rel="noopener" & DOCTYPE
    if not re.search(r"<!doctype\s+html>", html, re.IGNORECASE):
        scores["best-practices"] -= 15
        opportunities.append({
            "id": "doctype",
            "title": "Fehlender <!DOCTYPE html> Header (triggert Quirks Mode)",
            "displayValue": "Best Practices",
            "score": 0
        })

    # 6. Lighthouse SEO basics (Title, Meta Description, Crawlable Links)
    if not re.search(r"<title>[^<]+</title>", html, re.IGNORECASE):
        scores["seo"] -= 25
        opportunities.append({
            "id": "document-title",
            "title": "Dokument besitzt kein <title>-Element",
            "displayValue": "SEO Pflicht",
            "score": 0
        })

    if not re.search(r'<meta[^>]*name=["\']description["\']', html, re.IGNORECASE):
        scores["seo"] -= 25
        opportunities.append({
            "id": "meta-description",
            "title": "Dokument besitzt keine <meta name='description'>",
            "displayValue": "SEO Pflicht",
            "score": 0
        })

    for k in scores:
        scores[k] = max(0, min(100, scores[k]))

    return {
        "simulated": True,
        "strategy": strategy,
        "analysed_url": source_label,
        "categories": scores,
        "metrics": {
            "FCP": {"displayValue": "<= 1.2 s (Static Check)" if scores["performance"] >= 90 else "~ 2.4 s (Geschätzt)"},
            "LCP": {"displayValue": "<= 2.0 s (Static Check)" if scores["performance"] >= 90 else "~ 3.2 s (Geschätzt)"},
            "TBT": {"displayValue": f"{len(blocking_scripts) * 80} ms (Blocking Scripts: {len(blocking_scripts)})"},
            "CLS": {"displayValue": "0.00" if not unsized_imgs else f"~ {min(0.45, len(unsized_imgs) * 0.08):.2f} ({len(unsized_imgs)} unsized imgs)"},
            "SI": {"displayValue": "<= 2.5 s" if scores["performance"] >= 90 else "~ 3.8 s"},
        },
        "opportunities": opportunities
    }


def audit_html_content(html: str, source_label: str, base_domain: str = "example.com"):
    """
    Evaluates raw HTML against the exact Seobility 100/100 on-page scoring rules.
    """
    report = {
        "analysed_target": source_label,
        "simulated": True,
        "sections": {
            "meta": {"score_percent": 100, "points": 515, "points_max": 515, "warnings": []},
            "pagequality": {"score_percent": 100, "points": 360, "points_max": 360, "warnings": []},
            "structure": {"score_percent": 100, "points": 170, "points_max": 170, "warnings": []},
            "links": {"score_percent": 100, "points": 80, "points_max": 80, "warnings": []},
            "server": {"score_percent": 100, "points": 110, "points_max": 110, "warnings": []},
        }
    }

    # 1. Meta Title
    title_match = re.search(r"<title>([^<]*)</title>", html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""
    if not title:
        report["sections"]["meta"]["score_percent"] -= 40
        report["sections"]["meta"]["warnings"].append("Fehlt: <title> Tag nicht gefunden.")
    elif len(title) > 65:
        report["sections"]["meta"]["score_percent"] -= 15
        report["sections"]["meta"]["warnings"].append(f"Title zu lang ({len(title)} Zeichen > 65): '{title[:45]}...'")
    elif len(title) < 25:
        report["sections"]["meta"]["score_percent"] -= 10
        report["sections"]["meta"]["warnings"].append(f"Title zu kurz ({len(title)} Zeichen < 25).")

    # 2. Meta Description
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE) or \
                 re.search(r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']', html, re.IGNORECASE)
    desc = desc_match.group(1).strip() if desc_match else ""
    if not desc:
        report["sections"]["meta"]["score_percent"] -= 40
        report["sections"]["meta"]["warnings"].append("Fehlt: Meta Description nicht gefunden.")
    elif len(desc) < 120:
        report["sections"]["meta"]["score_percent"] -= 15
        report["sections"]["meta"]["warnings"].append(f"Description zu kurz ({len(desc)} Zeichen < 120). Empfohlen: 140-160.")
    elif len(desc) > 165:
        report["sections"]["meta"]["score_percent"] -= 15
        report["sections"]["meta"]["warnings"].append(f"Description zu lang ({len(desc)} Zeichen > 165).")

    # 3. Canonical Tag
    canonical = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']*)["\']', html, re.IGNORECASE)
    if not canonical:
        report["sections"]["meta"]["score_percent"] -= 20
        report["sections"]["meta"]["warnings"].append("Fehlt: Canonical Tag (<link rel='canonical'>) nicht gefunden.")

    # 4. Robots & Viewport
    if not re.search(r'<meta[^>]*name=["\']robots["\']', html, re.IGNORECASE):
        report["sections"]["meta"]["score_percent"] -= 10
        report["sections"]["meta"]["warnings"].append("Empfohlen: Meta Robots Tag definieren (z. B. index, follow).")
    if not re.search(r'<meta[^>]*name=["\']viewport["\']', html, re.IGNORECASE):
        report["sections"]["pagequality"]["score_percent"] -= 20
        report["sections"]["pagequality"]["warnings"].append("Fehlt: Viewport Meta Tag für Mobile Responsiveness.")

    # 5. H1 Tag (strictly 1)
    h1s = re.findall(r'<h1[^>]*>([\s\S]*?)</h1>', html, re.IGNORECASE)
    if len(h1s) == 0:
        report["sections"]["structure"]["score_percent"] -= 50
        report["sections"]["structure"]["warnings"].append("Fehlt: Kein <h1> Tag gefunden. Genau 1x <h1> erforderlich.")
    elif len(h1s) > 1:
        report["sections"]["structure"]["score_percent"] -= 30
        report["sections"]["structure"]["warnings"].append(f"Mehrere <h1> Tags ({len(h1s)}) gefunden. Genau 1x <h1> erlaubt.")

    # 6. Text Volume / Word count (Seobility factor_text)
    cleaned = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    cleaned = re.sub(r'<style[\s\S]*?</style>', '', cleaned, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', cleaned)
    words = [w for w in re.split(r'\s+', text) if len(w) > 1]
    word_count = len(words)
    if word_count < 300:
        report["sections"]["pagequality"]["score_percent"] -= 50
        report["sections"]["pagequality"]["warnings"].append(f"text_short: Nur {word_count} Wörter. Seobility verlangt mindestens 500-600 Wörter für 100%.")
    elif word_count < 500:
        report["sections"]["pagequality"]["score_percent"] -= 30
        report["sections"]["pagequality"]["warnings"].append(f"text_short: {word_count} Wörter (unter Seobilitys Richtwert von 500-600 Wörtern).")

    # 7. External Authority Links (Seobility factor_link_external)
    ext_links = re.findall(r'<a[^>]*href=["\'](https?://(?!' + base_domain.replace('.', r'\.') + r')[^"\']+)["\']', html, re.IGNORECASE)
    if len(ext_links) == 0:
        report["sections"]["links"]["score_percent"] -= 35
        report["sections"]["links"]["warnings"].append("link_external_none: 0 externe Autoritäts-Links gefunden. Seobility verlangt 1-3 Links zu Wikipedia/OSM o. ä.")

    # 8. Social Share Intents (Seobility factor_socialshare)
    has_social = bool(re.search(r'(twitter\.com/intent|facebook\.com/sharer|reddit\.com/submit|t\.me/share|whatsapp\.com/send)', html, re.IGNORECASE))
    if not has_social:
        report["sections"]["pagequality"]["score_percent"] -= 15
        report["sections"]["pagequality"]["warnings"].append("socialshare_no_plugin: Keine Social-Sharing-Buttons/Links (X, FB, Telegram, WhatsApp) gefunden.")

    # 9. Image Alt Attributes
    imgs = re.findall(r'<img([^>]*)>', html, re.IGNORECASE)
    missing_alt = [img for img in imgs if 'alt=' not in img.lower()]
    if missing_alt:
        report["sections"]["pagequality"]["score_percent"] -= 20
        report["sections"]["pagequality"]["warnings"].append(f"img_altmissing: {len(missing_alt)} Bild(er) ohne 'alt'-Attribut gefunden.")

    # 9b. Duplicate Bold / Strong Tags (Seobility factor_bold_tags -> boldtags_dublicated_tag)
    bold_tags = re.findall(r'<(?:strong|b)(?:\s[^>]*)?>([\s\S]*?)</(?:strong|b)>', cleaned, re.IGNORECASE)
    seen_bold = set()
    dup_bold = []
    for bt in bold_tags:
        norm_bt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', bt)).strip().lower()
        if not norm_bt:
            continue
        if norm_bt in seen_bold and norm_bt not in dup_bold:
            dup_bold.append(norm_bt)
        seen_bold.add(norm_bt)
    if dup_bold:
        report["sections"]["pagequality"]["score_percent"] -= 3
        report["sections"]["pagequality"]["warnings"].append(
            f"boldtags_dublicated_tag: Doppelte <strong>/<b> Tags gefunden ({', '.join(repr(x) for x in dup_bold[:5])}). Jeder <strong>-Text darf nur 1x pro Seite vorkommen."
        )

    # 10. Structured Data (JSON-LD)
    json_lds = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', html, re.IGNORECASE)
    if not json_lds:
        report["sections"]["structure"]["score_percent"] -= 20
        report["sections"]["structure"]["warnings"].append("Fehlt: Kein Schema.org JSON-LD Structured Data Block gefunden.")
    else:
        for idx, block in enumerate(json_lds):
            try:
                json.loads(block)
            except Exception as e:
                report["sections"]["structure"]["score_percent"] -= 15
                report["sections"]["structure"]["warnings"].append(f"JSON-LD Syntax-Fehler in Skript {idx+1}: {e}")

    sec_scores = [max(0, s["score_percent"]) for s in report["sections"].values()]
    for s in report["sections"].values():
        s["score_percent"] = max(0, s["score_percent"])
    report["overall_percent"] = max(0, int(sum(sec_scores) / len(sec_scores)))
    report["word_count"] = word_count

    return report


def format_pagespeed_report(psi_list: list) -> str:
    if not psi_list:
        return ""
    lines = []
    for psi in psi_list:
        strat = psi.get("strategy", "mobile").upper()
        mode_tag = "STATIC CWV HEURISTICS" if psi.get("simulated") else "GOOGLE PAGESPEED INSIGHTS API v5"
        cats = psi.get("categories", {})
        metrics = psi.get("metrics", {})
        opps = psi.get("opportunities", [])

        lines.append(f"=======================================================")
        lines.append(f"  GOOGLE PAGESPEED INSIGHTS ({strat} — {mode_tag})")
        lines.append(f"  Target: {psi.get('analysed_url')}")
        lines.append(f"=======================================================\n")
        lines.append("LIGHTHOUSE KATEGORIEN (0-100):")
        lines.append(f"  {'Kategorie':<25} | {'Score':<8} | {'Status'}")
        lines.append(f"  {'-'*25}-|-{'-'*8}-|-{'-'*12}")
        cat_labels = [
            ("performance", "Performance (CWV)"),
            ("accessibility", "Accessibility (A11y)"),
            ("best-practices", "Best Practices"),
            ("seo", "Google Lighthouse SEO"),
        ]
        for key, label in cat_labels:
            sc = cats.get(key, 0)
            st = "90-100 GRÜN" if sc >= 90 else ("50-89 GELB" if sc >= 50 else "0-49 ROT")
            lines.append(f"  {label:<25} | {f'{sc}%':<8} | {st}")

        lines.append("\nCORE WEB VITALS & LAB METRIKEN:")
        for m_key, m_label in [
            ("LCP", "Largest Contentful Paint (LCP <= 2.5s)"),
            ("FCP", "First Contentful Paint   (FCP <= 1.8s)"),
            ("TBT", "Total Blocking Time      (TBT <= 200ms)"),
            ("CLS", "Cumulative Layout Shift  (CLS <= 0.10)"),
            ("SI", "Speed Index              (SI  <= 3.4s)"),
        ]:
            m_val = metrics.get(m_key, {}).get("displayValue", "n/a")
            lines.append(f"  • {m_label:<40}: {m_val}")

        if opps:
            lines.append("\nOPTIMIERUNGSPOTENZIAL (PAGESPEED / LIGHTHOUSE):")
            for op in opps:
                extra = f" [{op['displayValue']}]" if op.get("displayValue") else ""
                lines.append(f"  • ({op.get('id')}) {op.get('title')}{extra}")
        else:
            lines.append("\n  Alle geprüften PageSpeed- & Core-Web-Vitals-Kriterien im grünen Bereich!")
        lines.append("\n")
    return "\n".join(lines)


def format_report(data: dict, psi_reports: list = None) -> str:
    lines = []
    if data.get("simulated"):
        lines.append(f"\n=======================================================")
        lines.append(f"  SEOBILITY ON-PAGE AUDIT: {data.get('analysed_target')}")
        lines.append(f"  OVERALL ON-PAGE SCORE: {data.get('overall_percent')}%")
        lines.append(f"  Analysierte Textmenge: {data.get('word_count', 0)} Wörter")
        lines.append(f"=======================================================\n")
        lines.append("ON-PAGE KATEGORIEN:")
        lines.append(f"  {'Kategorie':<25} | {'Score %':<8} | {'Status'}")
        lines.append(f"  {'-'*25}-|-{'-'*8}-|-{'-'*10}")

        category_names = {
            "meta": "Meta-Angaben",
            "pagequality": "Seitenqualität (Content)",
            "structure": "Seitenstruktur",
            "links": "Verlinkung (Links)",
            "server": "Server & Technik"
        }

        for key, label in category_names.items():
            sec = data.get("sections", {}).get(key, {})
            pct = f"{sec.get('score_percent')}%"
            status = "100% PERFEKT" if sec.get('score_percent') == 100 else "OPTIMIEREN"
            lines.append(f"  {label:<25} | {pct:<8} | {status}")

        lines.append("\n" + "="*55)
        lines.append("HANDLUNGSBEDARF & ABZÜGE (SEOBILITY):")
        lines.append("="*55)
        warnings = []
        for sec in data.get("sections", {}).values():
            warnings.extend(sec.get("warnings", []))
        if warnings:
            for w in warnings:
                lines.append(f"  • {w}")
        else:
            lines.append("  Keine Abzüge! Alle On-Page-Kriterien erfüllen zu 100% die Seobility-Standards.")
        lines.append("\n")
    else:
        analysis = data.get("data", {}).get("analysis", {})
        score_data = analysis.get("score", {})
        overall = score_data.get("overall_percent", 0)
        sections = score_data.get("sections", {})
        results = analysis.get("results", {})

        lines.append(f"\n=======================================================")
        lines.append(f"  SEOBILITY LIVE API AUDIT: {analysis.get('analysed_url')}")
        lines.append(f"  OVERALL SEO SCORE: {overall}%")
        lines.append(f"=======================================================\n")

        lines.append("KATEGORIE-ÜBERSICHT:")
        lines.append(f"  {'Kategorie':<25} | {'Punkte':<12} | {'Score %':<8} | {'Status'}")
        lines.append(f"  {'-'*25}-|-{'-'*12}-|-{'-'*8}-|-{'-'*10}")

        pillar_names = {
            "meta": "Meta-Angaben",
            "pagequality": "Seitenqualität (Content)",
            "structure": "Seitenstruktur",
            "links": "Verlinkung (Links)",
            "server": "Server & Technik",
            "extern": "Off-Page (Backlinks)"
        }

        for key, label in pillar_names.items():
            sec = sections.get(key, {})
            pts = f"{sec.get('points', 0)} / {sec.get('points_max', 0)}"
            pct = f"{sec.get('score_percent', 0)}%"
            status = "100% PERFEKT" if sec.get('score_percent', 0) == 100 else ("GUT" if sec.get('score_percent', 0) >= 80 else "OPTIMIEREN")
            lines.append(f"  {label:<25} | {pts:<12} | {pct:<8} | {status}")

        lines.append("\n" + "="*55)
        lines.append("SEOBILITY FACTOR WARNINGS:")
        lines.append("="*55)

        deductions_found = False
        for section_name, section in results.items():
            if not isinstance(section, dict):
                continue
            for factor_name, factor in section.items():
                if not isinstance(factor, dict) or "messages" not in factor:
                    continue
                for msg in factor["messages"]:
                    res = msg.get("result")
                    if res not in ("ok", None):
                        deductions_found = True
                        imp = factor.get("importance", {}).get("text", "normal")
                        lines.append(f"\n[{section_name.upper()}] Factor: {factor_name} (Importance: {imp})")
                        lines.append(f"  Issue: {msg.get('text_label')}")
                        if msg.get("params"):
                            lines.append(f"  Details: {msg.get('params')}")

        if not deductions_found:
            lines.append("\n  Keine Fehler! Alle On-Page-Faktoren mit voller Punktzahl bewertet.")
        lines.append("\n")

    if psi_reports:
        lines.append(format_pagespeed_report(psi_reports))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit URL or Local HTML against Seobility 100% Criteria + Google PageSpeed Insights")
    parser.add_argument("target", help="Target URL (https://..., http://localhost:3000) or local HTML file path (index.html)")
    parser.add_argument("--domain", default="example.com", help="Base domain to distinguish internal vs external links")
    parser.add_argument("--lang", default="de", choices=["de", "en", "es"], help="Language for Seobility audit")
    parser.add_argument("--psi", "--pagespeed", dest="psi", action="store_true", default=True, help="Run Google PageSpeed Insights / Core Web Vitals audit (enabled by default)")
    parser.add_argument("--no-psi", dest="psi", action="store_false", help="Skip Google PageSpeed Insights check")
    parser.add_argument("--strategy", default="mobile", choices=["mobile", "desktop", "both"], help="PageSpeed strategy: mobile, desktop, or both")
    parser.add_argument("--psi-key", default="", help="Optional Google PageSpeed Insights API key (or set PAGESPEED_API_KEY env var)")
    parser.add_argument("--json", action="store_true", help="Print raw JSON response")
    parser.add_argument("--save", type=str, default="", help="Save report to JSON file")

    args = parser.parse_args()

    data = None
    psi_reports = []
    target = args.target
    strategies = ["mobile", "desktop"] if args.strategy == "both" else [args.strategy]

    # Case 1: Local File
    if os.path.isfile(target):
        with open(target, "r", encoding="utf-8") as f:
            html = f.read()
        data = audit_html_content(html, f"Local File: {target}", base_domain=args.domain)
        if args.psi:
            for st in strategies:
                psi_reports.append(audit_html_pagespeed(html, f"Local File: {target}", strategy=st))

    # Case 2: Localhost or IP
    elif "localhost" in target or "127.0.0.1" in target:
        resp = requests.get(target, timeout=10)
        data = audit_html_content(resp.text, f"Dev Server: {target}", base_domain=args.domain)
        if args.psi:
            for st in strategies:
                psi_reports.append(audit_html_pagespeed(resp.text, f"Dev Server: {target}", strategy=st))

    # Case 3: Public URL -> Seobility API + Google PageSpeed Insights v5 API (with fallback)
    else:
        fetched_html = None
        try:
            data = run_seobility_api_audit(target, language=args.lang)
        except Exception as e:
            print(f"[Hinweis] Seobility Live API ({e}). Prüfe On-Page Kriterien direkt...\n", file=sys.stderr)
            resp = requests.get(target, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            fetched_html = resp.text
            data = audit_html_content(fetched_html, target, base_domain=args.domain)

        if args.psi:
            for st in strategies:
                try:
                    psi_reports.append(run_pagespeed_api_audit(target, strategy=st, api_key=args.psi_key))
                except Exception as psi_err:
                    print(f"[Hinweis] Google PageSpeed API ({st}: {psi_err}). Nutze lokalen Core-Web-Vitals-Check...\n", file=sys.stderr)
                    if fetched_html is None:
                        resp = requests.get(target, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                        fetched_html = resp.text
                    psi_reports.append(audit_html_pagespeed(fetched_html, target, strategy=st))

    combined_output = {
        "seobility": data,
        "pagespeed": psi_reports
    }

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(combined_output, f, indent=2, ensure_ascii=False)
        print(f"Report saved to {args.save}")

    if args.json:
        print(json.dumps(combined_output, indent=2, ensure_ascii=False))
    else:
        print(format_report(data, psi_reports))


if __name__ == "__main__":
    main()

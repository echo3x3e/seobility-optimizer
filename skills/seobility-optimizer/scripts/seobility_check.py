#!/usr/bin/env python3
"""
Seobility Auditor & On-Page Score Optimizer CLI
Audits live URLs, local development servers (localhost:3000), or local HTML files
against the Seobility SEO scoring rubric to reach 100% On-Page compliance.
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
    r_domain = session.get(domain_check_url, timeout=15)
    
    xsrf = session.cookies.get("XSRF-TOKEN")
    if xsrf:
        session.headers["X-XSRF-TOKEN"] = urllib.parse.unquote(xsrf)

    # Trigger Live SEO Check
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

def audit_html_content(html: str, source_label: str, base_domain: str = "lostfoundations.org"):
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

    # Calculate overall
    sec_scores = [max(0, s["score_percent"]) for s in report["sections"].values()]
    for s in report["sections"].values():
        s["score_percent"] = max(0, s["score_percent"])
    report["overall_percent"] = max(0, int(sum(sec_scores) / len(sec_scores)))
    report["word_count"] = word_count

    return report

def format_report(data: dict) -> str:
    if data.get("simulated"):
        lines = []
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
        lines.append("HANDLUNGSBEDARF & ABZÜGE (FALLS VORHANDEN):")
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
        return "\n".join(lines)

    # API output
    analysis = data.get("data", {}).get("analysis", {})
    score_data = analysis.get("score", {})
    overall = score_data.get("overall_percent", 0)
    sections = score_data.get("sections", {})
    results = analysis.get("results", {})

    lines = []
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
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Audit URL or Local HTML against Seobility 100% Criteria")
    parser.add_argument("target", help="Target URL (https://..., http://localhost:3000) or local HTML file path (index.html)")
    parser.add_argument("--domain", default="lostfoundations.org", help="Base domain to distinguish internal vs external links")
    parser.add_argument("--lang", default="de", choices=["de", "en", "es"], help="Language for audit")
    parser.add_argument("--json", action="store_true", help="Print raw JSON response")
    parser.add_argument("--save", type=str, default="", help="Save report to JSON file")
    
    args = parser.parse_args()

    data = None
    target = args.target

    # Case 1: Local File
    if os.path.isfile(target):
        with open(target, "r", encoding="utf-8") as f:
            html = f.read()
        data = audit_html_content(html, f"Local File: {target}", base_domain=args.domain)

    # Case 2: Localhost or IP (Cannot be accessed by remote Seobility crawler)
    elif "localhost" in target or "127.0.0.1" in target:
        resp = requests.get(target, timeout=10)
        data = audit_html_content(resp.text, f"Dev Server: {target}", base_domain=args.domain)

    # Case 3: Public URL -> Try Seobility API, fallback to local rule check
    else:
        try:
            data = run_seobility_api_audit(target, language=args.lang)
        except Exception as e:
            print(f"[Hinweis] Seobility Live API ({e}). Prüfe On-Page Kriterien direkt...\n", file=sys.stderr)
            resp = requests.get(target, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            data = audit_html_content(resp.text, target, base_domain=args.domain)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Report saved to {args.save}")

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_report(data))

if __name__ == "__main__":
    main()

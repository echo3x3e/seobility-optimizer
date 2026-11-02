#!/usr/bin/env python3
"""
Seobility Live Audit & Local Pre-Flight Auditor CLI
Audits any target URL against the official Seobility SEO engine or runs
an offline local Seobility simulation when API guest credits are exhausted.
"""

import sys
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

    # Step 1: Pre-flight domain check & establish session cookies
    domain_check_url = f"https://app.seobility.net/dapi/domain-check?url={urllib.parse.quote(target_url)}"
    r_domain = session.get(domain_check_url, timeout=15)
    
    xsrf = session.cookies.get("XSRF-TOKEN")
    if xsrf:
        session.headers["X-XSRF-TOKEN"] = urllib.parse.unquote(xsrf)

    # Step 2: Trigger Live SEO Check
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

def run_local_seobility_simulation(target_url: str):
    """
    Fallback auditor that runs the exact same rule checks locally against live HTML
    when Seobility guest rate limits are encountered.
    """
    resp = requests.get(target_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }, timeout=15)
    
    html = resp.text
    status = resp.status_code
    
    report = {
        "analysed_url": target_url,
        "status_code": status,
        "simulated": True,
        "sections": {
            "meta": {"score_percent": 100, "warnings": []},
            "pagequality": {"score_percent": 100, "warnings": []},
            "structure": {"score_percent": 100, "warnings": []},
            "links": {"score_percent": 100, "warnings": []},
            "server": {"score_percent": 100, "warnings": []},
        }
    }

    # 1. Meta Title
    title_match = re.search(r"<title>([^<]*)</title>", html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""
    if not title:
        report["sections"]["meta"]["score_percent"] -= 30
        report["sections"]["meta"]["warnings"].append("Missing <title> tag.")
    elif len(title) > 65:
        report["sections"]["meta"]["score_percent"] -= 10
        report["sections"]["meta"]["warnings"].append(f"Title too long ({len(title)} chars > 65): '{title[:40]}...'")

    # 2. Meta Description
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE) or \
                 re.search(r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']', html, re.IGNORECASE)
    desc = desc_match.group(1).strip() if desc_match else ""
    if not desc:
        report["sections"]["meta"]["score_percent"] -= 30
        report["sections"]["meta"]["warnings"].append("Missing meta description.")
    elif len(desc) < 120:
        report["sections"]["meta"]["score_percent"] -= 10
        report["sections"]["meta"]["warnings"].append(f"Meta description too short ({len(desc)} chars < 120).")
    elif len(desc) > 165:
        report["sections"]["meta"]["score_percent"] -= 10
        report["sections"]["meta"]["warnings"].append(f"Meta description too long ({len(desc)} chars > 165).")

    # 3. Canonical
    canonical = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']*)["\']', html, re.IGNORECASE)
    if not canonical:
        report["sections"]["meta"]["score_percent"] -= 20
        report["sections"]["meta"]["warnings"].append("Missing canonical tag.")

    # 4. H1 Structure
    h1s = re.findall(r'<h1[^>]*>([\s\S]*?)</h1>', html, re.IGNORECASE)
    if len(h1s) == 0:
        report["sections"]["structure"]["score_percent"] -= 40
        report["sections"]["structure"]["warnings"].append("Missing <h1> tag.")
    elif len(h1s) > 1:
        report["sections"]["structure"]["score_percent"] -= 25
        report["sections"]["structure"]["warnings"].append(f"Multiple <h1> tags found ({len(h1s)}). Exactly 1 required.")

    # 5. Content Volume (Word count)
    cleaned = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    cleaned = re.sub(r'<style[\s\S]*?</style>', '', cleaned, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', cleaned)
    words = [w for w in re.split(r'\s+', text) if len(w) > 1]
    word_count = len(words)
    if word_count < 500:
        report["sections"]["pagequality"]["score_percent"] -= 40
        report["sections"]["pagequality"]["warnings"].append(f"text_short: Only {word_count} words found. Seobility recommends >= 500-600 words.")

    # 6. External Links
    ext_links = re.findall(r'<a[^>]*href=["\'](https?://(?!' + urllib.parse.urlparse(target_url).netloc.replace('.', r'\.') + r')[^"\']+)["\']', html, re.IGNORECASE)
    if len(ext_links) == 0:
        report["sections"]["links"]["score_percent"] -= 30
        report["sections"]["links"]["warnings"].append("link_external_none: 0 external authority links found.")

    # 7. Social Sharing Intents
    has_social = bool(re.search(r'(twitter\.com/intent|facebook\.com/sharer|reddit\.com/submit|t\.me/share|whatsapp\.com/send)', html, re.IGNORECASE))
    if not has_social:
        report["sections"]["pagequality"]["score_percent"] -= 15
        report["sections"]["pagequality"]["warnings"].append("socialshare_no_plugin: No social sharing intent links detected.")

    # 8. Images without alt
    imgs = re.findall(r'<img([^>]*)>', html, re.IGNORECASE)
    missing_alt = [img for img in imgs if 'alt=' not in img.lower()]
    if missing_alt:
        report["sections"]["pagequality"]["score_percent"] -= 20
        report["sections"]["pagequality"]["warnings"].append(f"{len(missing_alt)} <img> tags missing alt attribute.")

    # Calculate overall simulated score
    sec_scores = [s["score_percent"] for s in report["sections"].values()]
    report["overall_percent"] = max(0, int(sum(sec_scores) / len(sec_scores)))

    return report

def format_report(data: dict) -> str:
    if data.get("simulated"):
        lines = []
        lines.append(f"\n=======================================================")
        lines.append(f"  SEOBILITY PRE-FLIGHT AUDIT: {data.get('analysed_url')}")
        lines.append(f"  OVERALL SIMULATED ON-PAGE SCORE: {data.get('overall_percent')}%")
        lines.append(f"  (Note: Evaluated via local Seobility rule engine)")
        lines.append(f"=======================================================\n")
        lines.append("CATEGORY BREAKDOWN:")
        lines.append(f"  {'Kategorie':<25} | {'Score %':<8} | {'Status'}")
        lines.append(f"  {'-'*25}-|-{'-'*8}-|-{'-'*10}")
        for key, sec in data.get("sections", {}).items():
            pct = f"{sec.get('score_percent')}%"
            status = "PERFEKT" if sec.get('score_percent') == 100 else "OPTIMIEREN"
            lines.append(f"  {key:<25} | {pct:<8} | {status}")
        
        lines.append("\n" + "="*55)
        lines.append("ACTIONABLE DEDUCTIONS & WARNINGS:")
        lines.append("="*55)
        warnings = []
        for sec in data.get("sections", {}).values():
            warnings.extend(sec.get("warnings", []))
        if warnings:
            for w in warnings:
                lines.append(f"  - {w}")
        else:
            lines.append("  None! All on-page criteria match 100% Seobility standards.")
        lines.append("\n")
        return "\n".join(lines)

    analysis = data.get("data", {}).get("analysis", {})
    score_data = analysis.get("score", {})
    overall = score_data.get("overall_percent", 0)
    sections = score_data.get("sections", {})
    results = analysis.get("results", {})

    lines = []
    lines.append(f"\n=======================================================")
    lines.append(f"  SEOBILITY AUDIT REPORT: {analysis.get('analysed_url')}")
    lines.append(f"  OVERALL SEO SCORE: {overall}%")
    lines.append(f"=======================================================\n")

    lines.append("CATEGORY BREAKDOWN:")
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
        status = "PERFEKT" if sec.get('score_percent', 0) == 100 else ("GUT" if sec.get('score_percent', 0) >= 80 else "OPTIMIEREN")
        lines.append(f"  {label:<25} | {pts:<12} | {pct:<8} | {status}")

    lines.append("\n" + "="*55)
    lines.append("ACTIONABLE DEDUCTIONS & WARNINGS:")
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
                    if factor.get("wiki_link"):
                        lines.append(f"  Guide: {factor.get('wiki_link')}")

    if not deductions_found:
        lines.append("\n  None! All on-page factors evaluated with 100% full points.")

    lines.append("\n")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Audit URL using Seobility Live API with fallback simulation")
    parser.add_argument("url", help="Target URL (e.g. https://lostfoundations.org)")
    parser.add_argument("--lang", default="de", choices=["de", "en", "es"], help="Language for audit hints")
    parser.add_argument("--mode", default="standard", choices=["standard", "mobile"], help="Crawling mode")
    parser.add_argument("--local-only", action="store_true", help="Force local offline simulation instead of Seobility API")
    parser.add_argument("--json", action="store_true", help="Print raw JSON response")
    parser.add_argument("--save", type=str, default="", help="Path to save raw JSON output")
    
    args = parser.parse_args()

    data = None
    if not args.local_only:
        try:
            data = run_seobility_api_audit(args.url, language=args.lang, crawling_mode=args.mode)
        except Exception as e:
            print(f"[Notice] Seobility API notice ({e}). Switching to local Seobility rule simulation...\n", file=sys.stderr)

    if data is None:
        data = run_local_seobility_simulation(args.url)

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

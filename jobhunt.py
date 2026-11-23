#!/usr/bin/env python3
"""Public LinkedIn job search with CSV and optional Gmail report."""
import argparse
import csv
import html
import os
import random
import smtplib
import ssl
import sys
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
KEYWORDS = ["Site Reliability Engineer", "DevOps Support", "Data Support Engineer", "L3 Production Support"]
FIELDS = ["search_keyword", "title", "company", "location", "posted", "url"]


def parse_jobs(markup, keyword):
    soup = BeautifulSoup(markup, "html.parser")
    jobs = []
    for card in soup.select("li"):
        link = card.select_one("a.base-card__full-link")
        if not link or not link.get("href"):
            continue

        def value(selector):
            element = card.select_one(selector)
            return element.get_text(" ", strip=True) if element else ""

        parts = urlsplit(link["href"])
        date = card.select_one("time")
        jobs.append({
            "search_keyword": keyword,
            "title": value(".base-search-card__title"),
            "company": value(".base-search-card__subtitle"),
            "location": value(".job-search-card__location"),
            "posted": date.get("datetime", "") if date else "",
            "url": urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", "")),
        })
    return jobs


def search_jobs(keywords, location, limit, days, pages, delay):
    results, seen = [], set()
    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
        for keyword in keywords:
            count = 0
            for page in range(pages):
                if count >= limit:
                    break
                params = {"keywords": keyword, "location": location, "start": page * 25}
                if days:
                    params["f_TPR"] = f"r{days * 86400}"
                try:
                    response = session.get(URL, params=params, timeout=20)
                    if response.status_code == 429:
                        print("LinkedIn returned HTTP 429; stopping without retrying.", file=sys.stderr)
                        return results
                    response.raise_for_status()
                except requests.RequestException as exc:
                    print(f"Search failed for {keyword}: {exc}", file=sys.stderr)
                    break
                new = 0
                for job in parse_jobs(response.text, keyword):
                    if job["url"] and job["url"] not in seen:
                        seen.add(job["url"])
                        results.append(job)
                        count += 1
                        new += 1
                        if count >= limit:
                            break
                if not new:
                    break
                if page + 1 < pages:
                    time.sleep(random.uniform(delay, delay + 2))
            print(f"{keyword}: {count} new results")
            if keyword != keywords[-1]:
                time.sleep(random.uniform(delay, delay + 2))
    return results


def save_csv(jobs, path):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(jobs)


def html_report(jobs, location, days):
    esc = lambda s: html.escape(str(s or ""), quote=True)
    rows = []
    for job in jobs:
        cells = "".join(f'<td style="border:1px solid #ddd;padding:8px">{esc(job[key])}</td>'
                        for key in ("title", "company", "location", "posted", "search_keyword"))
        rows.append(f'<tr>{cells}<td style="border:1px solid #ddd;padding:8px"><a href="{esc(job["url"])}">View job</a></td></tr>')
    headings = "".join(f"<th>{heading}</th>" for heading in
                       ("Title", "Company", "Location", "Posted", "Search term", "Link"))
    return (f'<html><body style="font-family:Arial,sans-serif"><h2>Job Search Report</h2>'
            f'<p>Location: {esc(location)} | Last {days} days | {len(jobs)} unique results</p>'
            f'<table style="border-collapse:collapse"><thead><tr>{headings}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table><p>CSV attached.</p></body></html>')


def send_email(jobs, path, location, days, recipient):
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    if not user or not password:
        raise RuntimeError("Set SMTP_USER and SMTP_PASSWORD in the environment (never in source code).")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    message = EmailMessage()
    message["Subject"] = f"Pune job report: {len(jobs)} jobs ({datetime.now():%d %b %Y})"
    message["From"] = user
    message["To"] = recipient
    message.set_content(f"Found {len(jobs)} jobs. See attached CSV or HTML version.")
    message.add_alternative(html_report(jobs, location, days), subtype="html")
    message.add_attachment(path.read_bytes(), maintype="text", subtype="csv", filename=path.name)
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30, context=context) as smtp:
            smtp.login(user, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls(context=context)
            smtp.login(user, password)
            smtp.send_message(message)
    print(f"Email sent to {recipient}")


def main():
    parser = argparse.ArgumentParser(description="Export public LinkedIn jobs and optionally email a report")
    parser.add_argument("-k", "--keywords", action="append", help="Repeat for multiple terms")
    parser.add_argument("-l", "--location", default="Pune, Maharashtra, India")
    parser.add_argument("-n", "--limit", type=int, default=50, help="Per-keyword maximum")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("-o", "--output")
    parser.add_argument("--email", action="store_true")
    parser.add_argument("--recipient", default="shubhamhavale0@gmail.com")
    args = parser.parse_args()
    if args.limit < 1 or args.max_pages < 1 or args.days < 0 or args.delay < 0:
        parser.error("Invalid limit, max-pages, days or delay")
    jobs = search_jobs(args.keywords or KEYWORDS, args.location, args.limit,
                       args.days, args.max_pages, args.delay)
    path = Path(args.output or f"linkedin_jobs_{datetime.now():%Y%m%d_%H%M}.csv")
    save_csv(jobs, path)
    print(f"Saved {len(jobs)} jobs to {path}")
    print(f'{"Title":35} | {"Company":24} | {"Location":25} | Posted')
    for job in jobs:
        print(f'{job["title"][:35]:35} | {job["company"][:24]:24} | {job["location"][:25]:25} | {job["posted"]}')
    if args.email:
        if jobs:
            send_email(jobs, path, args.location, args.days, args.recipient)
        else:
            print("No results; email skipped.", file=sys.stderr)


if __name__ == "__main__":
    main()

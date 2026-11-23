# LinkedIn Job Hunt — Pune

A small Python CLI that searches LinkedIn's public guest job listings, prints a terminal table, exports CSV (Excel-compatible), and optionally sends an HTML table with a CSV attachment via Gmail SMTP.

> **Caution:** LinkedIn can return HTTP 429 or change its public HTML. Automated collection may be restricted by LinkedIn's terms. Keep request volumes low; do not bypass rate limits. This tool is not affiliated with LinkedIn. It is not guaranteed to retrieve jobs or deliver email.

## Features

- Searches four default keywords: Site Reliability Engineer, DevOps Support, Data Support Engineer, L3 Production Support
- Pune location default; customizable keywords, date window, result limits and page count
- Removes duplicate job URLs within each run
- Exports UTF-8 CSV and prints a terminal table
- Optional Gmail SMTP email with HTML table and CSV attachment
- Stops on HTTP 429; skips email if no jobs are found

## Requirements

Python 3.10+ and pip. On macOS:

```bash
git clone https://github.com/ShubhamDevops07/job_hunt_linkedin.git
cd job_hunt_linkedin
python3 -m pip install -r requirements.txt
python3 jobhunt.py --days 7 --limit 50
```

Examples:

```bash
python3 jobhunt.py -k "Site Reliability Engineer" -l "Pune, Maharashtra, India" -n 25 --days 7
python3 jobhunt.py --days 1 --max-pages 1 --email
python3 jobhunt.py --help
```

CSV files are generated in the current directory and ignored by Git.

## Gmail authentication — create an App Password

**Never use your regular Gmail password, share an App Password in chat, or commit credentials.** If an App Password has been exposed, revoke it and create a new one.

1. Open [Google Account Security](https://myaccount.google.com/security) and enable **2-Step Verification**.
2. Open [Google App Passwords](https://myaccount.google.com/apppasswords). Availability depends on your Google account and administrator policies.
3. Create an App Password for this script. Google displays a 16-character password once; copy it privately.
4. Set environment variables in your local terminal, not in the repository:

```bash
export SMTP_USER="your-address@gmail.com"
read -s "SMTP_PASSWORD?Paste Gmail App Password: "
echo
export SMTP_PASSWORD
python3 jobhunt.py --email --recipient "your-address@gmail.com"
```

Use `SMTP_HOST=smtp.gmail.com` and `SMTP_PORT=465` (defaults). If using port 587, the script uses STARTTLS. Never paste the App Password into source code, README, shell history, GitHub issues or Actions logs.

For a scheduled Mac run, prefer macOS Keychain instead of a plaintext environment file. A sample wrapper is included as `run_jobhunt.sh.example`; copy it to `run_jobhunt.sh`, customize its paths, and keep that file untracked.

## Schedule hourly, 8 AM–4 PM India time

This means nine runs per day (08:00 through 16:00 inclusive). **Hourly scraping may trigger HTTP 429; consider reducing frequency or switching to an authorized jobs API.** Your Mac must be awake and connected; cron does not replay runs missed during sleep.

1. Save the new App Password in Keychain (you will be prompted):

```bash
security add-generic-password -a "your-address@gmail.com" -s "jobhunt-gmail" -w
```

2. Copy the example runner and edit its `PROJECT_DIR` and `SMTP_USER` values:

```bash
cp run_jobhunt.sh.example run_jobhunt.sh
chmod 700 run_jobhunt.sh
./run_jobhunt.sh
```

3. Find the absolute path with `pwd`, then use `crontab -e` to add the following line, replacing `/ABSOLUTE/PATH` with your directory:

```cron
0 8-16 * * * /ABSOLUTE/PATH/run_jobhunt.sh >> /ABSOLUTE/PATH/jobhunt.log 2>&1
```

Check `crontab -l` and `tail -n 50 jobhunt.log`. The cron schedule uses your Mac's local time zone; set it to Asia/Kolkata for IST. The Keychain may require interactive approval the first time; test the runner before relying on unattended execution. macOS `launchd` is preferable for more advanced scheduling.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| HTTP 429 | Stop requesting; wait for the rate limit to clear. Do not bypass it. |
| Zero jobs | Try a narrower keyword; selectors or guest endpoint may have changed. |
| `SMTPAuthenticationError` | Check the account, 2-Step Verification and App Password. |
| `SMTPServerDisconnected` | Verify network access and SSL port 465; try `nc -vz smtp.gmail.com 465`. |
| Cron runs but email fails | Check `jobhunt.log`, Keychain permissions, absolute paths, and Mac sleep. |

## Security

`.gitignore` excludes CSV exports, local secrets, runner scripts, logs, virtual environments and Python caches. **Git ignore rules do not remove secrets already committed**; revoke exposed credentials and remove them from history as needed.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests use sample HTML and mocked network/SMTP; they do not verify live LinkedIn availability or real email delivery.

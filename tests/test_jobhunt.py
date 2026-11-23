import unittest
from unittest.mock import patch, MagicMock
import jobhunt


class JobHuntTests(unittest.TestCase):
    def test_parse_jobs(self):
        markup = """<li><a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/123?tracking=abc"></a>
        <h3 class="base-search-card__title">SRE Engineer</h3>
        <h4 class="base-search-card__subtitle">Example Inc</h4>
        <span class="job-search-card__location">Pune</span>
        <time datetime="2026-11-23"></time></li>"""
        jobs = jobhunt.parse_jobs(markup, "SRE")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "SRE Engineer")
        self.assertEqual(jobs[0]["url"], "https://www.linkedin.com/jobs/view/123")

    def test_html_escapes_content(self):
        result = jobhunt.html_report([{
            "title": "<script>", "company": "A&B", "location": "Pune",
            "posted": "today", "search_keyword": "SRE", "url": "https://example.com"
        }], "Pune", 7)
        self.assertIn("&lt;script&gt;", result)
        self.assertNotIn("<script>", result)

    @patch("jobhunt.requests.Session")
    def test_rate_limit_stops(self, session_type):
        response = MagicMock(status_code=429)
        session_type.return_value.__enter__.return_value.get.return_value = response
        self.assertEqual(jobhunt.search_jobs(["SRE"], "Pune", 5, 1, 1, 0), [])


if __name__ == "__main__":
    unittest.main()

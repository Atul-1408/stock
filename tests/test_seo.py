"""SEO behaviour: robots.txt, sitemap.xml, noindex on API, real 404s."""
import os
import tempfile

import app as flask_app

app = flask_app.app


def client():
    return app.test_client()


def test_robots_blocks_private_areas_and_lists_sitemap():
    body = client().get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /api/" in body and "Disallow: /dashboard" in body
    assert "Sitemap: " in body and body.strip().endswith("/sitemap.xml")


def test_sitemap_lists_only_public_pages():
    xml = client().get("/sitemap.xml").get_data(as_text=True)
    assert "<loc>" in xml and "/signup" in xml
    assert "/dashboard" not in xml and "/api" not in xml


def test_api_responses_are_noindex():
    assert client().get("/api/health").headers.get("X-Robots-Tag") == "noindex, nofollow"


def test_unknown_url_is_a_real_404_and_known_page_is_200(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write('<link rel="canonical" href="__SITE_URL__/">')
        monkeypatch.setattr(app, "static_folder", d)
        c = client()
        assert c.get("/signup").status_code == 200
        assert c.get("/definitely-not-a-page").status_code == 404
        assert "__SITE_URL__" not in c.get("/").get_data(as_text=True)  # token replaced

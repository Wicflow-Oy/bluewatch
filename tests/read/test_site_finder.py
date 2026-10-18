import httpx

from bluewatch.models import Registry
from bluewatch.read.site_finder import find_site
from tests.read.fakes import FakeWeb, html

SEABER = Registry(country="FI", id="2855258-7", name="Seaber Oy", municipality="Helsinki")


def test_the_registry_website_comes_first_and_www_is_tried():
    clewat = Registry(country="FI", id="2896110-2", name="Clewat Oy", website="www.clewat.com")
    web = FakeWeb({"https://www.clewat.com/": html("Clewat", "<p>Clean water for the Baltic Sea.</p>")})
    site = find_site(clewat, get=web)
    assert site.how == "registry website field" and site.confident and site.page.ok
    assert web.calls == ["https://clewat.com/", "https://www.clewat.com/"]


def test_a_failing_registered_site_is_returned_with_its_reason():
    tls = httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    clewat = Registry(country="FI", id="2896110-2", name="Clewat Oy", website="www.clewat.com")
    site = find_site(clewat, get=FakeWeb({"https://clewat.com/": tls, "https://www.clewat.com/": tls}))
    assert not site.page.ok and site.page.error == "the site's TLS certificate fails"


def test_a_guessed_site_with_the_companys_own_id_attaches():
    web = FakeWeb({"https://seaber.com/": html("Seaber", "<p>Maritime freight software.</p><p>Y-tunnus 2855258-7</p>")})
    site = find_site(SEABER, get=web)
    assert site.confident and "registry ID" in site.ownership


def test_t10_a_foreign_namesake_is_rejected():
    florida = html("Seaber Inc.", "<p>Seaber Inc. pool supplies, proudly serving Miami, Florida.</p>")
    assert find_site(SEABER, get=FakeWeb({"https://seaber.com/": florida})) is None


def test_a_local_domain_or_the_registered_municipality_attaches_with_less_confidence():
    local = find_site(SEABER, get=FakeWeb({"https://seaber.fi/": html("Seaber", "<p>Seaber Oy plans freight.</p>")}))
    assert local and not local.confident and ".fi" in local.ownership
    town = html("Seaber", "<p>Seaber Oy, Lauttasaarentie 1, Helsinki</p>")
    assert "Helsinki" in find_site(SEABER, get=FakeWeb({"https://seaber.io/": town})).ownership


def test_a_page_showing_another_companys_id_is_rejected():
    atlan = html("Seaber", "<p>Seaber is a product of Atlan Studio Oy, Y-tunnus 3480010-2.</p>")
    assert find_site(SEABER, get=FakeWeb({"https://seaber.fi/": atlan})) is None

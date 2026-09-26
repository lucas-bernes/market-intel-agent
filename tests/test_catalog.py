import json

import pytest

from market_intel import catalog
from market_intel.catalog import (
    CatalogItem,
    SourceError,
    build_report,
    fetch_aimlapi,
    fetch_fal,
    fetch_piapi,
    fetch_replicate,
    fetch_runware,
    mark_notified,
    pending_events,
    price_change_pct,
    scan_platform,
    untracked_digest,
)
from market_intel.promo import find_promo, stale_hint


def _item(endpoint_id, price=None, family="Fam", title=None, deprecated=False, note=None):
    return CatalogItem(endpoint_id, title or endpoint_id, family, "2026-09-01T00:00:00Z", price, deprecated, note)


def _kinds(result):
    return sorted(e["kind"] for e in result.events)


# ---- promotional language ----------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        # Real texts seen on fal.ai and Runware on 2026-09-26.
        ("Note: these are promotional launch rates, 50% off for a limited time. The discount ends September 30, after which 480p is $0.05/second.", True),
        ("Currently 20% off for February 2026!", True),
        ("Video costs $0.1 per second.", False),
        ("Volume discounts are available on enterprise plans.", False),  # permanent, tiered: not a promotion
        ("Contact our sales team.", False),
        (None, False),
    ],
)
def test_find_promo(text, expected):
    assert (find_promo(text) is not None) is expected


def test_stale_hint_flags_a_past_month_only():
    from datetime import date

    today = date(2026, 9, 26)
    assert stale_hint("Currently 20% off for February 2026!", today) is not None
    assert stale_hint("Sale runs through September 2026", today) is None
    assert stale_hint("50% off, ends September 30", today) is None


# ---- price comparison ---------------------------------------------------------

@pytest.mark.parametrize(
    "old, new, expected",
    [
        ("$0.10/s", "$0.10 per second", 0.0),            # only the wording changed
        ("$0.10/s", "$0.08/s", 20.0),
        ("$0.025/s at 480p, $0.04/s at 768p", "$0.05/s at 480p, $0.08/s at 768p", 100.0),
        ("$0.10/s", "$0.10/s at 720p and $0.20/s at 1080p", None),  # not comparable one-to-one
        (None, "$0.10/s", None),
    ],
)
def test_price_change_pct(old, new, expected):
    result = price_change_pct(old, new)
    assert result == expected if expected is None else result == pytest.approx(expected)


# ---- scan / diff --------------------------------------------------------------

def test_baseline_records_everything_but_reports_only_promotions():
    result = scan_platform("fal", [_item("a"), _item("b", price="$0.10/s, 50% off for a limited time")])

    assert result.baseline is True
    assert _kinds(result) == ["promo"]  # existing promotions are time-limited, so they are reported at once
    assert len(untracked_digest("fal", set())) == 1


def test_a_new_endpoint_after_the_baseline_is_reported():
    scan_platform("fal", [_item("a"), _item("b")])
    result = scan_platform("fal", [_item("a"), _item("b"), _item("c", price="$0.2/s")])

    assert _kinds(result) == ["new"]
    assert result.events[0]["endpoint_id"] == "c"


def test_price_change_is_reported_with_both_prices():
    scan_platform("fal", [_item("a", price="$0.10/s")])
    result = scan_platform("fal", [_item("a", price="$0.08/s")])

    [event] = result.events
    assert event["kind"] == "price_changed"
    assert "$0.10/s" in event["detail"] and "$0.08/s" in event["detail"]


def test_wording_only_change_is_silent():
    scan_platform("fal", [_item("a", price="$0.10/s")])
    assert scan_platform("fal", [_item("a", price="$0.10 per second")]).events == []


def test_a_promotion_appearing_on_a_known_endpoint_is_a_promo_not_a_price_change():
    scan_platform("fal", [_item("a", price="$0.10/s")])
    result = scan_platform("fal", [_item("a", price="$0.05/s, promotional launch rate, 50% off for a limited time")])

    assert _kinds(result) == ["promo"]


def test_gone_only_after_three_consecutive_misses_then_returned():
    scan_platform("fal", [_item("a"), _item("b")])

    assert scan_platform("fal", [_item("b")]).events == []
    assert scan_platform("fal", [_item("b")]).events == []
    assert _kinds(scan_platform("fal", [_item("b")])) == ["gone"]
    assert _kinds(scan_platform("fal", [_item("a"), _item("b")])) == ["returned"]


def test_a_single_miss_is_forgotten_when_the_endpoint_comes_back():
    scan_platform("fal", [_item("a"), _item("b")])
    scan_platform("fal", [_item("b")])           # a missing once (API hiccup)
    scan_platform("fal", [_item("a"), _item("b")])
    scan_platform("fal", [_item("b")])
    assert scan_platform("fal", [_item("b")]).events == []  # the counter restarted, so still not "gone"


def test_an_implausibly_small_scan_is_rejected_and_changes_nothing():
    scan_platform("fal", [_item(str(i)) for i in range(10)])

    with pytest.raises(SourceError):
        scan_platform("fal", [_item("0")])

    assert pending_events() == []
    assert len(untracked_digest("fal", set())) == 1  # rows untouched, none marked gone


def test_deprecated_flag_is_reported_once():
    scan_platform("runware", [_item("x", family="openai")])
    first = scan_platform("runware", [_item("x", family="openai", deprecated=True, note="status: deprecated, deactivates 2026-09-24")])
    second = scan_platform("runware", [_item("x", family="openai", deprecated=True, note="status: deprecated, deactivates 2026-09-24")])

    assert _kinds(first) == ["deprecated"] and "2026-09-24" in first.events[0]["detail"]
    assert second.events == []


def test_platforms_do_not_mix():
    scan_platform("fal", [_item("a")])
    result = scan_platform("runware", [_item("a")])

    assert result.baseline is True and result.events == []


# ---- report / notification -----------------------------------------------------

def test_report_is_empty_without_news_and_lists_errors_and_events():
    assert build_report([], {}) == ""

    events = [{"platform": "fal", "endpoint_id": "x/y", "title": "X Y", "kind": "new", "detail": "Fam | 2026-09-20"}]
    report = build_report(events, {"piapi": "SourceError: boom"})

    assert "Source problem — piapi" in report and "### New endpoints (1)" in report and "`x/y`" in report


def test_report_truncates_long_groups():
    events = [{"platform": "fal", "endpoint_id": f"e{i}", "title": f"E{i}", "kind": "new", "detail": None} for i in range(40)]

    report = build_report(events, {})

    assert "and 15 more" in report and report.count("- `fal`") == catalog.MAX_PER_GROUP


def test_events_stay_pending_until_marked_notified():
    scan_platform("fal", [_item("a")])
    scan_platform("fal", [_item("a"), _item("b")])

    assert [e["endpoint_id"] for e in pending_events()] == ["b"]
    assert mark_notified() == 1
    assert pending_events() == []


def test_untracked_digest_groups_by_family_and_skips_tracked_ids():
    scan_platform("fal", [_item("k/1", family="Kling"), _item("k/2", family="Kling"), _item("m/1", family="MiniMax")])

    digest = untracked_digest("fal", {"K/1"})  # case-insensitive match

    assert [(family, count) for family, count, _ in digest] == [("Kling", 1), ("MiniMax", 1)]


# ---- readers (HTTP mocked with the real shapes) ---------------------------------

def _mock_http(monkeypatch, pages):
    monkeypatch.setattr(catalog, "_http", lambda url, limit=0: pages[url])


def test_fetch_fal_reads_every_page_and_flags_deprecated(monkeypatch):
    base = "https://fal.ai/api/models?categories=image-to-video&page="
    row = lambda i, **kw: {"id": f"fal-ai/m{i}/image-to-video", "title": f"M{i}", "modelFamily": "F", "date": "2026-09-01", **kw}
    _mock_http(monkeypatch, {
        base + "1": json.dumps({"items": [row(1, pricingInfoOverride="**$0.10** per second"), row(2, deprecated="True")], "pages": 2}),
        base + "2": json.dumps({"items": [row(3, removed=True)], "pages": 2}),
    })

    items = fetch_fal()

    assert [i.endpoint_id for i in items] == ["fal-ai/m1/image-to-video", "fal-ai/m2/image-to-video", "fal-ai/m3/image-to-video"]
    assert items[0].price_text == "$0.10 per second"  # markdown stripped
    assert [i.deprecated for i in items] == [False, True, True]


def test_fetch_runware_reads_the_embedded_model_objects(monkeypatch):
    page = (
        r'\"air\":\"openai:3@2\",\"name\":\"Sora 2 Pro\",\"creator\":\"openai\",\"status\":\"deprecated\",'
        r'\"deactivatesAt\":\"2026-09-24T00:00:00Z\",\"releasedAt\":\"2025-09-30T00:00:00Z\",'
        r'\"capabilities\":[\"io:text-to-video\",\"io:image-to-video\"],'
        r'\"pricingOverview\":\"Each generation will cost $0.3/s for 720p.\",\"pricingRates\":[]},'
        r'{\"air\":\"x:1@1\",\"name\":\"Text Only\",\"capabilities\":[\"io:text-to-video\"]}'
    )
    _mock_http(monkeypatch, {"https://runware.ai/models": page})

    [item] = fetch_runware()  # the text-to-video-only model is not an image-to-video endpoint

    assert (item.endpoint_id, item.title, item.family) == ("openai:3@2", "Sora 2 Pro", "openai")
    assert item.deprecated is True and "2026-09-24" in item.note
    assert item.price_text == "Each generation will cost $0.3/s for 720p."


def test_fetch_piapi_keeps_video_prices_and_drops_image_models(monkeypatch):
    page = (
        '{"group":"Kling API","link":"https://piapi.ai/kling-api","payg":['
        '{"matrix":{"title":"Video Generation","columns":["V2.5 / 2.6","V3.0"],'
        '"rows":[{"label":"STD","values":["$$0.20/5s","$$0.10/s"]},{"label":"PRO","values":["—","$$0.15/s"]}]}},'
        '{"label":"Video Generation (Turbo)","lines":["3.0 Turbo STD $0.13/s"]}]},'
        '{"group":"Seedream API","link":"https://piapi.ai/seedream","payg":['
        '{"matrix":{"title":"Image Generation","columns":["2K"],"rows":[{"label":"seedream-5","values":["$$0.052"]}]}}]}'
    )
    _mock_http(monkeypatch, {"https://piapi.ai/pricing": page})

    prices = {i.endpoint_id: i.price_text for i in fetch_piapi()}

    assert prices["Kling API/Video Generation V3.0 STD"] == "$0.10/s"
    assert prices["Kling API/Video Generation V3.0 PRO"] == "$0.15/s"
    assert "Kling API/Video Generation V2.5 / 2.6 PRO" not in prices  # an empty cell is not a price
    assert prices["Kling API/Video Generation (Turbo) 3.0 Turbo STD"] == "$0.13/s"
    assert not any("Seedream" in key for key in prices)  # "dream" inside "Seedream" is an image model


def test_fetch_aimlapi_keeps_only_video_generation_models(monkeypatch):
    data = {"data": [
        {"id": "minimax/h3-max", "type": "internal/video-generations/submit", "info": {"name": "MiniMax H3 Max", "developer": "MiniMax", "releasedAt": "2026-08-23"}},
        {"id": "openai/gpt-x", "type": "openai/chat-completions", "info": {"name": "GPT X"}},
    ]}
    _mock_http(monkeypatch, {"https://api.aimlapi.com/models": json.dumps(data)})

    [item] = fetch_aimlapi()

    assert (item.endpoint_id, item.family, item.published_at) == ("minimax/h3-max", "MiniMax", "2026-08-23")


def test_fetch_replicate_keeps_owner_name_links_only(monkeypatch):
    page = '<a href="/bytedance/seedance-2.0">x</a><a href="/collections/image-to-video">c</a><a href="/docs/api">d</a><a href="/alibaba/happyhorse-1.0">y</a>'
    _mock_http(monkeypatch, {"https://replicate.com/collections/image-to-video": page})

    assert [i.endpoint_id for i in fetch_replicate()] == ["alibaba/happyhorse-1.0", "bytedance/seedance-2.0"]

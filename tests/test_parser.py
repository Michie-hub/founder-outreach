
from main import SearchResult, parse_founder_candidate


def test_linkedin_title():
    result = SearchResult(
        title="Scott Cook - Founder at Stealth Startup | LinkedIn",
        url="https://ca.linkedin.com/in/scottcook-cc",
        snippet="Founder working on a new technology startup.",
    )

    candidate = parse_founder_candidate(result)

    assert candidate.name == "Scott Cook"
    assert candidate.company == "Stealth Startup"
    assert candidate.role == "Founder"
    assert candidate.profile_url == result.url
    assert candidate.review_status == "needs_review"


def test_forbes_style_title():
    result = SearchResult(
        title="Greg Smith | Founder & CEO - Thinkific | Forbes",
        url="https://example.com/greg-smith",
        snippet="Greg Smith is the Founder and CEO of Thinkific.",
    )

    candidate = parse_founder_candidate(result)

    assert candidate.name == "Greg Smith"
    assert candidate.company == "Thinkific"
    assert candidate.role == "Founder & CEO"
    assert candidate.profile_url is None


def test_founder_details_in_snippet():
    result = SearchResult(
        title="Meet The Canadian Founder Changing The Future of Computing",
        url=(
            "https://www.threemagazine.com/"
            "meet-the-canadian-founder-changing-the-future-of-computing/"
        ),
        snippet=(
            "As the founder of quantum computing company Xanadu, "
            "entrepreneur Christian Weedbrook is building new machines."
        ),
    )

    candidate = parse_founder_candidate(result)

    assert candidate.name == "Christian Weedbrook"
    assert candidate.company == "Xanadu"
    assert candidate.role == "Founder"


def test_missing_company():
    result = SearchResult(
        title="Scott Cook - Founder | LinkedIn",
        url="https://ca.linkedin.com/in/scottcook-cc",
        snippet="An entrepreneur working in technology.",
    )

    candidate = parse_founder_candidate(result)

    assert candidate.company is None
    assert candidate.name is None
    assert candidate.role == "Founder"
    assert candidate.review_status == "needs_review"


def test_evidence_and_source_are_preserved():
    result = SearchResult(
        title="Founder profile",
        url="https://example.com/profile",
        snippet="This is the original evidence.",
    )

    candidate = parse_founder_candidate(result)

    assert candidate.source_url == result.url
    assert candidate.evidence == result.snippet
    assert candidate.review_status == "needs_review"


import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from database import Base


class FakeDDGS:
    """Simulate search results without accessing the internet."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def text(self, query, max_results=10):
        return [
            {
                "title": "Scott Cook - Founder at Stealth Startup | LinkedIn",
                "href": "https://www.linkedin.com/in/scott-cook-test",
                "body": (
                    "Scott Cook is the founder of Stealth Startup, "
                    "a software startup."
                ),
            }
        ]


@pytest.fixture
def client(monkeypatch):
    # Create an isolated in-memory database for this test.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Replace real database access and web search with test versions.
    main.app.dependency_overrides[main.get_db] = override_get_db
    monkeypatch.setattr(main, "DDGS", FakeDDGS)

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()
    test_engine.dispose()


def test_search_returns_candidates_without_saving(client):
    response = client.post(
        "/founders/search",
        json={
            "country": "Canada",
            "industry": "software",
            "role": "Founder",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["saved_count"] == 0
    assert len(data["results"]) == 1

    saved_response = client.get("/founders")

    assert saved_response.status_code == 200
    assert saved_response.json() == []


def test_repeated_searches_remain_temporary_until_approval(client):
    payload = {
        "country": "Canada",
        "industry": "software",
        "role": "Founder",
    }

    first_response = client.post("/founders/search", json=payload)
    second_response = client.post("/founders/search", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert first_response.json()["saved_count"] == 0
    assert second_response.json()["saved_count"] == 0

    founders = client.get("/founders").json()
    assert founders == []


def test_approving_search_result_saves_it(client):
    search = client.post(
        "/founders/search",
        json={"country": "Canada", "industry": "software", "role": "Founder"},
    )
    candidate = search.json()["results"][0]

    approved = client.post(
        "/founders",
        json={**candidate, "review_status": "approved"},
    )

    assert approved.status_code == 201
    assert approved.json()["review_status"] == "approved"
    saved_founders = client.get("/founders").json()
    assert len(saved_founders) == 1
    assert saved_founders[0]["name"] == "Scott Cook"
    assert saved_founders[0]["company"] == "Stealth Startup"


def create_founder(client):
    response = client.post(
        "/founders",
        json={
            "name": "Scott Cook",
            "company": "Example Startup",
            "role": "Founder",
            "source_url": "https://example.com/scott-cook",
            "evidence": "Founder of Example Startup",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_founder_review_can_be_approved_or_rejected(client):
    founder = create_founder(client)

    approved = client.patch(
        f"/founders/{founder['id']}/review", json={"review_status": "approved"}
    )
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"

    rejected = client.patch(
        f"/founders/{founder['id']}/review", json={"review_status": "rejected"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"


def test_outreach_status_is_validated_and_saved(client):
    founder = create_founder(client)

    response = client.patch(
        f"/founders/{founder['id']}/outreach",
        json={"outreach_status": "meeting_booked"},
    )
    assert response.status_code == 200
    assert client.get("/founders").json()[0]["outreach_status"] == "meeting_booked"

    invalid = client.patch(
        f"/founders/{founder['id']}/outreach",
        json={"outreach_status": "sent"},
    )
    assert invalid.status_code == 422


def test_personalized_outreach_draft_is_saved_and_can_be_edited(client):
    founder = create_founder(client)

    generated = client.post(f"/founders/{founder['id']}/outreach-draft", json={})
    assert generated.status_code == 200
    draft = generated.json()["outreach_draft"]
    assert "Scott" in draft
    assert "Example Startup" in draft
    assert client.get("/founders").json()[0]["outreach_draft"] == draft

    custom_text = "Hi Scott, I liked the product direction at Example Startup."
    edited = client.post(
        f"/founders/{founder['id']}/outreach-draft", json={"draft": custom_text}
    )
    assert edited.status_code == 200
    assert client.get("/founders").json()[0]["outreach_draft"] == custom_text

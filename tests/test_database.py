from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import Founder

def create_test_session():
    """Create a separate in-memory database for testing."""
    engine =  create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    Base.metadata.create_all(bind=engine)
    
    TestSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    
    return TestSessionLocal()

def test_save_founder():
    session  = create_test_session()
    
    founder = Founder(
        name="Scott Cook",
        company="Example Startup",
        role="Founder",
        profile_url="https://www.linkedin.com/in/example",
        source_url="https://example.com/scott-cook",
        evidence="Scotte Cook is the founder of Example Startup",
        review_status="needs_review",
    )
    session.add(founder)
    session.commit()
    session.refresh(founder)

    saved_founder = session.query(Founder).filter_by(
        name="Scott Cook"
    ).first()

    assert saved_founder is not None
    assert saved_founder.company == "Example Startup"
    assert saved_founder.review_status == "needs_review"

    session.close()


def test_database_starts_empty():
    session = create_test_session()

    founders = session.query(Founder).all()

    assert founders == []

    session.close()

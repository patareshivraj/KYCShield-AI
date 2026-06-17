import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import Base, engine

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_upload_and_status(setup_db):
    client = TestClient(app)
    
    # 1. Upload mock files
    # Note: Requires actual dummy files in fixtures for full run
    files = {
        "aadhaar": ("aadhaar.pdf", b"%PDF-1.4 mock", "application/pdf"),
        "pan": ("pan.jpg", b"mock image", "image/jpeg"),
    }
    
    response = client.post("/api/v1/applicants/upload", files=files, data={"external_reference": "test-123"})
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "queued"
    
    job_id = data["job_id"]
    
    # 2. Check Status
    status_resp = client.get(f"/api/v1/jobs/{job_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in ["queued", "processing", "analyzed"]

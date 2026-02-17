
import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000/api/tracker"

def test_tracker_api():
    print("Testing Target Tracker API...")
    
    # 1. Add a company to tracking
    # Assuming company_id 1 exists (it should from seeding) or we can try a random one
    company_id = 999  # Using a likely non-existent ID for universe, but tracker doesn't strictly validate existence in universe for this test unless we mock it, wait, it does. 
    # Actually, let's use a dummy ID and hope the DB constraints aren't too strict for this integration test, 
    # OR better, if we rely on universe data, we might fail if seed data isn't there.
    # The models show `company_id` is an Integer, but no foreign key constraint *in the database schema definitions* for TrackedCompany to CompanyModel (it's logical FK).
    # Wait, TrackedCompany definition: `company_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)` - No ForeignKey("companies.id").
    # So we can use any ID.
    
    print("\n[1/5] Testing POST /add...")
    payload = {
        "company_id": 101, 
        "priority": "high", 
        "tags": ["api-test", "demo"], 
        "notes": "Added via API test"
    }
    try:
        response = requests.post(f"{BASE_URL}/add", json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Success! Response: {data}")
        tracked_id = data["tracked_id"]
    except Exception as e:
        print(f"Failed: {e}")
        if response:
            print(f"Response content: {response.text}")
        return

    # 2. List companies
    print("\n[2/5] Testing GET /companies...")
    try:
        response = requests.get(f"{BASE_URL}/companies", params={"priority": "high"})
        response.raise_for_status()
        companies = response.json()
        print(f"Success! Found {len(companies)} companies")
        found = any(c['id'] == tracked_id for c in companies)
        print(f"Newly added company found in list: {found}")
    except Exception as e:
        print(f"Failed: {e}")

    # 3. Add a note
    print("\n[3/5] Testing POST /note...")
    note_payload = {
        "note_text": "This is a test note",
        "created_by": "TestUser",
        "note_type": "research"
    }
    try:
        response = requests.post(f"{BASE_URL}/company/{tracked_id}/note", json=note_payload)
        response.raise_for_status()
        print(f"Success! Response: {response.json()}")
    except Exception as e:
        print(f"Failed: {e}")

    # 4. Get Data Detail
    print("\n[4/5] Testing GET /company/{id}...")
    try:
        response = requests.get(f"{BASE_URL}/company/{tracked_id}")
        response.raise_for_status()
        detail = response.json()
        print(f"Success! Retrieved details for company {detail['tracking']['company_id']}")
        print(f"Notes count: {len(detail['notes'])}")
    except Exception as e:
        print(f"Failed: {e}")

    # 5. Remove
    print("\n[5/5] Testing DELETE /company/{id}...")
    try:
        response = requests.delete(f"{BASE_URL}/company/{tracked_id}", params={"hard_delete": "true"})
        response.raise_for_status()
        print(f"Success! Response: {response.json()}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    # Wait a bit for server to be definitely ready if checked immediately after start
    time.sleep(1)
    test_tracker_api()

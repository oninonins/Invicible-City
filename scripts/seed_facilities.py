import urllib.request
import json

FACILITIES = [
    {"name": "RSUPN Dr. Cipto Mangunkusumo", "facility_type": "Hospital", "lat": -6.1969, "lng": 106.8465},
    {"name": "SMA Negeri 8 Jakarta", "facility_type": "School", "lat": -6.2238, "lng": 106.8580},
    {"name": "Stasiun Gambir", "facility_type": "Transport", "lat": -6.1767, "lng": 106.8306},
    {"name": "Halte TransJakarta Dukuh Atas", "facility_type": "Transport", "lat": -6.2023, "lng": 106.8227},
    {"name": "Puskesmas Kecamatan Tebet", "facility_type": "Clinic", "lat": -6.2291, "lng": 106.8569},
]

def seed():
    for f in FACILITIES:
        try:
            req = urllib.request.Request(
                "http://localhost:8000/api/v1/facilities/",
                data=json.dumps(f).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            res = urllib.request.urlopen(req)
            print(f"Created: {f['name']} (Status: {res.getcode()})")
        except Exception as e:
            msg = e.read().decode() if hasattr(e, 'read') else str(e)
            print(f"Failed to create {f['name']}: {msg}")

if __name__ == "__main__":
    seed()

import json
import os
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

DIST_DIR = Path(r"C:\Users\aarav.SOMEGUYWITHPRET\Documents\emsearch-polaris\frontend\dist")
OUT_DIR = Path(r"c:\Users\aarav.SOMEGUYWITHPRET\PayPal Hackathon\docs\screenshots")
ARTIFACT_DIR = Path(r"C:\Users\aarav.SOMEGUYWITHPRET\.gemini\antigravity\brain\d67e18d9-41bf-4c1b-ada3-82742e9d7a84")

OUT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

class SPAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            self.path = "/index.html"
        return super().do_GET()

def run_server(port=5174):
    server = ThreadingHTTPServer(("127.0.0.1", port), SPAHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server

SAMPLE_SUMMARY = {
    "generated_at": "2026-10-30T17:25:00Z",
    "system_status": "operational",
    "data_mode": "persisted_live_data",
    "monitoring": {
        "last_run_at": "2026-10-30T17:24:12Z",
        "last_run_status": "success",
        "assessment_count": 34,
        "persisted_snapshot_count": 12,
        "partial_failures": []
    },
    "metrics": {
        "active_incident_count": 4,
        "critical_incident_count": 1,
        "affected_asset_count": 3,
        "known_people_exposed": 128,
        "registered_asset_count": 18,
        "operational_capability_count": 9,
        "capability_count": 11
    },
    "incidents": [
        {
            "id": 101,
            "incident_key": "inc_cyclone_zeta",
            "asset_id": "ast_hq_sg",
            "headline": "Tropical Cyclone Zeta Category 3 Approaching Sector Bravo",
            "status": "active",
            "risk_level": "critical",
            "confidence": 0.94,
            "hazards": ["tropical_cyclone", "damaging_wind"],
            "first_seen_at": "2026-10-30T14:00:00Z",
            "last_seen_at": "2026-10-30T17:20:00Z",
            "intelligence": {
                "asset": {
                    "id": "ast_hq_sg",
                    "name": "Singapore Distribution Centre",
                    "type": "logistics_hub",
                    "latitude": 1.3521,
                    "longitude": 103.8198,
                    "criticality": "tier_1",
                    "occupancy": 84
                },
                "hazards": ["tropical_cyclone", "damaging_wind"],
                "events": [{
                    "assessment_id": "asm_901",
                    "title": "Severe Gale Warning & Inundation",
                    "summary": "120 knot sustained gusts tracking NW across shipping lanes.",
                    "hazard_type": "tropical_cyclone",
                    "lifecycle_status": "ongoing",
                    "verification_status": "verified",
                    "source_event_ids": ["src_noaa_88"],
                    "latitude": 1.45,
                    "longitude": 103.95,
                    "distance_km": 18.4,
                    "severity_indicators": {"wind_speed_kts": 120}
                }],
                "evidence": [
                    {"source": "NOAA Satellite Feed", "verification_status": "verified"}
                ],
                "recommended_actions": [
                    "Initiate automated perimeter flood barriers",
                    "Re-route outbound ground couriers to dry inland routes"
                ],
                "radius": {
                    "impact_radius_km": 45,
                    "core_radius_km": 20,
                    "caution_radius_km": 60,
                    "asset_distance_km": 18.4,
                    "exposure_zone": "direct_impact",
                    "exposure_zone_label": "Direct Zone",
                    "basis": "atmospheric_pressure",
                    "scale_name": "Saffir-Simpson"
                }
            }
        },
        {
            "id": 102,
            "incident_key": "inc_quake_norcal",
            "asset_id": "ast_sv_lab",
            "headline": "M5.9 Tectonic Event Silicon Valley Perimeter",
            "status": "active",
            "risk_level": "high",
            "confidence": 0.98,
            "hazards": ["earthquake", "seismic"],
            "first_seen_at": "2026-10-30T16:10:00Z",
            "last_seen_at": "2026-10-30T17:15:00Z",
            "intelligence": {
                "asset": {
                    "id": "ast_sv_lab",
                    "name": "Silicon Valley R&D Campus",
                    "type": "data_center",
                    "latitude": 37.3861,
                    "longitude": -122.0839,
                    "criticality": "tier_1",
                    "occupancy": 320
                },
                "hazards": ["earthquake"],
                "events": [{
                    "assessment_id": "asm_902",
                    "title": "Shallow Crustal Rupture",
                    "summary": "Epicenter 12km NW of Mountain View facility.",
                    "hazard_type": "earthquake",
                    "lifecycle_status": "active",
                    "verification_status": "verified",
                    "source_event_ids": ["src_usgs_99"],
                    "latitude": 37.45,
                    "longitude": -122.15,
                    "distance_km": 12.1,
                    "severity_indicators": {"magnitude": 5.9}
                }],
                "evidence": [
                    {"source": "USGS Real-time API", "verification_status": "verified"}
                ],
                "recommended_actions": [
                    "Execute secondary structural integrity check",
                    "Verify automated offsite failover for compute clusters"
                ],
                "radius": {
                    "impact_radius_km": 30,
                    "core_radius_km": 15,
                    "caution_radius_km": 50,
                    "asset_distance_km": 12.1,
                    "exposure_zone": "moderate_shaking",
                    "exposure_zone_label": "Severe Ground Motion",
                    "basis": "peak_ground_acceleration",
                    "scale_name": "MMI"
                }
            }
        }
    ],
    "capabilities": [],
    "automatic_alert_allowed": False
}

def main():
    port = 5174
    server = run_server(port)
    print(f"SPA Server running on http://127.0.0.1:{port}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2
        )
        page = context.new_page()

        # 1. Capture Login Page
        print("Navigating to login page...")
        page.goto(f"http://127.0.0.1:{port}/login")
        page.wait_for_timeout(2000)
        
        login_img = OUT_DIR / "polaris_original_login.png"
        page.screenshot(path=str(login_img), full_page=False)
        shutil.copy(login_img, ARTIFACT_DIR / "polaris_original_login.png")

        # 2. Mock auth and backend data for authenticated AppShell & Command Centre
        page.route("**/auth/me", lambda r: r.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "authenticated": True,
                "subject": "usr_aarav",
                "email": "aarav@polaris.ai",
                "full_name": "Aarav Sharma",
                "role": "admin",
                "organization_id": "org_polaris_core",
                "tier": "enterprise"
            })
        ))

        page.route("**/api/v1/dashboard/summary", lambda r: r.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(SAMPLE_SUMMARY)
        ))
        page.route("**/api/dashboard/summary", lambda r: r.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(SAMPLE_SUMMARY)
        ))
        page.route("**/api/v1/incidents**", lambda r: r.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"count": len(SAMPLE_SUMMARY["incidents"]), "incidents": SAMPLE_SUMMARY["incidents"]})
        ))
        page.route("**/api/v1/incidents/101", lambda r: r.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(SAMPLE_SUMMARY["incidents"][0])
        ))

        page.evaluate('''() => {
            sessionStorage.removeItem("polaris_logged_out");
            sessionStorage.setItem("polaris_token", "mock-token-xyz");
        }''')

        # Navigate to command centre
        print("Navigating to command centre with loaded data...")
        page.goto(f"http://127.0.0.1:{port}/command-centre")
        page.wait_for_timeout(3500)

        cmd_img = OUT_DIR / "polaris_original_command_centre.png"
        page.screenshot(path=str(cmd_img), full_page=False)
        print(f"Captured: {cmd_img}")
        shutil.copy(cmd_img, ARTIFACT_DIR / "polaris_original_command_centre.png")

        # Hover sidebar to capture expanded dock
        print("Hovering sidebar...")
        sidebar_el = page.locator("aside").first
        if sidebar_el.count() > 0:
            sidebar_el.hover()
            page.wait_for_timeout(800)
            expanded_img = OUT_DIR / "polaris_original_sidebar_expanded.png"
            page.screenshot(path=str(expanded_img), full_page=False)
            print(f"Captured: {expanded_img}")
            shutil.copy(expanded_img, ARTIFACT_DIR / "polaris_original_sidebar_expanded.png")

        # Click first incident card in unified sidebar to open UnifiedRiskDossier drawer
        print("Clicking incident to open dossier drawer...")
        try:
            # find an incident card
            incident_card = page.locator("text=Tropical Cyclone Zeta").first
            if incident_card.count() > 0:
                incident_card.click()
                page.wait_for_timeout(1000)
                dossier_img = OUT_DIR / "polaris_original_incident_dossier.png"
                page.screenshot(path=str(dossier_img), full_page=False)
                print(f"Captured: {dossier_img}")
                shutil.copy(dossier_img, ARTIFACT_DIR / "polaris_original_incident_dossier.png")
        except Exception as e:
            print("Could not open dossier:", e)

        # Navigate to monitoring page
        print("Navigating to monitoring...")
        page.goto(f"http://127.0.0.1:{port}/monitoring")
        page.wait_for_timeout(2000)
        mon_img = OUT_DIR / "polaris_original_monitoring.png"
        page.screenshot(path=str(mon_img), full_page=False)
        print(f"Captured: {mon_img}")
        shutil.copy(mon_img, ARTIFACT_DIR / "polaris_original_monitoring.png")

        browser.close()

    server.shutdown()
    print("Done capturing all screenshots!")

if __name__ == "__main__":
    main()

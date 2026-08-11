#!/usr/bin/env python3
"""End-to-end QA test for Latitude Zero CMS (uses stdlib only)"""
import urllib.request, urllib.parse, urllib.error, http.cookiejar, json, sys, time, subprocess, os, signal

BASE = "http://localhost:5001"

def urlopen(url, data=None, headers=None, opener=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    if opener:
        return opener.open(req)
    return urllib.request.urlopen(req)

def login(opener):
    # Get login page
    try:
        r = urlopen(f"{BASE}/admin/", opener=opener)
    except urllib.error.HTTPError as e:
        print(f"✗ Admin login page failed: {e.code}")
        return False
    print("✓ Admin login page loads")

    # Post login
    data = urllib.parse.urlencode({"username": "admin", "password": "latitude2026"}).encode()
    try:
        r = urlopen(f"{BASE}/admin/login/", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, opener=opener)
        content = r.read()
        if b"Dashboard" in content or b"Invalid" not in content:
            print("✓ Login successful, session created")
            return True
        else:
            print("✗ Login failed: Invalid credentials")
            return False
    except urllib.error.HTTPError as e:
        if e.code == 302:
            # Possible redirect after successful login
            print("✓ Login successful (redirect received)")
            return True
        print(f"✗ Login failed: HTTP {e.code}")
        return False

def test_admin_pages(opener):
    pages = [
        ("/admin/", "Dashboard"),
        ("/admin/bookings/", "Bookings"),
        ("/admin/settings/", "Settings"),
        ("/admin/testimonials/", "Testimonials"),
        ("/admin/rooms/", "Rooms"),
        ("/admin/gallery/", "Gallery"),
        ("/admin/pages/", "Pages"),
        ("/admin/pages/about/", "Edit About"),
        ("/admin/pages/services/", "Edit Services"),
        ("/admin/users/", "Users"),
    ]
    errors = []
    for path, name in pages:
        try:
            r = urlopen(f"{BASE}{path}", opener=opener)
            text = r.read().decode('utf-8', errors='replace')
            error_markers = ["Traceback", "Internal Server Error", "jinja2.exceptions", "sqlalchemy"]
            found_error = False
            for marker in error_markers:
                if marker in text:
                    errors.append(f"✗ {name} ({path}): contains '{marker}'")
                    found_error = True
                    break
            if not found_error:
                print(f"✓ {name} ({path})")
        except urllib.error.HTTPError as e:
            errors.append(f"✗ {name} ({path}): status {e.code}")
    return errors

def test_api_endpoints():
    endpoints = [
        "/api/content/",
        "/api/pages/about/",
        "/api/pages/services/",
        "/api/pages/contact/",
        "/api/pages/gallery/",
        "/api/gallery/",
    ]
    errors = []
    for endpoint in endpoints:
        try:
            r = urlopen(f"{BASE}{endpoint}")
            text = r.read().decode('utf-8')
            data = json.loads(text)
            if endpoint == "/api/content/":
                assert "hero" in data, "Missing hero in content API"
                assert "footer" in data, "Missing footer in content API"
                assert "meta_title" in data["hero"], "Missing hero meta_title"
                assert "meta_description" in data["hero"], "Missing hero meta_description"
            elif "/api/pages/" in endpoint:
                assert "sections" in data, f"Missing sections in {endpoint}"
                for s in data["sections"]:
                    assert "meta_title" in s, f"Missing meta_title in section {s.get('key')}"
                    assert "meta_description" in s, f"Missing meta_description in section {s.get('key')}"
            print(f"✓ API {endpoint}")
        except Exception as e:
            errors.append(f"✗ API {endpoint}: {e}")
    return errors

def test_feature_builder(opener):
    r = urlopen(f"{BASE}/admin/pages/about/", opener=opener)
    text = r.read().decode('utf-8', errors='replace')
    checks = [
        ('feature-builder', 'Feature builder class'),
        ('builder_', 'Builder ID prefix'),
        ('feature-intro', 'Intro field class'),
        ('builder-rows', 'Rows container'),
        ('btn-add', 'Add button class'),
        ('parseFeatureContent', 'parseFeatureContent function'),
        ('initFeatureBuilder', 'initFeatureBuilder function'),
        ('addFeatureRow', 'addFeatureRow function'),
        ('removeFeatureRow', 'removeFeatureRow function'),
    ]
    errors = []
    for check, desc in checks:
        if check in text:
            print(f"✓ {desc} present in page")
        else:
            errors.append(f"✗ {desc} NOT found in page HTML")
    return errors

def test_website_pages():
    pages = [
        "/",
        "/pages/about.html",
        "/pages/services.html",
        "/pages/gallery.html",
        "/pages/contact.html",
    ]
    errors = []
    for path in pages:
        try:
            r = urlopen(f"{BASE}{path}")
            text = r.read().decode('utf-8')
            if 'footer-tagline' not in text:
                errors.append(f"✗ {path}: missing .footer-tagline element")
            print(f"✓ Website {path}")
        except urllib.error.HTTPError as e:
            errors.append(f"✗ Website {path}: status {e.code}")
    return errors

def main():
    print("=" * 60)
    print("LATITUDE ZERO CMS — END-TO-END QA")
    print("=" * 60)

    # Kill any existing server on port 5001
    try:
        result = subprocess.run(["lsof", "-ti:5001"], capture_output=True, text=True)
        if result.stdout.strip():
            for pid in result.stdout.strip().split():
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except:
                    pass
            time.sleep(1)
    except:
        pass

    # Start server
    proc = subprocess.Popen(
        ["python3", "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/Users/mac/hotel-website"
    )
    time.sleep(3)

    all_errors = []
    try:
        # Verify server is running
        try:
            urlopen(f"{BASE}/api/content/")
        except Exception as e:
            print(f"✗ Server not running: {e}. Aborting.")
            return 1

        # Create opener with cookie jar
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        # 1. Login
        print("\n1. Login")
        success = login(opener)
        if not success:
            return 1

        # 2. Admin Pages
        print("\n2. Admin Pages (logged in)")
        all_errors.extend(test_admin_pages(opener))

        # 3. API Endpoints
        print("\n3. API Endpoints")
        all_errors.extend(test_api_endpoints())

        # 4. Feature Builder
        print("\n4. Feature Builder (Admin Pages)")
        all_errors.extend(test_feature_builder(opener))

        # 5. Website Pages (Public)
        print("\n5. Website Pages (Public)")
        all_errors.extend(test_website_pages())

        # Summary
        print("\n" + "=" * 60)
        if all_errors:
            print(f"RESULT: {len(all_errors)} ISSUE(S) FOUND\n")
            for e in all_errors:
                print(f"  {e}")
        else:
            print("RESULT: ALL CHECKS PASSED ✓")
        print("=" * 60)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except:
            proc.kill()

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())

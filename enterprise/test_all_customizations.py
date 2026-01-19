"""Comprehensive test of all ActivityWatch customizations"""
import requests
import pymysql
from datetime import datetime, date, timezone

SERVER = "http://localhost:5601"
passed = 0
failed = 0

def test(name, condition, details=""):
    global passed, failed
    if condition:
        print(f"[OK] {name}")
        passed += 1
    else:
        print(f"[FAIL] {name}")
        if details:
            print(f"       {details}")
        failed += 1
    return condition

print("=" * 70)
print("  COMPREHENSIVE TEST OF ACTIVITYWATCH CUSTOMIZATIONS")
print("=" * 70)

# ============================================================
# TEST 1: MySQL Backend
# ============================================================
print("\n" + "=" * 70)
print("TEST 1: MySQL Backend")
print("=" * 70)

try:
    conn = pymysql.connect(
        host='localhost', port=3306,
        user='awuser', password='awpassword',
        database='activitywatch_local', charset='utf8mb4'
    )
    cursor = conn.cursor()

    # Check tables exist
    cursor.execute("SHOW TABLES")
    tables = [t[0] for t in cursor.fetchall()]
    test("MySQL connection", True)
    test("Buckets table exists", "buckets" in tables)
    test("Events table exists", "events" in tables)
    test("Employees table exists", "employees" in tables)
    test("Devices table exists", "devices" in tables)

    # Check event count
    cursor.execute("SELECT COUNT(*) FROM events")
    event_count = cursor.fetchone()[0]
    test(f"Events in database: {event_count}", event_count > 0)

    cursor.close()
    conn.close()
except Exception as e:
    test("MySQL connection", False, str(e))

# ============================================================
# TEST 2: Enterprise Employee Tracking
# ============================================================
print("\n" + "=" * 70)
print("TEST 2: Enterprise Employee Tracking")
print("=" * 70)

try:
    # List employees
    r = requests.get(f"{SERVER}/api/0/admin/employees")
    test("Employees API responds", r.status_code == 200)

    employees = r.json().get('employees', [])
    test(f"Employees exist: {len(employees)}", len(employees) > 0)

    # Check employee structure
    if employees:
        emp = employees[0]
        test("Employee has id", 'id' in emp)
        test("Employee has name", 'name' in emp)
        test("Employee has devices", 'devices' in emp)
        test("Employee has stats", 'stats' in emp)

    # Check employee with device
    emp_with_device = [e for e in employees if e.get('devices')]
    test(f"Employees with devices: {len(emp_with_device)}", len(emp_with_device) > 0)

    if emp_with_device:
        device = emp_with_device[0]['devices'][0]
        test("Device has hostname", 'hostname' in device)
        test("Device has device_type", 'device_type' in device)

except Exception as e:
    test("Employee API", False, str(e))

# ============================================================
# TEST 3: Algorithm Fixes (aw-core compatible)
# ============================================================
print("\n" + "=" * 70)
print("TEST 3: Algorithm Fixes (aw-core compatible)")
print("=" * 70)

try:
    today = date.today().isoformat()
    tomorrow = date.today().isoformat()
    timeperiod = f"{today}T00:00:00Z/{today}T23:59:59Z"

    # Test filter_period_intersect
    query = {
        "timeperiods": [timeperiod],
        "query": [
            'events = query_bucket(find_bucket("aw-watcher-window_"));',
            'afk = query_bucket(find_bucket("aw-watcher-afk_"));',
            'not_afk = filter_keyvals(afk, "status", ["not-afk"]);',
            'filtered = filter_period_intersect(events, not_afk);',
            'RETURN = {"original": len(events), "not_afk": len(not_afk), "filtered": len(filtered), "events": filtered};'
        ]
    }
    r = requests.post(f"{SERVER}/api/0/query/", json=query)
    result = r.json()[0]

    test("filter_period_intersect executes", r.status_code == 200)
    filtered_count = len(result['filtered']) if isinstance(result['filtered'], list) else result['filtered']
    test(f"Filtered events: {filtered_count}", filtered_count >= 0)

    # Check filtered events have correct structure
    if result['events']:
        evt = result['events'][0]
        test("Filtered event has timestamp", 'timestamp' in evt)
        test("Filtered event has duration", 'duration' in evt)
        test("Filtered event has data", 'data' in evt)
        test("Duration is positive", evt['duration'] >= 0)

    # Test merge_events_by_keys
    query2 = {
        "timeperiods": [timeperiod],
        "query": [
            'events = query_bucket(find_bucket("aw-watcher-window_"));',
            'merged = merge_events_by_keys(events, ["app"]);',
            'RETURN = {"original": len(events), "merged": len(merged), "events": merged};'
        ]
    }
    r = requests.post(f"{SERVER}/api/0/query/", json=query2)
    result2 = r.json()[0]

    test("merge_events_by_keys executes", r.status_code == 200)
    test(f"Merged events <= original", result2['merged'] <= result2['original'])

    # Test sum_durations
    query3 = {
        "timeperiods": [timeperiod],
        "query": [
            'events = query_bucket(find_bucket("aw-watcher-window_"));',
            'duration = sum_durations(events);',
            'RETURN = {"duration": duration, "count": len(events)};'
        ]
    }
    r = requests.post(f"{SERVER}/api/0/query/", json=query3)
    result3 = r.json()[0]

    test("sum_durations executes", r.status_code == 200)
    test(f"Duration is float: {result3['duration']:.1f}s", isinstance(result3['duration'], (int, float)))

except Exception as e:
    test("Algorithm tests", False, str(e))

# ============================================================
# TEST 4: Heartbeat & Duplicate Prevention
# ============================================================
print("\n" + "=" * 70)
print("TEST 4: Heartbeat & Duplicate Prevention")
print("=" * 70)

try:
    # Check latest events have proper duration (heartbeat merging works)
    r = requests.get(f"{SERVER}/api/0/buckets/aw-watcher-window_PC458/events?limit=1")
    latest = r.json()[0]
    test(f"Latest window event duration: {latest['duration']:.1f}s", latest['duration'] > 0)

    r = requests.get(f"{SERVER}/api/0/buckets/aw-watcher-afk_PC458/events?limit=1")
    latest_afk = r.json()[0]
    test(f"Latest AFK event duration: {latest_afk['duration']:.1f}s", latest_afk['duration'] > 0)

    # Check for duplicates in today's events
    conn = pymysql.connect(
        host='localhost', port=3306,
        user='awuser', password='awpassword',
        database='activitywatch_local', charset='utf8mb4'
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT bucket_id, timestamp, COUNT(*) as cnt
        FROM events
        WHERE DATE(timestamp) = %s
        GROUP BY bucket_id, timestamp
        HAVING cnt > 1
    """, (date.today(),))
    duplicates = cursor.fetchall()

    test(f"No duplicate events today", len(duplicates) == 0,
         f"Found {len(duplicates)} duplicate groups" if duplicates else "")

    cursor.close()
    conn.close()

except Exception as e:
    test("Heartbeat tests", False, str(e))

# ============================================================
# TEST 5: Active Time Calculation
# ============================================================
print("\n" + "=" * 70)
print("TEST 5: Active Time Calculation")
print("=" * 70)

try:
    # Get active time
    query = {
        "timeperiods": [f"{date.today().isoformat()}T00:00:00Z/{date.today().isoformat()}T23:59:59Z"],
        "query": [
            'events = query_bucket(find_bucket("aw-watcher-window_"));',
            'afk = query_bucket(find_bucket("aw-watcher-afk_"));',
            'not_afk = filter_keyvals(afk, "status", ["not-afk"]);',
            'events = filter_period_intersect(events, not_afk);',
            'duration = sum_durations(events);',
            'RETURN = {"active_duration": duration, "not_afk_duration": sum_durations(not_afk)};'
        ]
    }
    r = requests.post(f"{SERVER}/api/0/query/", json=query)
    result = r.json()[0]

    active = result['active_duration']
    not_afk_dur = result['not_afk_duration']

    # Handle if result is a list (shouldn't be, but safety check)
    if isinstance(active, list):
        active = sum(e.get('duration', 0) for e in active)
    if isinstance(not_afk_dur, list):
        not_afk_dur = sum(e.get('duration', 0) for e in not_afk_dur)

    test(f"Active time: {active:.0f}s ({active/60:.1f} min)", active >= 0)
    test(f"Not-AFK time: {not_afk_dur:.0f}s ({not_afk_dur/60:.1f} min)", not_afk_dur >= 0)
    test("Active time <= Not-AFK time", active <= not_afk_dur + 1)  # +1 for rounding

    # Calculate elapsed time
    first_event = None
    r = requests.get(f"{SERVER}/api/0/buckets/aw-watcher-afk_PC458/events?limit=100")
    events = r.json()
    today_events = [e for e in events if date.today().isoformat() in e['timestamp']]
    if today_events:
        first_ts = min(e['timestamp'] for e in today_events)
        first_event = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
        elapsed = (datetime.now(timezone.utc) - first_event).total_seconds()
        test(f"Elapsed time: {elapsed:.0f}s ({elapsed/60:.1f} min)", elapsed > 0)
        test("Active time <= Elapsed time", active <= elapsed + 10)  # +10 for timing

except Exception as e:
    test("Active time tests", False, str(e))

# ============================================================
# TEST 6: Employee Selector UI
# ============================================================
print("\n" + "=" * 70)
print("TEST 6: Employee Selector UI")
print("=" * 70)

try:
    # Check if JS file is served
    r = requests.get(f"{SERVER}/")
    html = r.text
    test("Main page loads", r.status_code == 200)
    test("Employee selector JS included", "employee-selector.js" in html)

    # Check JS file content
    r = requests.get(f"{SERVER}/js/employee-selector.js")
    if r.status_code == 200:
        js = r.text
        test("JS file loads", True)
        test("Has employee selector", "employee-selector" in js or "employeeSelect" in js)
        test("Calls employees API", "/api/0/admin/employees" in js)
        test("Uses localStorage", "localStorage" in js)
    else:
        test("JS file loads", False, f"Status: {r.status_code}")

except Exception as e:
    test("UI tests", False, str(e))

# ============================================================
# TEST 7: Full WebUI Query (Integration)
# ============================================================
print("\n" + "=" * 70)
print("TEST 7: Full WebUI Query (Integration)")
print("=" * 70)

try:
    # Simulate full aw-webui activity query
    query = {
        "timeperiods": [f"{date.today().isoformat()}T00:00:00Z/{date.today().isoformat()}T23:59:59Z"],
        "query": [
            'events = query_bucket(find_bucket("aw-watcher-window_"));',
            'afk_events = query_bucket(find_bucket("aw-watcher-afk_"));',
            'not_afk = filter_keyvals(afk_events, "status", ["not-afk"]);',
            'events = filter_period_intersect(events, not_afk);',
            'app_events = merge_events_by_keys(events, ["app"]);',
            'app_events = sort_by_duration(app_events);',
            'title_events = merge_events_by_keys(events, ["app", "title"]);',
            'title_events = sort_by_duration(title_events);',
            'duration = sum_durations(events);',
            'RETURN = {"app_events": app_events, "title_events": title_events, "duration": duration, "active_events": events};'
        ]
    }
    r = requests.post(f"{SERVER}/api/0/query/", json=query)
    result = r.json()[0]

    test("Full query executes", r.status_code == 200)
    test("Has app_events", 'app_events' in result)
    test("Has title_events", 'title_events' in result)
    test("Has duration", 'duration' in result)
    test("Has active_events", 'active_events' in result)

    # Verify sorting
    if result['app_events'] and len(result['app_events']) > 1:
        durations = [e['duration'] for e in result['app_events']]
        test("App events sorted by duration", durations == sorted(durations, reverse=True))

except Exception as e:
    test("Integration tests", False, str(e))

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("  TEST SUMMARY")
print("=" * 70)
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
print(f"  Total:  {passed + failed}")
print("=" * 70)

if failed == 0:
    print("  ALL TESTS PASSED!")
else:
    print(f"  {failed} TEST(S) FAILED")
print("=" * 70)

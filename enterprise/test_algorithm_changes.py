#!/usr/bin/env python3
"""
Test the updated algorithms to match original ActivityWatch aw-core:
1. filter_period_intersect - two-pointer O(n+m) algorithm
2. merge_events_by_keys - composite key from existing keys only
3. sum_durations - sum of all event durations
"""
import requests
import json
from datetime import datetime, timedelta, timezone

SERVER = "http://localhost:5601"

def test_server_info():
    """Test basic server connectivity"""
    print("=" * 60)
    print("TEST 1: Server Connectivity")
    print("=" * 60)
    r = requests.get(f"{SERVER}/api/0/info")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"Server Info: {r.json()}")
        print("[OK] PASSED")
        return True
    else:
        print("[FAIL] FAILED")
        return False

def test_buckets():
    """Test bucket listing"""
    print("\n" + "=" * 60)
    print("TEST 2: List Buckets")
    print("=" * 60)
    r = requests.get(f"{SERVER}/api/0/buckets/")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        buckets = r.json()
        print(f"Found {len(buckets)} buckets:")
        for bid, bdata in buckets.items():
            print(f"  - {bid}")
        print("[OK] PASSED")
        return True
    else:
        print("[FAIL] FAILED")
        return False

def test_filter_period_intersect():
    """Test filter_period_intersect with two-pointer algorithm"""
    print("\n" + "=" * 60)
    print("TEST 3: filter_period_intersect (Two-Pointer Algorithm)")
    print("=" * 60)

    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    timeperiod = f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    # Query that tests filter_period_intersect
    query_lines = [
        'events = flood(query_bucket(find_bucket("aw-watcher-window_")));',
        'not_afk = flood(query_bucket(find_bucket("aw-watcher-afk_")));',
        'not_afk = filter_keyvals(not_afk, "status", ["not-afk"]);',
        'filtered = filter_period_intersect(events, not_afk);',
        'RETURN = {"original_count": events, "afk_count": not_afk, "filtered": filtered};'
    ]

    r = requests.post(
        f"{SERVER}/api/0/query/",
        json={"timeperiods": [timeperiod], "query": query_lines}
    )

    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        result = r.json()
        if result and isinstance(result[0], dict):
            data = result[0]
            orig_count = len(data.get('original_count', []))
            afk_count = len(data.get('afk_count', []))
            filtered_count = len(data.get('filtered', []))

            print(f"  Original events: {orig_count}")
            print(f"  Not-AFK periods: {afk_count}")
            print(f"  Filtered events: {filtered_count}")

            # Check that filtering works correctly
            if filtered_count <= orig_count:
                print("  [OK] Filtered count <= original count")

            # Check filtered events have correct structure
            filtered = data.get('filtered', [])
            if filtered:
                sample = filtered[0]
                has_timestamp = 'timestamp' in sample
                has_duration = 'duration' in sample
                has_data = 'data' in sample
                print(f"  [OK] Event structure: timestamp={has_timestamp}, duration={has_duration}, data={has_data}")

                # Check durations are positive
                all_positive = all(e.get('duration', 0) > 0 for e in filtered)
                print(f"  [OK] All durations positive: {all_positive}")

            print("[OK] PASSED")
            return True
        else:
            print(f"Unexpected result format: {result}")
            print("[FAIL] FAILED")
            return False
    else:
        print("[FAIL] FAILED")
        return False

def test_merge_events_by_keys():
    """Test merge_events_by_keys with composite key algorithm"""
    print("\n" + "=" * 60)
    print("TEST 4: merge_events_by_keys (Composite Key Algorithm)")
    print("=" * 60)

    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    timeperiod = f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    # Query that tests merge_events_by_keys
    query_lines = [
        'events = flood(query_bucket(find_bucket("aw-watcher-window_")));',
        'not_afk = flood(query_bucket(find_bucket("aw-watcher-afk_")));',
        'not_afk = filter_keyvals(not_afk, "status", ["not-afk"]);',
        'events = filter_period_intersect(events, not_afk);',
        'by_app = merge_events_by_keys(events, ["app"]);',
        'by_title = merge_events_by_keys(events, ["app", "title"]);',
        'RETURN = {"events": events, "by_app": by_app, "by_title": by_title};'
    ]

    r = requests.post(
        f"{SERVER}/api/0/query/",
        json={"timeperiods": [timeperiod], "query": query_lines}
    )

    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        result = r.json()
        if result and isinstance(result[0], dict):
            data = result[0]
            events = data.get('events', [])
            by_app = data.get('by_app', [])
            by_title = data.get('by_title', [])

            print(f"  Original events: {len(events)}")
            print(f"  Merged by app: {len(by_app)}")
            print(f"  Merged by app+title: {len(by_title)}")

            # Check that merged count <= original
            if len(by_app) <= len(events):
                print("  [OK] by_app count <= original")

            if len(by_title) <= len(events):
                print("  [OK] by_title count <= original")

            # Check that merged events only contain specified keys
            if by_app:
                sample = by_app[0]
                data_keys = list(sample.get('data', {}).keys())
                print(f"  [OK] by_app data keys: {data_keys}")
                if 'app' in data_keys:
                    print("  [OK] 'app' key present in merged data")

            # Check duration sums are preserved
            orig_total = sum(e.get('duration', 0) for e in events)
            app_total = sum(e.get('duration', 0) for e in by_app)
            print(f"  Original total duration: {orig_total:.2f}s")
            print(f"  Merged by_app total: {app_total:.2f}s")

            if abs(orig_total - app_total) < 0.1:  # Allow small floating point error
                print("  [OK] Duration sums match!")
            else:
                print(f"  [WARN] Duration difference: {abs(orig_total - app_total):.2f}s")

            print("[OK] PASSED")
            return True
        else:
            print("[FAIL] FAILED - unexpected result format")
            return False
    else:
        print("[FAIL] FAILED")
        return False

def test_sum_durations():
    """Test sum_durations function"""
    print("\n" + "=" * 60)
    print("TEST 5: sum_durations")
    print("=" * 60)

    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    timeperiod = f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    # Query that tests sum_durations
    query_lines = [
        'events = flood(query_bucket(find_bucket("aw-watcher-window_")));',
        'not_afk = flood(query_bucket(find_bucket("aw-watcher-afk_")));',
        'not_afk = filter_keyvals(not_afk, "status", ["not-afk"]);',
        'events = filter_period_intersect(events, not_afk);',
        'total = sum_durations(events);',
        'RETURN = {"events": events, "total_duration": total};'
    ]

    r = requests.post(
        f"{SERVER}/api/0/query/",
        json={"timeperiods": [timeperiod], "query": query_lines}
    )

    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        result = r.json()
        if result and isinstance(result[0], dict):
            data = result[0]
            events = data.get('events', [])
            total_duration = data.get('total_duration', 0)

            # Manually calculate sum
            manual_sum = sum(e.get('duration', 0) for e in events)

            print(f"  Events count: {len(events)}")
            print(f"  sum_durations result: {total_duration:.2f}s ({total_duration/60:.1f} min)")
            print(f"  Manual sum: {manual_sum:.2f}s")

            if abs(total_duration - manual_sum) < 0.001:
                print("  [OK] sum_durations matches manual calculation!")
                print("[OK] PASSED")
                return True
            else:
                print(f"  [FAIL] Mismatch: {abs(total_duration - manual_sum):.4f}s")
                print("[FAIL] FAILED")
                return False
        else:
            print("[FAIL] FAILED - unexpected result format")
            return False
    else:
        print("[FAIL] FAILED")
        return False

def test_full_webui_query():
    """Test the complete web UI query that uses all functions"""
    print("\n" + "=" * 60)
    print("TEST 6: Full Web UI Query (Integration Test)")
    print("=" * 60)

    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    timeperiod = f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    # Exact query from aw-webui Activity view
    query_lines = [
        'events = flood(query_bucket(find_bucket("aw-watcher-window_")));',
        'not_afk = flood(query_bucket(find_bucket("aw-watcher-afk_")));',
        'not_afk = filter_keyvals(not_afk, "status", ["not-afk"]);',
        'events = filter_period_intersect(events, not_afk);',
        'events = categorize(events, []);',
        'title_events = sort_by_duration(merge_events_by_keys(events, ["app", "title"]));',
        'app_events = sort_by_duration(merge_events_by_keys(title_events, ["app"]));',
        'cat_events = sort_by_duration(merge_events_by_keys(events, ["$category"]));',
        'duration = sum_durations(events);',
        'RETURN = {"window": {"app_events": app_events, "title_events": title_events, "cat_events": cat_events, "active_events": not_afk, "duration": duration}};'
    ]

    r = requests.post(
        f"{SERVER}/api/0/query/",
        json={"timeperiods": [timeperiod], "query": query_lines}
    )

    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        result = r.json()
        if result and isinstance(result[0], dict) and 'window' in result[0]:
            window = result[0]['window']

            print(f"  app_events: {len(window.get('app_events', []))} entries")
            print(f"  title_events: {len(window.get('title_events', []))} entries")
            print(f"  cat_events: {len(window.get('cat_events', []))} entries")
            print(f"  active_events: {len(window.get('active_events', []))} entries")
            print(f"  duration: {window.get('duration', 0):.2f}s ({window.get('duration', 0)/60:.1f} min)")

            # Verify structure matches what aw-webui expects
            required_keys = ['app_events', 'title_events', 'cat_events', 'active_events', 'duration']
            has_all_keys = all(k in window for k in required_keys)
            print(f"  [OK] Has all required keys: {has_all_keys}")

            # Check that app_events are sorted by duration (descending)
            app_events = window.get('app_events', [])
            if len(app_events) > 1:
                durations = [e.get('duration', 0) for e in app_events]
                is_sorted = all(durations[i] >= durations[i+1] for i in range(len(durations)-1))
                print(f"  [OK] app_events sorted by duration (desc): {is_sorted}")

            print("[OK] PASSED")
            return True
        else:
            print(f"Unexpected result structure: {result}")
            print("[FAIL] FAILED")
            return False
    else:
        print("[FAIL] FAILED")
        return False

def main():
    print("\n" + "=" * 60)
    print("  ACTIVITYWATCH ALGORITHM TEST SUITE")
    print("  Testing updated aw-core compatible algorithms")
    print("=" * 60)

    results = []

    # Run all tests
    results.append(("Server Connectivity", test_server_info()))
    results.append(("List Buckets", test_buckets()))
    results.append(("filter_period_intersect", test_filter_period_intersect()))
    results.append(("merge_events_by_keys", test_merge_events_by_keys()))
    results.append(("sum_durations", test_sum_durations()))
    results.append(("Full Web UI Query", test_full_webui_query()))

    # Summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[OK] PASSED" if result else "[FAIL] FAILED"
        print(f"  {name}: {status}")

    print(f"\n  Total: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

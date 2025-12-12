"""
Analyze duplicate complex_id values in complexes.csv
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path


def analyze_duplicates():
    """Analyze duplicate complex_id values."""
    csv_file = Path("/Users/jito.hello/dev/wooto/homesweethome/output/complexes.csv")

    # Read CSV
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Count occurrences of each complex_id
    id_counts = Counter(row["complex_id"] for row in rows)

    # Find duplicates
    duplicates = {cid: count for cid, count in id_counts.items() if count > 1}

    print(f"Total rows: {len(rows)}")
    print(f"Unique complex_ids: {len(id_counts)}")
    print(f"Duplicates found: {len(duplicates)}")

    # Group duplicates by complex_id
    duplicate_groups = defaultdict(list)
    for row in rows:
        cid = row["complex_id"]
        if cid in duplicates:
            duplicate_groups[cid].append(row)

    # Analyze patterns
    print("\nDuplicate Analysis:")
    print("=" * 50)

    # Check for patterns in duplicates
    same_id_different_names = []

    for cid, rows_list in duplicate_groups.items():
        names = [r["complex_name"] for r in rows_list]
        unique_names = set(names)

        if len(unique_names) > 1:
            same_id_different_names.append((cid, rows_list))

    # Count names
    name_counts = Counter(row["complex_name"] for row in rows)
    name_duplicates = {name: count for name, count in name_counts.items() if count > 1}

    # Group by name
    name_groups = defaultdict(list)
    for row in rows:
        name = row["complex_name"]
        if name in name_duplicates:
            name_groups[name].append(row)

    # Print examples
    print("\nExamples of same complex_id with different names:")
    for cid, rows_list in same_id_different_names[:5]:
        print(f"\ncomplex_id: {cid}")
        for r in rows_list:
            print(f"  - {r['complex_name']} (fetched_at: {r['fetched_at']})")

    print("\n\nExamples of same complex_name with different IDs:")
    for name, rows_list in list(name_groups.items())[:5]:
        if len(set(r["complex_id"] for r in rows_list)) > 1:
            print(f"\ncomplex_name: {name}")
            for r in rows_list:
                print(f"  - {r['complex_id']} (fetched_at: {r['fetched_at']})")

    # Check for temporal patterns
    print("\n\nTemporal Analysis:")
    print("=" * 50)

    # Group by fetch time
    fetch_times = Counter(row["fetched_at"] for row in rows)
    print(f"Unique fetch times: {len(fetch_times)}")

    for time, count in fetch_times.most_common(3):
        print(f"  {time}: {count} rows")

    # Check if duplicates have different fetch times
    duplicates_with_different_times = 0
    for cid, rows_list in duplicate_groups.items():
        times = set(r["fetched_at"] for r in rows_list)
        if len(times) > 1:
            duplicates_with_different_times += 1

    print(f"\nDuplicates with different fetch times: {duplicates_with_different_times}")

    # Export duplicate analysis
    with open("duplicate_analysis_report.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["complex_id", "complex_name", "count", "is_duplicate"])

        for cid, count in id_counts.items():
            is_dup = count > 1
            name = None
            for row in rows:
                if row["complex_id"] == cid:
                    name = row["complex_name"]
                    break
            writer.writerow([cid, name, count, "Yes" if is_dup else "No"])

    print("\nDuplicate analysis exported to: duplicate_analysis_report.csv")


if __name__ == "__main__":
    analyze_duplicates()

#!/usr/bin/env python3
"""Generate a README.md with GitHub traffic statistics."""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def read_csv(filepath):
    rows = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def get_date_range(data_dir):
    all_dates = set()
    for csv_file in Path(data_dir, "views").glob("*.csv"):
        for row in read_csv(csv_file):
            if row.get("date"):
                all_dates.add(row["date"])
    if not all_dates:
        return "N/A", "N/A"
    return min(all_dates), max(all_dates)


def compute_days(start_date, end_date):
    try:
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date, "%Y-%m-%d")
        return (d2 - d1).days + 1
    except (ValueError, TypeError):
        return 0


def aggregate_views_clones(data_dir, metric):
    results = {}
    for csv_file in Path(data_dir, metric).glob("*.csv"):
        repo = csv_file.stem
        total_count = 0
        total_uniques = 0
        daily = []
        monthly = defaultdict(lambda: {"count": 0, "uniques": 0})
        for row in read_csv(csv_file):
            try:
                count = int(row.get("count", 0) or 0)
                uniques = int(row.get("uniques", 0) or 0)
                date = row.get("date", "")
                total_count += count
                total_uniques += uniques
                if date and len(date) >= 7:
                    month_key = date[:7]
                    monthly[month_key]["count"] += count
                    monthly[month_key]["uniques"] += uniques
                if count > 0:
                    daily.append({"date": date, "count": count, "uniques": uniques})
            except ValueError:
                continue
        if total_count > 0:
            peak = max(daily, key=lambda x: x["count"]) if daily else None
            results[repo] = {
                "count": total_count,
                "uniques": total_uniques,
                "peak": peak,
                "days_active": len(daily),
                "monthly": dict(sorted(monthly.items())),
            }
    return dict(sorted(results.items(), key=lambda x: x[1]["count"], reverse=True))


def aggregate_monthly_totals(data_dir, metric):
    monthly = defaultdict(lambda: {"count": 0, "uniques": 0})
    for csv_file in Path(data_dir, metric).glob("*.csv"):
        for row in read_csv(csv_file):
            try:
                count = int(row.get("count", 0) or 0)
                uniques = int(row.get("uniques", 0) or 0)
                date = row.get("date", "")
                if date and len(date) >= 7:
                    monthly[date[:7]]["count"] += count
                    monthly[date[:7]]["uniques"] += uniques
            except ValueError:
                continue
    return dict(sorted(monthly.items()))


def aggregate_referrers(data_dir):
    ref_totals = defaultdict(lambda: defaultdict(lambda: {"count": 0, "uniques": 0}))
    for csv_file in Path(data_dir, "referrers").glob("*.csv"):
        repo = csv_file.stem
        for row in read_csv(csv_file):
            for i in range(1, 11):
                ref = row.get(f"ref_{i}", "").strip()
                count = row.get(f"ref_{i}_count", "")
                uniques = row.get(f"ref_{i}_uniques", "")
                if ref and count:
                    try:
                        ref_totals[repo][ref]["count"] += int(count)
                        ref_totals[repo][ref]["uniques"] += int(uniques or 0)
                    except ValueError:
                        continue
    return ref_totals


def aggregate_all_referrers(referrers):
    global_refs = defaultdict(lambda: {"count": 0, "uniques": 0})
    for repo_refs in referrers.values():
        for ref, stats in repo_refs.items():
            global_refs[ref]["count"] += stats["count"]
            global_refs[ref]["uniques"] += stats["uniques"]
    return dict(sorted(global_refs.items(), key=lambda x: x[1]["count"], reverse=True))


def aggregate_paths(data_dir):
    path_totals = defaultdict(lambda: defaultdict(lambda: {"count": 0, "uniques": 0}))
    for csv_file in Path(data_dir, "paths").glob("*.csv"):
        repo = csv_file.stem
        for row in read_csv(csv_file):
            for i in range(1, 11):
                path = row.get(f"path_{i}", "").strip()
                count = row.get(f"path_{i}_count", "")
                uniques = row.get(f"path_{i}_uniques", "")
                if path and count:
                    try:
                        path_totals[repo][path]["count"] += int(count)
                        path_totals[repo][path]["uniques"] += int(uniques or 0)
                    except ValueError:
                        continue
    return path_totals


def compute_totals(views, clones):
    total_views = sum(s["count"] for s in views.values())
    total_uniques = sum(s["uniques"] for s in views.values())
    total_clones = sum(s["count"] for s in clones.values())
    total_cloners = sum(s["uniques"] for s in clones.values())
    return total_views, total_uniques, total_clones, total_cloners


def generate_readme(data_dir="data"):
    start_date, end_date = get_date_range(data_dir)
    days = compute_days(start_date, end_date)
    views = aggregate_views_clones(data_dir, "views")
    clones = aggregate_views_clones(data_dir, "clones")
    monthly_views = aggregate_monthly_totals(data_dir, "views")
    monthly_clones = aggregate_monthly_totals(data_dir, "clones")
    referrers = aggregate_referrers(data_dir)
    global_refs = aggregate_all_referrers(referrers)
    paths = aggregate_paths(data_dir)
    total_views, total_uniques, total_clones, total_cloners = compute_totals(
        views, clones
    )

    lines = [
        "# GitHub Traffic Stats",
        "",
        f"**Data range:** `{start_date}` to `{end_date}` ({days} days)",
        "",
        "| Metric | Total | Unique |",
        "|--------|-------|--------|",
        f"| Views | {total_views:,} | {total_uniques:,} |",
        f"| Clones | {total_clones:,} | {total_cloners:,} |",
        f"| Repos tracked | {len(views)} | - |",
        "",
        "Auto-generated from [GitHub Traffic API](https://docs.github.com/en/rest/metrics/traffic) data collected daily via GitHub Actions.",
        "",
        "---",
        "",
        "## Monthly Breakdown",
        "",
    ]

    all_months = sorted(set(list(monthly_views.keys()) + list(monthly_clones.keys())))
    if all_months:
        lines.append("| Month | Views | Unique Visitors | Clones | Unique Cloners |")
        lines.append("|-------|-------|-----------------|--------|----------------|")
        cumulative_views = 0
        cumulative_clones = 0
        for month in all_months:
            mv = monthly_views.get(month, {"count": 0, "uniques": 0})
            mc = monthly_clones.get(month, {"count": 0, "uniques": 0})
            cumulative_views += mv["count"]
            cumulative_clones += mc["count"]
            lines.append(
                f"| {month} | {mv['count']:,} | {mv['uniques']:,} "
                f"| {mc['count']:,} | {mc['uniques']:,} |"
            )
        lines.append(
            f"| **Total** | **{total_views:,}** | **{total_uniques:,}** "
            f"| **{total_clones:,}** | **{total_cloners:,}** |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Top Repositories by Views",
            "",
            "| # | Repository | Views | Uniques | Peak Day | Peak Views | Active Days |",
            "|---|-----------|-------|---------|----------|------------|-------------|",
        ]
    )

    for i, (repo, stats) in enumerate(list(views.items())[:25], 1):
        peak = stats.get("peak")
        peak_date = peak["date"] if peak else "-"
        peak_count = f"{peak['count']:,}" if peak else "-"
        lines.append(
            f"| {i} | [{repo}](https://github.com/Chocapikk/{repo}) "
            f"| {stats['count']:,} | {stats['uniques']:,} "
            f"| {peak_date} | {peak_count} | {stats['days_active']} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Top Repositories by Clones",
            "",
            "| # | Repository | Clones | Uniques | Peak Day | Peak Clones | Active Days |",
            "|---|-----------|--------|---------|----------|-------------|-------------|",
        ]
    )

    for i, (repo, stats) in enumerate(list(clones.items())[:25], 1):
        peak = stats.get("peak")
        peak_date = peak["date"] if peak else "-"
        peak_count = f"{peak['count']:,}" if peak else "-"
        lines.append(
            f"| {i} | [{repo}](https://github.com/Chocapikk/{repo}) "
            f"| {stats['count']:,} | {stats['uniques']:,} "
            f"| {peak_date} | {peak_count} | {stats['days_active']} |"
        )

    # Monthly breakdown per top repo
    lines.extend(
        [
            "",
            "---",
            "",
            "## Monthly Views per Repository (Top 10)",
            "",
        ]
    )

    top_repos = list(views.keys())[:10]
    if all_months and top_repos:
        header = "| Repository | " + " | ".join(all_months) + " | Total |"
        sep = "|-----------|" + "|".join(["-------"] * len(all_months)) + "|-------|"
        lines.append(header)
        lines.append(sep)
        for repo in top_repos:
            monthly = views[repo].get("monthly", {})
            cols = [f"{monthly.get(m, {}).get('count', 0):,}" for m in all_months]
            lines.append(
                f"| [{repo}](https://github.com/Chocapikk/{repo}) | "
                + " | ".join(cols)
                + f" | **{views[repo]['count']:,}** |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Global Referrers (All Repos Combined)",
            "",
            "> **Note:** Referrer data uses GitHub's 14-day rolling window, "
            "so totals reflect cumulative snapshots and may exceed actual view counts.",
            "",
            "| # | Referrer | Total Views | Total Uniques |",
            "|---|----------|-------------|---------------|",
        ]
    )

    for i, (ref, stats) in enumerate(list(global_refs.items())[:15], 1):
        lines.append(f"| {i} | {ref} | {stats['count']:,} | {stats['uniques']:,} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Top Referrers by Repository",
            "",
        ]
    )

    top_repos_by_views = list(views.keys())[:10]
    for repo in top_repos_by_views:
        if repo not in referrers or not referrers[repo]:
            continue
        sorted_refs = sorted(
            referrers[repo].items(), key=lambda x: x[1]["count"], reverse=True
        )[:5]
        if not sorted_refs:
            continue

        lines.append(
            f"<details><summary><b>{repo}</b> "
            f"({views[repo]['count']:,} views)</summary>"
        )
        lines.append("")
        lines.append("| Referrer | Views | Uniques |")
        lines.append("|----------|-------|---------|")
        for ref, stats in sorted_refs:
            lines.append(f"| {ref} | {stats['count']:,} | {stats['uniques']:,} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Top Paths by Repository",
            "",
            "> **Note:** Path data uses GitHub's 14-day rolling window, "
            "same caveat as referrers.",
            "",
        ]
    )

    for repo in top_repos_by_views[:5]:
        if repo not in paths or not paths[repo]:
            continue
        sorted_paths = sorted(
            paths[repo].items(), key=lambda x: x[1]["count"], reverse=True
        )[:5]
        if not sorted_paths:
            continue

        lines.append(f"<details><summary><b>{repo}</b></summary>")
        lines.append("")
        lines.append("| Path | Views | Uniques |")
        lines.append("|------|-------|---------|")
        for path, stats in sorted_paths:
            short_path = path.replace(f"/Chocapikk/{repo}", "") or "/"
            lines.append(
                f"| `{short_path}` | {stats['count']:,} | {stats['uniques']:,} |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            f"*Last updated: auto-generated by `generate_readme.py` "
            f"| {len(views)} repos | {days} days of data*",
            "",
        ]
    )

    with open("README.md", "w") as f:
        f.write("\n".join(lines))

    print(
        f"README.md generated ({len(views)} repos tracked, "
        f"{start_date} to {end_date}, {days} days)"
    )


if __name__ == "__main__":
    generate_readme()

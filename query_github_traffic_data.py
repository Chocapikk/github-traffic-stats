import os
import csv
import requests
from datetime import datetime, timedelta

BASE_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GH_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def get_github_data(endpoint):
    response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS)
    response.raise_for_status()
    return response.json()


def append_to_csv(filename, data):
    file_exists = os.path.isfile(filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(data.keys())
        writer.writerow(data.values())


def save_views_clones_data(data, filename):
    yesterday = (datetime.now() - timedelta(days=1)).date()
    for item in data:
        item_date = datetime.strptime(item["timestamp"][:10], "%Y-%m-%d").date()
        if item_date == yesterday:
            csv_data = {
                "date": item_date.strftime("%Y-%m-%d"),
                "count": item["count"],
                "uniques": item["uniques"],
            }
            append_to_csv(filename, csv_data)
            break


def save_referrers_paths_data(data, filename, data_type):
    today = datetime.now().date().strftime("%Y-%m-%d")
    csv_data = {"date": today}

    if not data:
        return

    padded_data = data[:10] + [
        {"path": "", "referrer": "", "count": "", "uniques": ""}
    ] * (10 - len(data))

    for i, item in enumerate(padded_data, 1):
        key = "path" if data_type == "path" else "referrer"
        csv_data[f"{data_type}_{i}"] = item[key]
        csv_data[f"{data_type}_{i}_count"] = item["count"]
        csv_data[f"{data_type}_{i}_uniques"] = item["uniques"]

    file_exists = os.path.isfile(filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(csv_data.keys())
        writer.writerow(csv_data.values())


def get_user_public_repos(username):
    repos = []
    page = 1
    while True:
        response = get_github_data(
            f"/users/{username}/repos?type=owner&per_page=100&page={page}"
        )
        if not response:
            break
        repos.extend(
            repo["name"]
            for repo in response
            if not repo["fork"] and not repo["private"]
        )
        page += 1
    return repos


def main():
    owner = "Chocapikk"
    repos = get_user_public_repos(owner)
    print(f"Found {len(repos)} public repos")

    for repo in repos:
        try:
            views_data = get_github_data(f"/repos/{owner}/{repo}/traffic/views")
            save_views_clones_data(views_data["views"], f"data/views/{repo}.csv")

            clones_data = get_github_data(f"/repos/{owner}/{repo}/traffic/clones")
            save_views_clones_data(clones_data["clones"], f"data/clones/{repo}.csv")

            paths_data = get_github_data(f"/repos/{owner}/{repo}/traffic/popular/paths")
            save_referrers_paths_data(paths_data, f"data/paths/{repo}.csv", "path")

            referrers_data = get_github_data(
                f"/repos/{owner}/{repo}/traffic/popular/referrers"
            )
            save_referrers_paths_data(
                referrers_data, f"data/referrers/{repo}.csv", "ref"
            )

            print(f"  [+] {repo}")

        except requests.exceptions.HTTPError as exc:
            print(f"  [-] {repo}: {exc}")
            continue


if __name__ == "__main__":
    main()

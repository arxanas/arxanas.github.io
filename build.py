#!/usr/bin/env python3
import collections
import os
import shutil
import time

import bs4
import feedparser
import requests

from typing import Mapping, Optional


CITY = "Seattle"


def get_blog_info() -> Mapping[str, str]:
    feed = feedparser.parse("https://blog.waleedkhan.name/feed.xml")
    entry = feed.entries[0]
    title = entry.title
    date = time.strftime("%b %d, %Y", entry.published_parsed)
    tags = " &bull; ".join(tag["term"] for tag in entry.tags)
    link = entry.link
    return {
        "blog": f"""\
<p>
<span class="latest">Latest post</span>
<span class="latest">{date} &bull; {tags}</span>
<a href="{link}">{title}</a><br />
</p>
"""
    }


def get_github_info() -> Mapping[str, str]:
    result = requests.get(
        "https://api.github.com/users/arxanas/events/public",
        headers={"Accept": "application/vnd.github.v3+json"},
    )
    commits = []
    for event in result.json():
        repo = event["repo"]
        event_time = time.strftime(
            "%b %d, %Y", time.strptime(event["created_at"].split("T")[0], "%Y-%m-%d")
        )
        for commit in event["payload"].get("commits", []):
            commit_url = (
                f"""https://github.com/{repo["name"]}/commits/{commit["sha"]}"""
            )
            commits.append(
                f"""\
<tr>
<td><a href="https://github.com/{repo["name"]}">{repo["name"]}</a></td>
<td>{event_time}</td>
<td><a href="{commit_url}">{commit["message"]}</a></td>
</tr>
"""
            )
    latest_commits, earlier_commits = commits[:3], commits[3:]
    tbody_html = "\n".join(latest_commits)
    num_earlier_commits = len(earlier_commits)

    return {
        "github": f"""\
<p>
<span class="latest">Recent commits</span>
<div class="table-container">
<table>
<thead>
<th>Repo</th>
<th>Date</th>
<th>Message</th>
</thead>
<tbody>
{tbody_html}
</tbody>
</table>
</div>
<span class="latest">...and <a href="https://github.com/arxanas#js-contribution-activity">{num_earlier_commits} more recent commits</a>.</span>
</p>
"""
    }


def get_resume_info() -> Mapping[str, str]:
    return {
        "resume": f"""\
<p>
<span class="latest">Contact me at
  <a href="mailto:me@waleedkhan.name">me@waleedkhan.name</a>
</span >
I'm a software engineer who builds highly-scalable developer
tooling.<br />
I'm based in {CITY}.
</p>
"""
    }


def get_linkedin_info() -> Mapping[str, str]:
    # The LinkedIn API doesn't provide enough information unless you're
    # approved for their Partner Program. Just scrape my resume and pretend
    # it's from LinkedIn.
    result = requests.get("https://resume.waleedkhan.name")
    soup = bs4.BeautifulSoup(result.content, features="html.parser")
    job = soup.find_all(class_="job")[0]
    job_employer = job.find(class_="job-employer").text
    job_description = job.find(class_="job-description").text
    job_date = job.find(class_="job-date").text
    return {
        "linkedin": f"""\
<p>
<span class="latest">Current position</span>
{job_description} @ {job_employer}<br />
{job_date}
</p>
"""
    }


def get_stack_overflow_info() -> Mapping[str, str]:
    result = requests.get(
        "https://api.stackexchange.com/2.2/users/344643?site=stackoverflow"
    )
    user_info = result.json()["items"][0]
    reputation = user_info["reputation"]
    reputation_change_month = user_info["reputation_change_month"]
    return {
        "stackoverflow": f"""\
<p>
<span class="latest">Reputation</span>
{reputation} internet points<br />
+{reputation_change_month} this month
<p>
"""
    }


def get_last_updated_info() -> Mapping[str, str]:
    current_date = time.strftime("%Y-%m-%d")
    return {
        "last_updated": f"""\
<p>
<span class="latest">Last updated: {current_date}</span>
This page is a live activity feed of my internet presence, updated once a day.
</p>
"""
    }


def get_restaurant_info() -> Mapping[str, str]:
    budget_id = "last-used"
    category_name = "Eating Out"
    ynab_api_key = os.environ["YNAB_API_KEY"]
    headers = {"Authorization": f"Bearer {ynab_api_key}"}
    category_groups = requests.get(
        f"https://api.youneedabudget.com/v1/budgets/{budget_id}/categories",
        headers=headers,
    ).json()["data"]["category_groups"]

    category_id = None
    for category_group in category_groups:
        for category in category_group["categories"]:
            if category["name"] == category_name:
                category_id = category["id"]
    assert category_id is not None, f"Could not find YNAB category: {category_name}"

    year = int(time.strftime("%Y")) - 1
    month = time.strftime("%m")
    since_date = f"{year}-{month}-01"
    transactions = requests.get(
        f"https://api.youneedabudget.com/v1/budgets/{budget_id}/categories/{category_id}/transactions",
        headers=headers,
        params={
            "since_date": since_date,
        },
    ).json()["data"]["transactions"]

    payees = collections.defaultdict(list)
    for transaction in transactions:
        payees[transaction["payee_name"]].append(transaction)
    top_payees = sorted(payees.items(), key=lambda kv: len(kv[1]), reverse=True)[:10]

    table_rows_html = ""
    for (payee_name, payee_transactions) in top_payees:
        payee_href = (
            f"""http://google.com/maps/search/{CITY}+{payee_name.replace(" ", "+")}"""
        )
        num_payee_transactions = len(payee_transactions)
        total_spent_at_payee = (
            -sum(transaction["amount"] for transaction in payee_transactions) / 1000
        )
        table_rows_html += f"""\
<tr>
<td><a href="{payee_href}">{payee_name}</a></td>
<td>{num_payee_transactions}</td>
<td>${total_spent_at_payee:.2f}</td>
</tr>
"""

    return {
        "restaurants": f"""\
<p>
<span class="latest">Top {CITY} restaurants</span>
<span class="latest">Automatically extracted from budgeting software. Don't judge.</span>
</p>
<div class="table-container">
<table>
<thead>
<th>Name</th>
<th>Visits (past year)</th>
<th>Spend 😱 (past year)</th>
</thead>
<tbody>
{table_rows_html}
</tbody>
</table>
</div>
"""
    }


def get_redirects() -> Mapping[str, str]:
    blog_articles = [
        "will-i-ever-use-this",
        "steno-journal",
        "steno-adventures-part-1",
        "steno-adventures-part-2",
        "dot-name-email-address",
        "pyqt-designer",
        "messenger-conversation-macros",
        "parsing-contextual-keywords",
        "union-vs-sum-types",
        "data-comprehension-syntaxes",
        "my-steno-system",
        "getting-a-job-in-pl",
        "ocaml-file-extensions",
        "monotonicity",
        "mail-server",
        "lan-adapter",
        "smash-bros-parabola-rule",
        "smash-training-retrospective",
        "rust-modules-for-python-users",
    ]
    blog_redirects = {
        "blog": "https://blog.waleedkhan.name/",
    }
    for article in blog_articles:
        blog_redirects[f"blog/{article}"] = f"https://blog.waleedkhan.name/{article}/"

    eecs281_articles = [
        "sublime-clang",
        "from-eecs-183-and-280",
        "painless-automated-testing",
        "code-deduplication",
        "terminal-tips-and-tricks",
        "dealing-with-caen",
    ]
    eecs281_redirects = {
        "281": "https://eecs281.waleedkhan.name/",
    }
    for article in eecs281_articles:
        eecs281_redirects[
            f"281/{article}"
        ] = f"https://eecs281.waleedkhan.name/{article}/"

    redirects = {
        **blog_redirects,
        **eecs281_redirects,
        "resume": "https://resume.waleedkhan.name/",
    }
    return redirects


def make_redirect_html(path: str, target_url: str) -> str:
    return f"""\
<!DOCTYPE html>
<head>
<meta http-equiv="refresh" content="0; url={target_url}">
<link rel="canonical" href="{target_url}" />
</head>
<body>
<p>This page has moved to <a href="{target_url}">{target_url}</a>.
</body>
"""


def main() -> None:
    infos = {
        **get_blog_info(),
        **get_github_info(),
        **get_resume_info(),
        **get_linkedin_info(),
        **get_stack_overflow_info(),
        **get_restaurant_info(),
        **get_last_updated_info(),
    }
    with open("index.template.html") as f:
        template_html = f.read()
    for k, v in infos.items():
        k = "{" + k + "}"
        template_html = template_html.replace(k, v)

    shutil.rmtree("_site", ignore_errors=True)
    os.mkdir("_site")
    with open("_site/index.html", "w") as f:
        f.write(template_html)

    for path, target_url in get_redirects().items():
        os.makedirs(f"_site/{path}", exist_ok=True)
        with open(f"_site/{path}/index.html", "w") as f:
            f.write(make_redirect_html(path, target_url))

    for static_file in os.listdir("_static"):
        shutil.copy(src=os.path.join("_static", static_file), dst="_site")


if __name__ == "__main__":
    main()

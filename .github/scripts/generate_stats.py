import os
import requests
import sys

# --- Configuration ---
USERNAME = "wyqmath"
TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    raise ValueError("A GITHUB_TOKEN is required to run this script.")

# --- API Headers ---
HEADERS = {
    "Authorization": f"bearer {TOKEN}",
    "Content-Type": "application/json",
}

def run_graphql_query(query):
    request = requests.post("https://api.github.com/graphql", json={"query": query}, headers=HEADERS)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(f"Query failed to run by returning code of {request.status_code}. {query}")

def get_total_stars():
    """
    Smartly fetches total stars by combining:
    1. Repositories you own or collaborate on (Write access).
    2. Repositories you have pinned to your profile (covers external contributions).
    """
    unique_repos = {}

    # Query 1: Owned, Member, and Collaborator repositories
    # We remove 'isFork: false' to include forks you maintain if they have stars
    query_owned = f"""
    query {{
      user(login: "{USERNAME}") {{
        repositories(first: 100, ownerAffiliations: [OWNER, ORGANIZATION_MEMBER, COLLABORATOR]) {{
          nodes {{
            nameWithOwner
            stargazerCount
          }}
        }}
      }}
    }}
    """

    # Query 2: Pinned repositories (This fixes the missing mindspore-lab/models issue)
    query_pinned = f"""
    query {{
      user(login: "{USERNAME}") {{
        pinnedItems(first: 6, types: [REPOSITORY]) {{
          nodes {{
            ... on Repository {{
              nameWithOwner
              stargazerCount
            }}
          }}
        }}
      }}
    }}
    """

    # Process Owned/Collaborator Repos
    try:
        res_owned = run_graphql_query(query_owned)
        if res_owned.get("data", {}).get("user"):
            for repo in res_owned["data"]["user"]["repositories"]["nodes"]:
                unique_repos[repo["nameWithOwner"]] = repo["stargazerCount"]
    except Exception as e:
        print(f"Warning: Failed to fetch owned repos: {e}")

    # Process Pinned Repos
    try:
        res_pinned = run_graphql_query(query_pinned)
        if res_pinned.get("data", {}).get("user"):
            for repo in res_pinned["data"]["user"]["pinnedItems"]["nodes"]:
                # If it's already in the dict, it updates (or stays same); if new, it adds.
                unique_repos[repo["nameWithOwner"]] = repo["stargazerCount"]
    except Exception as e:
        print(f"Warning: Failed to fetch pinned repos: {e}")

    # Optional: Manual Whitelist (Hardcode specific repos if pinning fails)
    # If you haven't pinned it yet, this line ensures it's counted.
    # You can remove this block if you are sure you pinned 'mindspore-lab/models'
    manual_whitelist = ["mindspore-lab/models"]
    for repo_name in manual_whitelist:
        if repo_name not in unique_repos:
            try:
                owner, name = repo_name.split('/')
                q_manual = f"""query {{ repository(owner: "{owner}", name: "{name}") {{ stargazerCount }} }}"""
                res_manual = run_graphql_query(q_manual)
                if res_manual.get("data", {}).get("repository"):
                    unique_repos[repo_name] = res_manual["data"]["repository"]["stargazerCount"]
            except Exception:
                pass # Ignore errors for whitelist

    return sum(unique_repos.values())

def get_contribution_stats():
    # (Keep your original logic here, it was fine)
    from datetime import datetime
    
    creation_query = f"""
    query {{
        user(login: "{USERNAME}") {{
            createdAt
        }}
    }}
    """
    creation_result = run_graphql_query(creation_query)
    creation_date_str = creation_result["data"]["user"]["createdAt"]
    creation_date = datetime.strptime(creation_date_str, "%Y-%m-%dT%H:%M:%SZ")
    creation_year = creation_date.year
    current_year = datetime.now().year

    total_contributions = 0

    for year in range(creation_year, current_year + 1):
        from_date = f"{year}-01-01T00:00:00Z"
        to_date = f"{year}-12-31T23:59:59Z"
        if year == current_year:
            to_date = datetime.utcnow().isoformat(timespec='seconds') + 'Z'

        contrib_query = f"""
        query {{
          user(login: "{USERNAME}") {{
            contributionsCollection(from: "{from_date}", to: "{to_date}") {{
              contributionCalendar {{
                totalContributions
              }}
            }}
          }}
        }}
        """
        result = run_graphql_query(contrib_query)
        if result.get("data", {}).get("user"):
            collection = result["data"]["user"]["contributionsCollection"]
            if collection.get("contributionCalendar"):
                total_contributions += collection["contributionCalendar"].get("totalContributions", 0)

    return total_contributions

def generate_svg_badge(stars, contributions):
    def format_number(n):
        if n >= 1000:
            return f"{n/1000:.1f}k"
        return str(n)

    display_stars = format_number(stars)
    display_contributions = format_number(contributions)

    svg_template = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="320" height="70" role="img">
        <title>GitHub Stats</title>
        <style>
            .card {{
                fill: #ffffff;
                stroke: #e2e8f0;
                stroke-width: 1;
                rx: 4.5;
            }}
            .label {{ font: 600 13px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif; fill: #4f46e5; text-anchor: start; }}
            .value {{ font: 600 13px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif; fill: #1f2937; text-anchor: end; }}
        </style>
        <rect class="card" width="319" height="69" />
        <g transform="translate(20, 25)">
            <text class="label">Total Stars</text>
            <text class="value" x="280" y="0">{display_stars}</text>
        </g>
        <g transform="translate(20, 50)">
            <text class="label">Total Contributions</text>
            <text class="value" x="280" y="0">{display_contributions}</text>
        </g>
    </svg>
    """
    return svg_template.strip()

if __name__ == "__main__":
    try:
        # Updated logic for stars
        total_stars = get_total_stars()
        # Original logic for contributions
        total_contributions = get_contribution_stats()
        
        svg_content = generate_svg_badge(total_stars, total_contributions)
        
        output_dir = "generated"
        os.makedirs(output_dir, exist_ok=True)
        
        with open(os.path.join(output_dir, "total-stars.svg"), "w") as f:
            f.write(svg_content)
            
        print(f"Successfully generated SVG with {total_stars} stars and {total_contributions} contributions.")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

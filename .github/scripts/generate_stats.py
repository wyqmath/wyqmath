import os
import requests
import sys
from datetime import datetime

# --- Configuration ---
USERNAME = "wyqmath"
# The GITHUB_TOKEN is provided by GitHub Actions
TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    raise ValueError("A GITHUB_TOKEN is required to run this script.")

# --- API Headers ---
HEADERS = {
    "Authorization": f"bearer {TOKEN}",
    "Content-Type": "application/json",
}

def run_graphql_query(query):
    """Helper function to run a GraphQL query."""
    request = requests.post("https://api.github.com/graphql", json={"query": query}, headers=HEADERS)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(f"Query failed to run by returning code of {request.status_code}. {query}")

def get_contribution_stars():
    """
    Fetches all repositories a user has contributed to and sums their stars.
    This includes owned repos and repos contributed to.
    It uses a set to avoid double-counting.
    """
    # Repositories the user owns
    owned_repos_query = f"""
    query {{
      user(login: "{USERNAME}") {{
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {{
          nodes {{
            nameWithOwner
            stargazerCount
          }}
        }}
      }}
    }}
    """
    
    # Repositories the user has made commits or PRs to
    contributed_repos_query = f"""
    query {{
      user(login: "{USERNAME}") {{
        repositoriesContributedTo(first: 100, contributionTypes: [COMMIT, PULL_REQUEST]) {{
          nodes {{
            nameWithOwner
            stargazerCount
          }}
        }}
      }}
    }}
    """

    # Using a dictionary to store unique repos and their star counts
    unique_repos = {}

    # Fetch and process owned repositories
    owned_result = run_graphql_query(owned_repos_query)
    if owned_result.get("data", {}).get("user"):
        for repo in owned_result["data"]["user"]["repositories"]["nodes"]:
            unique_repos[repo["nameWithOwner"]] = repo["stargazerCount"]

    # Fetch and process contributed-to repositories
    contrib_result = run_graphql_query(contributed_repos_query)
    if contrib_result.get("data", {}).get("user"):
        for repo in contrib_result["data"]["user"]["repositoriesContributedTo"]["nodes"]:
            unique_repos[repo["nameWithOwner"]] = repo["stargazerCount"]

    # Sum the stars from all unique repositories
    total_stars = sum(unique_repos.values())
    
    return total_stars, unique_repos

def get_contribution_stats():
    """
    Fetches all-time contribution stats for a user (total contributions).
    It iterates through each year of the user's membership.
    """
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
    """Generates an SVG badge image with multiple stats."""
    
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
        total_stars, unique_repos = get_contribution_stars()
        total_contributions = get_contribution_stats()
        
        svg_content = generate_svg_badge(total_stars, total_contributions)
        
        # Ensure the output directory exists
        output_dir = "generated"
        os.makedirs(output_dir, exist_ok=True)
        
        # Write the SVG to a file
        with open(os.path.join(output_dir, "total-stars.svg"), "w") as f:
            f.write(svg_content)
            
        print(f"Successfully generated SVG with {total_stars} stars and {total_contributions} contributions.")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)
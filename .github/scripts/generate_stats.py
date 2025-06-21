import os
import requests
import sys

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
    
    return total_stars

def generate_svg_badge(stars_count):
    """Generates an SVG badge image with the star count."""
    # Simple SVG badge template
    # You can customize colors, fonts, and layout here
    if stars_count >= 1000:
        display_stars = f"{stars_count/1000:.1f}k"
    else:
        display_stars = str(stars_count)

    svg_template = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="210" height="28" role="img" aria-label="Total Contribution Stars: {display_stars}">
        <title>Total Contribution Stars: {display_stars}</title>
        <style>
            .text {{ font: 600 12px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif; fill: #fff; }}
        </style>
        <rect width="155" height="28" fill="#555" rx="4.5" />
        <rect x="155" width="55" height="28" fill="#007ec6" rx="4.5" />
        <rect x="155" width="55" height="28" fill="url(#gradient)" rx="4.5" />
        <defs>
            <linearGradient id="gradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#007ec6"/>
                <stop offset="100%" stop-color="#2ca0d9"/>
            </linearGradient>
        </defs>
        <g class="text" text-anchor="middle">
            <text x="77.5" y="17.5">Total Contribution Stars</text>
            <text x="182.5" y="17.5">{display_stars}</text>
        </g>
    </svg>
    """
    return svg_template.strip()

if __name__ == "__main__":
    try:
        total_stars = get_contribution_stars()
        svg_content = generate_svg_badge(total_stars)
        
        # Ensure the output directory exists
        output_dir = "generated"
        os.makedirs(output_dir, exist_ok=True)
        
        # Write the SVG to a file
        with open(os.path.join(output_dir, "total-stars.svg"), "w") as f:
            f.write(svg_content)
            
        print(f"Successfully generated SVG with {total_stars} total stars.")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)
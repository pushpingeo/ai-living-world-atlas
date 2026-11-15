# Atlas MCP server (private)

A Cloudflare Worker that lets AI agents search the atlas. It needs a key for now.

Tools: `find_datasets`, `get_dataset`, `fetch_features`, `vocabulary`.

## Connecting

Endpoint: `https://atlas-mcp.<your-subdomain>.workers.dev/mcp`

- **Claude Code:** `claude mcp add --transport http atlas <endpoint> --header "Authorization: Bearer <key>"`
- **Claude desktop or web (custom connector):** use `<endpoint>?key=<key>` as the URL. The key in a URL is less private than a header; fine while it's just us, and the key can be rotated by changing the `ATLAS_MCP_KEY` secret and re-running the deploy.

## Deploying

`.github/workflows/deploy-mcp.yml` deploys on changes here, and reloads the database after every Pages rebuild (so after each crawl or tagging run). It needs the repo secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` and `ATLAS_MCP_KEY`.

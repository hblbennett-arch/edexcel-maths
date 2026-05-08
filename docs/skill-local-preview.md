# Skill: Local Preview Server

## When to Use
When the user wants to view/test the site locally before pushing.

## Start Server
```bash
python3 -m http.server 8765 --directory /Users/i1003721/edexcel-maths &>/dev/null &
```

## Open in Browser
```bash
open http://localhost:8765/output/index.html        # A Level
open http://localhost:8765/output-as/index.html     # AS Level
open http://localhost:8765/output-as/topics/coordinate-geometry-circles.html  # specific page
```

## Kill Server
```bash
lsof -ti:8765 | xargs kill 2>/dev/null
```

## Notes
- Playwright MCP can't access `file://` URLs — must use HTTP server
- Port 8765 chosen to avoid conflicts
- Use `open` command on macOS to launch in default browser
- GitHub Pages takes 1-2 minutes to deploy after push; local preview is instant

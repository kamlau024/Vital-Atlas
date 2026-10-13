# Diagrams

Generated with [Archify](https://github.com/tt-a1i/archify) from the code at commit
`ce2bc11`. Every step and component cites the source lines it was drawn from.

| Diagram | Type | Shown in the main README under |
|---|---|---|
| `architecture` | architecture | How a crawl works |
| `scroll-capture` | workflow | Virtualized List Handling |
| `change-detection` | workflow | Change Detection |

For each diagram, this folder holds:

- `<name>.light.svg` and `<name>.dark.svg`: the images embedded in the main README
- `<name>/<name>.html`: the interactive version; download and open it in a browser to search, focus, and follow source links
- `<name>/candidate.json`: the diagram source

## Regenerating after a code change

1. Edit the `candidate.json`: set `meta.repository.revision` to the new commit (it must be
   pushed, or the source links won't resolve) and fix any `sources` line ranges that moved.
2. From the repository root, run:

   ```bash
   node <archify>/bin/archify.mjs finalize workflow docs/diagrams/scroll-capture/candidate.json docs/diagrams/scroll-capture/scroll-capture.html --repo-root . --quality showcase
   ```

   Use `architecture` as the type for the architecture diagram. `finalize` checks every
   source reference against that commit and renders the page in headless Chrome.
3. Open the HTML, choose **Export → SVG · Light** and **Export → SVG · Dark**, and save
   them over the SVGs in this folder.

The check receipts and screenshots that `finalize` writes are git-ignored because they
contain local paths.

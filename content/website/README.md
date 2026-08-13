# Website content

This directory is the Git-backed CMS source for the Portal website. It is
deliberately file-based: content changes are reviewed, versioned, and released
through normal Git workflows. There is no browser editor or CMS API.

## Layout

- `homepage/`: public homepage copy and supporting sections, localized under
  `zh/` and `en/`.
- `product/`: product marketing copy.
- `docs/`, `doc/`, and `blogs/`: website documentation and editorial content.
- `about/`: company and team copy.
- `content-manifest.yaml`: the source contract consumed by Portal builds.

## Publishing

1. Edit the Markdown/YAML source here on a branch.
2. Validate from the Portal checkout with `yarn content:validate` after pulling
   this directory into `src/content`.
3. Merge the content change and run the Portal build pipeline with this
   repository, branch, and `content/website` subdirectory configured as the
   content backend.

Portal copies this directory into its build workspace before it generates
typed content artifacts. The resulting image therefore contains an immutable
snapshot of this Git revision; a later content change requires a new build and
deployment.

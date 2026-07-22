# Maintaining the fork

This repository is a packaging and Windows-support fork of
[`danini/superansac`](https://github.com/danini/superansac). The last upstream
commit in the fork's first-parent history before the Windows changes is:

```text
27de48676f07704856fb5619dd31cde807d0661d
```

The wheel hardening work started from fork release `v1.0.0-rc.2` at
`35d781ab49c6e807eb0b8308f95bfd8fbe691c39`. Keep both identifiers in release
notes so an artifact can be reconstructed without relying on a moving branch.

## Refresh procedure

1. Add or update the upstream remote and fetch it without modifying the
   release branch.

   ```bash
   git remote add upstream https://github.com/danini/superansac.git
   git fetch --tags upstream
   ```

2. Create a dedicated refresh branch from the current fork main branch. Merge
   or cherry-pick the intended, explicitly recorded upstream commit. Do not
   follow upstream `main` implicitly in packaging metadata or CI.

3. Review every newly introduced vendored source and its license before
   building. In particular, do not reintroduce the removed `GCoptimization`,
   legacy `energy`, or legacy Boykov-Kolmogorov source bundle. Add new linked
   dependencies to `THIRD_PARTY_NOTICES.md`, the license expression, and the
   wheel/vcpkg license audits.

4. Re-run the C++ binary-energy tests, Linux installed-wheel tests, all three
   Windows wheel jobs, dependency/path/license audits, reproducibility check,
   and the rc.2 performance comparison.

5. Update the upstream commit in this document and release notes only after the
   refresh pull request passes. Do not replace assets in an existing release;
   issue a new prerelease tag.

The vcpkg baseline is independently pinned in `vcpkg.json`. Update it in a
separate, reviewable change and record all newly resolved target libraries and
licenses.

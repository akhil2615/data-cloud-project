# ADR 0007: Version alignment

Status: proposed

`sfdx-project.json` is API 68.0, which DC1 sandbox reports as its latest release. Before each production run, compare sandbox and prod API versions. If the sandbox is newer, rebuild the kit or wait.

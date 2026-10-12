# ADR 0007: Version alignment

Status: proposed

`sfdx-project.json` is API 68.0, which the build sandbox reports as its latest release. Before each production run, compare the build sandbox, the deployment sandbox, and production. If the build sandbox is newer than production, rebuild the kit or wait.

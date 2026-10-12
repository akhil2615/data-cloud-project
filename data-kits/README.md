# Kit matrix

`kit-matrix.yaml` is the list of spaces, the order for each space, and the kit version to deploy.

- `inventory: seeded` means the kits below are real names waiting for a UI manifest.
- `inventory: not-seeded` means the space exists in DC1 sandbox and the layers are not filled in yet.
- `inventory: awaiting-name` is the 31st row. The sandbox API returned 30 spaces.
- An empty list means that layer is confirmed not applicable.
- `10b` is the external-target API step. It is never a kit.

See `docs/CICD_PROCESS.md`.

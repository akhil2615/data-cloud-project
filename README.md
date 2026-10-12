# Data Cloud sandbox to production

This repository promotes Data Cloud kits from DC1 sandbox to DC1 prod.

Read [docs/CICD_PROCESS.md](docs/CICD_PROCESS.md) for the full process, including how it matches the deployment diagram, the layer order, and the automation.

```bash
python scripts/validate_repo.py
python scripts/update-space-status.py
```

Kit manifests in `manifest/kits/` are placeholders until they are downloaded from the Data Kit UI. Do not deploy them.

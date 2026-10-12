# ADR 0001: Deploy method

Status: proposed

Plain `sf project deploy start --source-dir` is the default because the retrieved kit lives in its own folder. The Connect API deploy is available with `--method connect-api` for the pilot. Do not accept one method until a small kit is deployed and `DataPackageKitDefinition` is queried in the target.

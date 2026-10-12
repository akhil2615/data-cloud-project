# Data Cloud CI/CD process

This is the process for building Data Cloud (Data 360) configuration in the sandbox, reviewing it in Git, deploying it to the test sandbox, and promoting it to production.

Share this file with the team. The repository around it is the automation: folder layout, kit matrix, scripts, and GitHub Actions.

## How this matches the deployment diagram

The diagram has two homes and one promotion path between them.

| Diagram | This repository |
|---|---|
| Development / Home Dev, fed by Org 1 CRM, Org 2 OCRM, Org 3 MBCRM | DC1 sandbox. Those three orgs are source systems connected to Home Dev. They are not Data Cloud orgs and they are not Git branches. |
| Data Kit creation for the required deployment | A fresh DevOps kit is created in the Data Kit UI for one data space and one layer. |
| Extract the manifest file locally | Download the manifest, then `scripts/retrieve-kit.sh` retrieves it into `data-cloud/<space>/<kit>/`. |
| Commit to Git feature/dev/qa branch | `feature/<space>-<kit>-<description>` |
| Pull request to the release branch | Pull request into `release` |
| Review and four-eyes principle | Two approving reviews. Branch protection on `release` must require 2 approvals. |
| Merge with the release branch | Merge. The `deploy-test` workflow starts. |
| Push the manifest to the test sandbox and deploy | `deploy-test.yml` deploys the changed kits to DC1 sandbox, in that space's layer order. |
| Post deployment steps | Publish identity resolution, activate prediction jobs, publish parent segments, recreate external activation targets, and wait until components are active. |
| Home Prod, fed by the prod CRM / OCRM / MBCRM orgs | DC1 prod. Connectors there must use the same API names as the sandbox. |
| Core deployment process | `deploy-prod.yml`, started manually from the release branch after the post-deploy checks pass. `main` is updated only after prod is confirmed. |

Two Data Cloud orgs exist today: DC1 sandbox and DC1 prod. In the diagram, Home Dev and the test-sandbox deploy are both DC1 sandbox. Home Prod is DC1 prod. The test deploy still matters: it deploys the retrieved manifest and proves the package, the cleanup, and the layer order. It does not prove a brand-new org, because the kit was created in that same sandbox.

## What moves, and what does not

A kit moves metadata: streams, DLOs, mappings, relationships, transforms, identity resolution, calculated insights, segments, Marketing Cloud targets and activations, and data graphs.

A kit does not move data, connector passwords, or external-platform credentials. CRM, OCRM, MBCRM, Marketing Cloud, Databricks, and SFTP connections must already exist in the target and use the same API names as the sandbox.

External audience targets (Meta, Meta CAPI, Google Ads, DV360, Amazon Ads) are recreated in prod by `scripts/recreate-external-targets.py`. They are not a kit.

## Kit layers

The default order is below. A data space lists only the layers it uses, and it can reorder them in `data-kits/kit-matrix.yaml`.

| Step | Kit | Contents | When it applies |
|---|---|---|---|
| 01 | One stream bundle per source | Streams, DLOs, DLO–DMO mappings, data space membership, DMO–DMO relationships | Sources: mbcrm, ocrm, amg, marketing-cloud, ucp-databricks, vans-databricks, sftp, file-upload. Not every source exists in every space. The amg source is only in the AMG space. |
| 02 | Custom DLOs | DLOs, mappings, membership, relationships | Per space |
| 02b | AI models and prediction jobs | Prediction models and jobs | Only spaces that have them |
| 03 | Transforms | DLO-based and DMO-based transforms. A DMO-based transform also creates its output DMO. | Transforms that only need objects from steps 01 and 02 |
| 04 | Identity resolution | Ruleset | Per space. Publish it before anything reads unified DMOs. |
| 05 | Standalone calculated insights | Insights with no nested dependency | Only spaces that have them |
| 06 | Nested calculated insights | Insights that depend on other insights | Only spaces that have them |
| 07 | Standalone segments | No dependencies | Per space |
| 08 | Dependent segments | Depend on insights or other segments | Only spaces that have them. Publish membership parents first. |
| 09 | Marketing Cloud activation targets | MC targets | Per space |
| 10 | Marketing Cloud activations | Activations on the MC targets | Per space |
| 10c | Dependent transforms | Transforms that read unified DMOs, insight outputs, segment DMOs, or activation DMOs | Only spaces that have them. Always after step 10. |
| 10b | Not a kit. API script. | Recreate external audience targets in prod | Only when the space has external activations, and only against prod |
| 11 | External activations | Meta, Meta CAPI, Google Ads, DV360, Amazon Ads, and similar | Only spaces that have them |
| 12 | Data graphs | For example France | Only spaces that have them |

Name every kit `DK<layer>_<scope>_<space>_v<n>`, for example `DK05_ci-standalone_france_v1`.

Create a new version for every deployment (`_v2`, `_v3`). Do not edit kit XML by hand. Creating the kit in the UI does not deploy it.

## Per-space order

`layers_order` in the matrix is the default. Each space can set `order`. A layer that is absent, or set to an empty list, is skipped.

Germany needs AI before early transforms, and a dependent transform after Marketing Cloud activations:

```yaml
germany:
  order: ["01", "02", "02b", "03", "04", "05", "06", "07", "08", "09", "10", "10c"]
```

France has no AI kit and adds data graphs at the end:

```yaml
france:
  order: ["01", "02", "03", "04", "05", "07", "08", "09", "10", "10b", "11", "12"]
```

The pipeline reads that list. It does not assume every space follows the same sequence.

## Repository layout

```text
data-cloud-project/
  docs/CICD_PROCESS.md          This process
  data-kits/kit-matrix.yaml     Space, layer, kit name, version, order
  manifest/kits/<kit>.xml       Manifest downloaded from the Data Kit UI
  data-cloud/<space>/<kit>/     Retrieved kit. One folder per kit.
  force-app/                    CRM metadata only (flows, reports, Apex)
  api-payloads/10b-external-targets/
  scripts/                      retrieve, cleanup, deploy, validate
  .github/workflows/            Pull request, test deploy, prod deploy
  deployment-state/             Resume ledger. Not edited by hand.
```

Shared components are copied into each kit folder that contains them. That is intentional: one retrieve must not overwrite another kit. After the first production pilot, decide whether to switch to a single object-level folder.

## Branches

| Branch | Role |
|---|---|
| `feature/<space>-<kit>-<description>` | Retrieve, cleanup, and the pull request. This is the feature/dev/qa branch on the diagram. |
| `release` | Reviewed kits. A merge deploys to the test sandbox. |
| `main` | What DC1 prod last received. Updated only after the core deployment is confirmed. |
| `hotfix/*` | Cut from `main`, then merged back to `release` and `main`. |

No permanent branch per data space. While nothing is in flight, the repository has `main` and `release`.

Four eyes means two people approve the pull request into `release`. GitHub cannot store that rule inside the repo files. After the repo is on GitHub, set branch protection on `release` and `main`:

- pull request required
- 2 approving reviews
- the `validate` check must pass
- CODEOWNERS review on `data-kits/` and `.github/`

## Pipeline

### 1. Feature pull request

`validate-pr.yml` runs on every pull request into `release`.

- repository rules (`scripts/validate_repo.py`)
- XML formatting
- `cleanup-kit.sh` has no remaining `KQ_*` fields, empty CustomObject labels, or managed-package components
- dependency check
- package under 50 MB (52,428,800 bytes)
- check-only deploy to the test sandbox when `SF_AUTH_URL` is configured and the metadata type supports `--dry-run`

The pull request does not install the kit.

### 2. Merge to release: test sandbox

`deploy-test.yml` runs on a push to `release`.

It deploys only the kits changed in that merge, in the order declared for their data space. It does not deploy all 30 spaces.

For each kit it:

1. deploys the retrieved folder with the Salesforce CLI
2. runs `sf project deploy report`
3. checks that the kit components exist in the target
4. waits until they are active, or stops on a post-deploy gate

A CLI status of Succeeded is not enough. If the report succeeds and the components are missing, the job fails.

### 3. Post deployment steps

The test job stops at a gate instead of guessing that a manual step happened.

| After | Gate |
|---|---|
| 02b | Activate the prediction job so the score DMO exists |
| 04 | Publish identity resolution so unified DMOs exist |
| 07 | Publish membership-parent segments |
| 10 | Dependent transforms in 10c may now run |
| 10b | Recreate external audience targets in prod, then run layer 11 |

When the gate is done, rerun with the resume ledger. Completed kits are skipped only when the Git commit and kit version still match.

### 4. Core deployment to production

`deploy-prod.yml` is started by hand from `release`.

Inputs: data space, optional kit, dry run.

It uses the GitHub Environment `prod` (required reviewers) and the concurrency group `prod-deploy`, so two production deployments cannot run together.

The job runs one space, or one kit, never all spaces at once. Then it compares sandbox and prod counts, updates `docs/space-status.md`, tags `kit-<layer>-v<n>`, and appends `CHANGELOG.md`.

After that job is green, merge `release` into `main`. `main` is the retrace point for production.

## Waves

| Wave | Spaces | Purpose |
|---|---|---|
| 0 | `default` and one small space, every layer that space uses | Prove retrieve, cleanup, test deploy, gates, and prod |
| 1 | Spaces with streams, insights, and segments only | No AI, graphs, dependent transforms, or external audiences |
| 2 | Spaces with nested insights or dependent segments | Proves publish gates |
| 3 | Spaces with AI, 10c transforms, data graphs, or external audiences | Uses the API step for external targets |

## One kit, from the UI to production

1. In DC1 sandbox, create a fresh DevOps kit. Add the data space and the components. Run View/Add Dependencies. Check the publish sequence.
2. Download the manifest into `manifest/kits/<kit>.xml`. Replace the placeholder file. Do not hand-write members.
3. `scripts/retrieve-kit.sh <kit> dc1-sandbox`
4. `scripts/cleanup-kit.sh data-cloud/<space>/<kit>`
5. Commit on `feature/<space>-<kit>-<description>` and open a pull request into `release`.
6. Two reviewers approve. Merge.
7. The test workflow deploys to DC1 sandbox. Complete any gate it stops on.
8. Start the prod workflow for that space. Approve the `prod` environment.
9. Confirm the components in the prod UI. Merge `release` into `main`.

## Rollback

Rollback is a new forward deployment.

1. Find the last good tag.
2. Create a fresh kit version in the sandbox from that known state.
3. Retrieve, review, deploy to the test sandbox, then deploy to prod.
4. Do not assume an old XML file can be pushed over a kit that cached its version. Some components have no destructive undeploy.

## Local checks before you share the repo

From the repository root:

```bash
python scripts/validate_repo.py
python scripts/update-space-status.py
```

Salesforce commands need an authenticated CLI alias (`dc1-sandbox`, `dc1-prod`). GitHub Actions reads `SF_AUTH_URL` from the `test` and `prod` environments. Do not commit auth files, keys, or connector passwords.

## What was verified, and what is still a pilot

Verified against DC1 sandbox on 12 Oct 2026:

- Salesforce CLI `2.131.7`.
- Org API version `68.0` (`sf org display`, and `/services/data` lists `68.0` as Latest Release). `sfdx-project.json` uses `68.0`.
- `sf project retrieve start` supports `--manifest` and `--output-dir`. `--output-dir` cannot be a package directory, so retrieve uses a temp folder and then moves the files.
- `sf project deploy start` supports `--source-dir`, `--manifest`, `--metadata-dir`, `--dry-run`, and `--wait`. Check-only in this repo is `--dry-run`.
- `sf project deploy report` is the follow-up check. Case 473942263 is still unresolved: a CLI success has been reported without the kit objects landing. The scripts fail the job when the objects are absent.
- The sandbox data-spaces API returned **30** spaces, including `default`. The brief asked for 31. The matrix has those 30 plus an `unassigned` row until the missing name is supplied.
- The current Data 360 CLI guide says the manifest can be downloaded from the Data Kit UI or from the get-data-kit-manifest Connect API. A call to `/services/data/v68.0/ssot/data-kits/__probe_does_not_exist__/manifest` returned `NOT_FOUND`. That does not prove the route is absent, because a missing kit returns the same code. The default path remains the UI download.

Still a pilot, on one small kit, before the workflows lock a single method:

- plain CLI deploy versus the Connect API deploy (`POST /ssot/data-kits/{name}?asyncMode=true`) versus a JSON payload
- whether Marketing Cloud targets and activations actually install from a kit
- whether a batch transform that creates a DMO can deploy to prod
- whether two kits that contain the same DLO or DMO need a shared base kit
- whether check-only is honored for every Data Cloud type

Those decisions are recorded as proposed ADRs under `docs/adr/`. None of them is accepted yet.

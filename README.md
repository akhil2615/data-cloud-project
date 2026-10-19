# Data Cloud sandbox to production

This repository is the shared record of what we build in the build sandbox,
test in the deployment sandbox, and promote to production.

A worked example of “kit retrieve vs object retrieve” is in
[demo/git-demo-kit/README.md](demo/git-demo-kit/README.md). That demo uses the
sandbox kit `GIT_Demo_Kit` (AMG CRM Account and Contact).

You do not need to be a Git expert to use it. The process is:

```text
Build a fresh kit in the build sandbox
        ↓
Download its manifest and retrieve its files
        ↓
Save the files in Git and ask two people to review them
        ↓
Deploy the approved files to the deployment sandbox
        ↓
Complete the required publish/activation checks
        ↓
Deploy the same files to production
        ↓
Record the successful deployment in Git
```

The build sandbox and the deployment sandbox are different orgs. The kit is
created in the first one. The deployment sandbox is the real install test,
because that org did not create the kit. Production receives the files only
after that test succeeds.

## The Git words used here

- **Repository:** this shared project folder and its history.
- **Commit:** a saved version of the files.
- **Working branch:** a temporary copy where one kit is prepared without
  changing the approved files.
- **Pull request:** the page where teammates inspect the changes.
- **Release branch:** the approved copy that is ready for deployment.
- **Main branch:** the copy that represents what was successfully deployed to
  production.
- **Merge:** copying approved changes from one branch into another.

## How two-person approval works

1. The person preparing a kit creates a working branch, such as
   `feature/germany-ir-v1`.
2. They retrieve the kit, save it, and open a pull request into `release`.
3. Reviewer 1 opens **Files changed**, checks the files, and selects
   **Review changes → Approve**.
4. Reviewer 2 does the same.
5. After both approvals, an authorized person selects **Merge pull request**.
6. GitHub copies the kit into `release` and starts the test-sandbox workflow.

The reviewers do not deploy the kit themselves. They approve the exact files
that the automation will deploy.

GitHub branch protection must be configured to require two approvals. The
repository files cannot enforce that setting by themselves.

## Folder structure in plain language

```text
data-cloud-project/
├── manifest/kits/       Lists downloaded from the Data Kit UI
├── data-cloud/          The actual metadata retrieved from the sandbox
├── data-kits/           Which kits each data space uses and their order
├── api-payloads/        Templates for external activation targets
├── force-app/           CRM metadata, kept separate from Data Cloud kits
├── scripts/             Programs that retrieve, check and deploy kits
├── .github/workflows/   Instructions GitHub runs automatically
└── docs/                Detailed instructions and deployment status
```

### `manifest/kits/`: the shopping lists

Each Data Kit UI download is stored here:

```text
manifest/kits/
├── DK01_mbcrm_france_v1.xml
├── DK04_ir_france_v1.xml
└── DK07_segments_france_v1.xml
```

A manifest says which Salesforce metadata components belong to a kit. Never
invent or hand-write its members. Replace a placeholder with the manifest
downloaded from the Data Kit UI.

### `data-cloud/`: one data space, then one kit

```text
data-cloud/
├── france/
│   ├── DK01_mbcrm_france_v1/
│   ├── DK04_ir_france_v1/
│   └── DK07_segments_france_v1/
├── germany/
│   ├── DK01_mbcrm_germany_v1/
│   ├── DK02b_ai-models_germany_v1/
│   └── DK10c_dependent-transforms_germany_v1/
└── amg/
    └── DK01_amg_amg_v1/
```

The first folder is the data space. Inside it, each folder is one fresh Data
Kit version. A space contains only the kits it needs. For example, only the AMG
space gets an AMG source kit.

Every kit folder contains the real Salesforce metadata returned by
`sf project retrieve start`, such as:

```text
DK04_ir_france_v1/
├── dataPackageKitDefinitions/
├── DataPackageKitObjects/
└── dataKitObjectTemplates/
```

Keeping each retrieve in its own folder prevents one kit from overwriting
another kit.

### `data-kits/kit-matrix.yaml`: the deployment schedule

This file tells the automation:

- which kits apply to each data space;
- each kit's version;
- the order for that space;
- which optional layers are absent;
- where a manual publish or API step is required.

The normal layer order is:

```text
01 streams
02 custom DLOs
02b AI models and prediction jobs, when used
03 early transforms
04 identity resolution
05 standalone calculated insights
06 dependent calculated insights
07 standalone segments
08 dependent segments
09 Marketing Cloud targets
10 Marketing Cloud activations
10c transforms that need unified, CI, segment or activation DMOs
10b external targets created through the API
11 external activations
12 data graphs
```

Each space can skip layers or use a different order.

### `force-app/`: CRM metadata only

This repository is a Salesforce DX project. `sfdx-project.json` defines
`force-app` and `data-cloud` as project directories, and the scripts use
Salesforce CLI.

`force-app/main/default/` is reserved for normal CRM metadata such as flows,
reports, Apex, permission sets and Lightning components. Data Cloud kits stay
under `data-cloud/` and are deployed separately with Salesforce CLI.

## One kit from sandbox to production

1. In the build sandbox, create a **fresh DevOps Data Kit**, for example
   `DK04_ir_france_v1`.
2. Add the data space and components.
3. Run **View/Add Dependencies** and check the publish sequence.
4. Download the manifest to `manifest/kits/<kit>.xml`.
5. Retrieve the kit:

   ```bash
   scripts/retrieve-kit.sh DK04_ir_france_v1 dc1-build
   ```

6. Clean the retrieved files:

   ```bash
   scripts/cleanup-kit.sh data-cloud/france/DK04_ir_france_v1
   ```

7. Save the changes on a working branch and open a pull request into
   `release`.
8. Two teammates approve it. Merge the pull request.
9. GitHub deploys the changed kit to the deployment sandbox.
10. Complete any required gate, such as publishing identity resolution or
    publishing a parent segment.
11. Start the production workflow for that space or kit. A production
    approver authorizes it.
12. Confirm the deploy report and confirm the components in the production UI.
13. Merge the successful release into `main`.

## Do we update Git after deployment?

Yes. Git is updated at two different moments for two different reasons.

### Before deployment

The retrieved kit is committed before deployment. This records exactly what
we intend to deploy and lets two people review it.

```text
Working branch → pull request → release
```

### After the deployment-sandbox deployment

The deployment result and any completed gates are recorded in the deployment
status. If a fix is required, make the fix in a new commit and review that
change before trying again.

Do not edit metadata directly in the deployment sandbox and leave Git unchanged.

### After the production deployment succeeds

1. Record the production deployment ID, result, date and kit version.
2. Update `docs/space-status.md` and `CHANGELOG.md`.
3. Create a Git tag for the known production version.
4. Merge `release` into `main`.

```text
release ──successful production deployment──► main
```

After this, `main` is the answer to: **What should currently exist in
production?**

If production fails, do not merge the release into `main`. Fix the working
branch, repeat the review, and deploy again.

Normally, we do not retrieve production back into Git after every deployment.
We deploy the already-reviewed files and verify that they landed. A separate
drift check can retrieve or compare production if someone may have changed it
manually.

## Important safety rules

- Always create a fresh kit version (`v1`, `v2`, `v3`) for a deployment.
- Always retrieve before deploying.
- Never hand-edit the kit XML or manifest members.
- Never commit passwords, access tokens, auth files or connector credentials.
- A Salesforce CLI status of `Succeeded` is not enough. Run the deployment
  report and confirm the components exist in the target.
- Wait for each layer to become active before deploying something that depends
  on it.
- Do not deploy placeholder manifests.

## Current repository status

The initial folders and automation are present. The example manifests are
placeholders; no real Data Kit has been deployed from this repository yet.

The DC1 sandbox API returned 30 data spaces, including `default`. The matrix
contains those 30 spaces and one `unassigned` row until the expected 31st space
is identified.

For the detailed technical process, decisions and known pilot items, read
[docs/CICD_PROCESS.md](docs/CICD_PROCESS.md).

## Local validation

From the repository root:

```bash
python scripts/validate_repo.py
python scripts/update-space-status.py
```

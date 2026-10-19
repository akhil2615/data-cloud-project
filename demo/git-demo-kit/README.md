# Demo: kit retrieve vs object retrieve

This folder is a live example from DC1 sandbox kit **GIT Demo Kit** (`GIT_Demo_Kit`).
It shows why Git should store the **real objects**, not the Data Kit wrapper files.

Two teammates would review the files in `retrieved-objects/`.
The kit is still how the next org is updated. It is not what we version as the source.

## What we did

1. Created a DevOps Data Kit in the build sandbox and added AMG CRM Account and Contact.
2. Downloaded the kit manifest (`package.xml`).
3. Retrieved **twice** from the same org:

| Folder | Command idea | What it is |
|---|---|---|
| `retrieved-kit-as-is/` | retrieve using `1-kit-manifest.xml` | The kit box: templates, dependencies, timestamped kit objects |
| `retrieved-objects/` | retrieve using `2-objects-manifest.xml` | The live streams and DLOs via the Metadata API |

## The naming problem (kit as-is)

These names came from the kit. They are not the names you use in the org:

```text
GIT_Demo_Kit_1792413264568     kit wrapper
GIT_Demo_Kit_1792413265614     kit wrapper
GIT_Demo_Kit_1792413266731     kit wrapper
Account_AMGCRM1                object template
Account_AMGCRM2                data source object
Account_AMGCRM_1792413265630   stream template
```

The live objects are:

```text
Account_AMGCRM                 data stream
Account_AMGCRM__dll            data lake object
Contact_AMGCRM
Contact_AMGCRM__dll
Salesforce_AMGCRM              data source
amgcrm                         stream bundle
```

If you commit the kit retrieve, every new kit version looks like a huge rename because the numbers change. The Account and Contact definitions may not have changed at all.

Open these two files side by side:

- Kit wrapper: `retrieved-kit-as-is/DataPackageKitObjects/GIT_Demo_Kit_1792413265614.DataPackageKitObject-meta.xml`
- Live stream: `retrieved-objects/dataStreamDefinitions/Account_AMGCRM.dataStreamDefinition-meta.xml`

The wrapper only points at a template named `Account_AMGCRM1`.
The stream file is the real Account ingest definition.

## What Git should hold after this demo

```text
manifest/kits/GIT_Demo_Kit.xml     membership list (who is in the kit)
retrieved-objects/                 the files reviewers inspect
```

After two approvals, create or install a Data Kit in the **deployment sandbox** from that membership list. Do not treat the timestamped wrapper files as the source of truth.

## How to repeat the retrieves

From the repository root, against the build sandbox:

```bash
sf project retrieve start --manifest demo/git-demo-kit/1-kit-manifest.xml --target-org DC1SBX --output-dir demo/git-demo-kit/retrieved-kit-as-is
sf project retrieve start --manifest demo/git-demo-kit/2-objects-manifest.xml --target-org DC1SBX --output-dir demo/git-demo-kit/retrieved-objects
```

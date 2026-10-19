# Demo: same components, second kit (`Git_Demo_kit_2`)

Same Account and Contact AMG CRM components as `GIT_Demo_Kit`, packaged again.
The **live objects did not change**. The **kit wrapper names did**.

## Kit as-is names: kit 1 vs kit 2

| Kind | First kit (`GIT_Demo_Kit`) | Second kit (`Git_Demo_kit_2`) |
|---|---|---|
| Kit object | `GIT_Demo_Kit_1792413265614` | `Git_Demo_kit_2_1792415102289` |
| Stream template | `Account_AMGCRM_1792413265630` | `Account_AMGCRM_1792415102312` |
| Object template | `Account_AMGCRM1` | `Account_AMGCRM2` |
| Data source object | `Account_AMGCRM2` | `Account_AMGCRM3` |
| Bundle | `amgcrm` | `amgcrm1` |
| Connector dependency | `SalesforceDotCom_AMGCRM5` | `SalesforceDotCom_AMGCRM7` |

If Git stored kit retrieves, this second kit would look like a full replace.

## Retrieved metadata (unchanged)

These names are the same as kit 1:

```text
Account_AMGCRM
Contact_AMGCRM
Account_AMGCRM__dll
Contact_AMGCRM__dll
Salesforce_AMGCRM
```

That is what reviewers should approve. The next org still gets a Data Kit install.

Pull requests:

- Option 1 (kit wrappers): compare `feature/demo-kit-2-as-is` into `release`
- Option 2 (live objects): compare `feature/demo-kit-2-objects` into `release`

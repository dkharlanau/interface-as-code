# SAP integration profile

The optional `profiles.sap` extension records SAP-specific identifiers without contaminating the vendor-neutral core: integration style/technology, Integration Assessment reference, Cloud Integration package/iFlow, AIF namespace/interface, DRF outbound implementation and runtime artifact ID.

```bash
interface-as-code sap-summary examples/sap-mdg-to-s4-customer/interface.yaml
interface-as-code sap-import-metadata interface.yaml exported-sap-metadata.yaml -o enriched.yaml
```

The repository includes three SAP scenarios: IDoc/AIF/DRF-style customer replication, synchronous OData product API, and event-driven order publication through SAP Event Mesh. They require no SAP tenant.

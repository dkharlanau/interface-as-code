# Bootstrap an existing interface inventory

Most enterprise interface catalogs start in Excel. Export the sheet as CSV, then run:

```bash
interface-as-code import-csv interface-list.csv interfaces/
interface-as-code validate interfaces/
interface-as-code check interfaces/
```

Recognized canonical columns include `interface_id`, `name`, `source`, `target`, `protocol`, `mode`, `owner`, `business_owner`, `technical_owner`, `support_route`, `criticality`, `business_key`, `middleware`, `frequency` and `reconciliation_frequency`.

Use `--columns columns.yaml` when the source headers differ and `--normalize-systems systems.yaml` to map inconsistent system labels. Missing operational data is emitted as explicit TODO placeholders and recorded in `import-report.json`; the importer never invents an owner, replay process or business key.

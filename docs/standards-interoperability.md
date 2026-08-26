# Standards interoperability

Interface as Code is deliberately not a replacement for OpenAPI or AsyncAPI. Use their documents as authoritative contract artifacts and import/link only the metadata needed by the operational contract.

```bash
interface-as-code import-openapi api.yaml interfaces/order --id ORDER-API-01 --source Portal --target OMS
interface-as-code import-asyncapi asyncapi.yaml interfaces/order-event --id ORDER-EVENT-01 --source SAP-S4 --target Fulfillment
```

Arazzo remains appropriate for sequences/workflows over APIs; OpenAPI Overlay remains appropriate for transformations of an OpenAPI document; CloudEvents remains an event-envelope convention. Interface as Code references rather than reimplements those concerns.

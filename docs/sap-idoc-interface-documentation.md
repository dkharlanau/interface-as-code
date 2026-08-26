# SAP IDoc interface documentation that operations can use

`IDoc + message type` is not enough to operate an interface. A production-facing SAP interface description should also identify the logical producer/consumer, middleware route, delivery/replay behavior, AIF or other support route, business correlation key, responsible team and a reconciliation rule that proves the business object arrived correctly.

See `examples/sap-mdg-to-s4-customer/` for a synthetic DEBMAS-style example with those controls.

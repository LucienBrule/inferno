

# PDU Candidates

This document lists potential rack-mounted PDUs under consideration for the Inferno cluster. Each rack will receive 2× PDUs (A/B feed), each supporting 240V @ 30A continuous.

---

## Evaluation Criteria

- L6-30P input, 240V, 30A
- Vertical 0U preferred
- Outlet mix: ≥24 C13 + ≥6 C19
- Metered or switched (preferably both)
- SNMP/Web interface
- Vendor reputation
- Buyable in batch (4–8 units)

---

## Candidate List

| Vendor     | Model               | Inlet      | Outlets (C13/C19) | Metered | Switched | Notes                                 | Source Status |
|------------|---------------------|------------|-------------------|---------|----------|----------------------------------------|----------------|
| Raritan    | PX3-5867V-F6        | L6-30P     | 24 / 6            | Yes     | Yes      | Advanced SNMP, per-outlet metering     | Refurb avail   |
| APC        | AP8941              | L6-30P     | 21 / 3            | Yes     | Yes      | SNMP/Web, solid legacy model           | Refurb avail   |
| Vertiv     | VP7N30SA            | L6-30P     | 30 / 6            | Yes     | Yes      | High outlet count, modern firmware     | New preferred  |
| ServerTech | C2-48V2C413         | L6-30P     | 36 / 12           | Yes     | Yes      | High-density, very robust              | Expensive new  |
| CyberPower | PDU81105            | L6-30P     | 21 / 3            | Yes     | Yes      | Budget option, fewer outlets           | Limited supply |

---

## Next Steps

- Verify availability in quantity (min. 4 matching units)
- Confirm per-outlet telemetry where needed
- Assess firmware and SNMPv3 compatibility
- Check included mounting brackets

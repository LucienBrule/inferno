

# 🚚 Delivery & Deployment

This document outlines the logistics, installation, and acceptance process for **Project Inferno** at *Avernus* (1544 Bel Aire Dr). All artifacts and operations follow the Inferno taxonomy.

## 1. Pre-Delivery Preparation

- **Site Address**: 1544 Bel Aire Dr, second garage (*Avernus*).
- **Access Requirements**:
  - Ensure driveway clearance for delivery trucks (min 12ft width, 14ft height).
  - Garage door quick-release manifold panel retracted.
  - Staging area marked 20ft × 12ft adjacent to the door.
- **Personnel Coordination**:
  - Notify Receiving Agent 24h before delivery.
  - Confirm contractor availability for on-site lift assistance.

## 2. Shipping and Receiving

- **Shipment Tracking**:
  - Update `procurement/shipments.yaml` with carrier, tracking number, ETA.
- **Delivery Sequence**:
  - Deliver racks in Circle order (1 → 2 → 3 …).
  - Label packages with `circle-<n>` manifest tags.
- **Receiving Inspection**:
  - Verify SKU, quantity, and condition against PO.
  - Photograph packaging, note damage, and log in `delivery/inspection-<date>.md`.
  - Reject or accept items per Receiving Agent procedures.

## 3. Staging & Rack Placement

- **Unboxing**:
  - Use two-person lift for chassis and heavy components.
  - Place protective floor mats under each rack footprint.
- **Rack Positioning**:
  - Align rack rails to centerline marks on floor.
  - Maintain 36″ cold aisle clearances front and 36″ hot aisle clearances rear.
  - Confirm `circle-<n>` rack ID matches physical position.

## 4. Installation Steps

1. **Frame Assembly**  
   - Install rail kits, cable management arms, shelves.
2. **PDU & Power**  
   - Mount `inferno-pdu-circle<n>-1`, route input cable to NEMA outlet.
3. **Network Cabling**  
   - Terminate patch cables to `panel-circle-<n>`, label per port.
4. **HVAC Integration**  
   - Secure containment lid, attach duct fan to manifold flange.
5. **Component Fixtures**  
   - Slide in servers, storage units, mezzanine cards.
6. **Grounding & Bonding**  
   - Connect rack to ground bus per **power** design.

## 5. Acceptance Testing

- **Electrical**:  
  - Verify PDU power-on, monitor input voltage.
- **Network**:  
  - Ping default gateway and DNS servers on VLAN10.
- **Compute**:  
  - Power-on hosts, verify BIOS/UEFI and BMC access.
- **HVAC**:  
  - Run duct fan test at 100% for 5 minutes.
- **Environmental Sensors**:  
  - Confirm DS18B20 and DHT22 readings logged.

Log results in `delivery/acceptance-<date>.md` and collect signatures.

## 6. Handover & Documentation

- **Deliverables**:
  - Signed acceptance forms.
  - Updated inventory in `procurement/bom.yaml`.
  - Final network and power diagrams.
- **Training**:
  - Walkthrough of monitoring dashboards and emergency shutdown.
- **Contacts**:
  - List contractor, vendor, and support contacts in `delivery/contacts.md`.

## 7. Future Moves

- **Rack Removal**:
  - Reverse installation steps; keep `inspection` logs archived.
- **Door Manifold**:
  - Quick-release handles for door duct coupling.
- **Expansion**:
  - Document additional rack positions in `naming/` registry.

---

*All delivery activities must adhere to local codes, safety procedures, and the Inferno taxonomy.*
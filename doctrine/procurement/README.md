# 🛒 Procurement Architecture

This document defines the sourcing, vendor engagement, and acquisition workflow for **Project Inferno** at *Avernus* (1544 Bel Aire Dr). All procurement artifacts and naming follow the Inferno taxonomy.

## Purpose

Establish a clear, auditable process to:
- Collect and compare vendor quotes
- Track part numbers, SKUs, and pricing
- Manage purchase orders (POs) and contracts
- Coordinate delivery schedules and acceptance testing
- Ensure alignment with budget, timeline, and quality requirements

## Procurement Phases

1. **Requirements Gathering**  
   - Finalize Bill of Materials (BOM) in `procurement/bom.yaml`  
   - Define technical specifications for each category (compute, networking, HVAC, electrical)

2. **Vendor Identification**  
   - Compile potential suppliers for each category:  
     - **Compute**: Supermicro, Rave, Silicon Mechanics  
     - **Storage**: TrueNAS, QNAP, Supermicro  
     - **Networking**: Cisco, Arista, Ubiquiti, Mellanox  
     - **HVAC**: Haier, Mitsubishi, local OEM  
     - **Electrical**: Local licensed electrician, Eaton, Schneider  
     - **Accessories**: AC Infinity, Antec, Middle Atlantic

3. **Request for Quote (RFQ)**  
   - Distribute standardized RFQ template (`procurement/rfq-template.md`)  
   - Collect quotes by *YYYY-MM-DD* (TBD)  
   - Ensure quotes include SKU, lead time, price, warranty, support terms

4. **Evaluation & Selection**  
   - Populate `procurement/quotes/` with vendor responses  
   - Score quotes by: Price, Delivery, Support, Compliance  
   - Document decision rationale in `procurement/decision-log.md`

5. **Purchase Order (PO) Issuance**  
   - Generate POs using naming: `PO-inferno-<category>-<vendor>-<YYYYMMDD>`  
   - Store signed POs in `procurement/purchase-orders/`

6. **Delivery & Inspection**  
   - Track shipment via `procurement/shipments.yaml`  
   - Perform receipt inspection: verify SKU, quantity, physical condition  
   - Log acceptance in `procurement/receipts/receipt-<date>.md`

7. **Invoice & Payment**  
   - Match invoices to POs and receipts  
   - Process payments per contract terms  
   - Record transactions in `procurement/payments/`

8. **Closeout & Archival**  
   - Confirm all items delivered and functional  
   - Archive all procurement documents and sign-offs  
   - Mark procurement tickets as closed in project tracker

## Bill of Materials (BOM)

Maintain a master YAML file: `procurement/bom.yaml` with entries:

```yaml
- id: inferno-chassis-circle2
  category: compute
  description: Supermicro AS-4125GS-TNR chassis
  quantity: 1
  sku: AS-4125GS-TNR
  vendor: Supermicro
- id: inferno-cpu-9655
  category: compute
  description: AMD EPYC 9655 Processor (96C, 2.6GHz, 400W)
  quantity: 2
  sku: 1000372206
  vendor: Supermicro
# ... additional items ...
```

## Roles & Responsibilities

- **Operator (Lucien/You)**: Define requirements, approve quotes, issue POs, coordinate acceptance.
- **Procurement Lead**: Manage RFQ distribution, vendor communication, decision logging.
- **Receiving Agent**: Inspect and log deliveries, coordinate with contractors for installation.
- **Accounting**: Validate invoices, process payments.

## Timelines & Milestones

- **RFQ Issued:** `Phase 0 + 7 days`
- **Quote Evaluation Complete:** `Phase 0 + 14 days`
- **POs Issued:** `Phase 0 + 21 days`
- **Delivery Window:** `Phase 1 duration (HVAC & electrical) + compute hardware`
- **Project Go-Live:** Target *TBD* after all components are installed and tested

---

*All procurement artifacts must be named and stored according to the Inferno taxonomy. Changes to procurement procedures require Phase 0 review and sign-off.*

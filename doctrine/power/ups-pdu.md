

# UPS & PDU Infrastructure

This document captures the selected UPS hardware and ongoing planning for rack-mounted PDUs in the Inferno deployment.

---

## 🔋 UPS Selection

**Model:** APC Smart-UPS SRT 3000VA  
**Part Number:** SRT3000RMXLT-NC  
**Source:** Refurbished market (~$800)

### Specs:
- 3000 VA / 2700 W capacity
- Double-conversion (online)
- Input: L6-30P (240V)
- Output: 6 × C13 + 2 × C19 (IEC)
- Runtime: ~4–5 minutes at full load (~2.5 kW)
- Management: Network card (SNMP/Web) included
- Form Factor: 2U rackmount
- Monitoring Integration: Supported via SNMP, Prometheus, apcupsd

This unit will be deployed 1:1 per rack. If needed, runtime extension is possible via external battery packs (SRT192BP).

---

## 🔌 PDU Planning (In Progress)

Each rack will require **2× 0U vertical PDUs** (A/B feed), each on a separate 30A 240V circuit.

### Requirements:
- Input: L6-30P, 240V, 30A
- Output: 24+ C13 and 6+ C19 outlets
- Metered and/or switched
- SNMP/Web monitoring interface
- Rack-mount 0U preferred

**Goal:** Identify 4–8 identical units (new or refurbished) suitable for dual-feed deployment.

### Brands Under Consideration:
- Raritan PX3 or PX2 series
- Vertiv Geist VP7Nxx
- APC AP8941 / AP8xxx
- ServerTech C2 series
- CyberPower PDU81105

A follow-up document (`pdu-candidates.md`) will catalog potential models and sourcing notes.

---
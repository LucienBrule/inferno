# 📝 Contracting Architecture

This document defines the contractual framework, stakeholder roles, and engagement process for construction and installation phases of **Project Inferno** at *Avernus* (1544 Bel Aire Dr). All artifacts follow the Inferno taxonomy.

## 1. Purpose

Establish clear, legally sound agreements to:
- Define scopes of work for HVAC, electrical, and installation contractors
- Detail deliverables, milestones, and acceptance criteria
- Allocate responsibilities, timelines, and payment schedules
- Ensure safety, code compliance, and quality control

## 2. Contract Stakeholders

- **Owner/Operator**: Lucien (“Operator”) – project sponsor and final decision authority  
- **General Contractor**: Licensed firm responsible for coordinating trades  
- **HVAC Contractor**: Licensed HVAC technician or firm for minisplit and ducting  
- **Electrical Contractor**: Licensed electrician for subpanel, outlets, PDU feeds  
- **Network Installer**: Low-voltage contractor for switch, cabling, and conduit work  
- **Procurement Lead**: Liaison for material orders and vendor contracts  
- **Receiving Agent**: Verifies delivery and installation per contract

## 3. Contract Phases

### Phase A: Scoping & SOW
- Draft Statement of Work (SOW) per discipline (files in `contracting/sow/`)
- Include detailed task descriptions: deliverable, timeline, resource requirements  

### Phase B: Bid & Award
- Issue RFPs using template (`contracting/rfp-template.md`)
- Collect bids by *YYYY-MM-DD*
- Evaluate bids on cost, expertise, timeline, compliance  
- Award contracts, document in `contracting/awards/award-<vendor>.md`

### Phase C: Mobilization
- Kickoff meeting with all contractors
- Review safety plan, site access, and scheduling  
- Confirm insurance and permits  

### Phase D: Construction & Installation
- Execute installations according to `hvac/`, `power/`, and `network/` specs  
- Conduct daily or weekly check-ins and progress reports  
- Log deviations and change orders in `contracting/change-orders/`

### Phase E: Commissioning & Handover
- Perform system tests (electrical loads, airflow, network connectivity)  
- Document results in `contracting/commissioning/commission-<date>.md`  
- Obtain sign-off from Owner/Operator  

### Phase F: Warranty & Closeout
- Define warranty period and support terms in contracts  
- Archive all contract documents in `contracting/archive/`  
- Release final payment upon successful handover  

## 4. Deliverables & Documentation

- **SOW Documents**: Detailed scope per subproject  
- **RFP/RFQ Templates**: Standardized engagement templates  
- **Award Notices**: Contract award letters with scope and terms  
- **Change Orders**: Formal records of scope or schedule changes  
- **Commissioning Reports**: Test results and acceptance sign-offs  
- **Insurance & Permits**: Copies stored in `contracting/legal/`

## 5. Roles & Responsibilities

- **Owner/Operator**: Approve scopes, sign contracts, accept deliverables  
- **General Contractor**: Coordinate trades, ensure site readiness  
- **Subcontractors**: Execute discipline-specific scope  
- **Procurement Lead**: Facilitate contract terms for materials  
- **Inspectors**: Verify code and quality compliance  

## 6. Payment & Schedule

- **Milestone Payments**: Tied to phase completion (e.g., 20% mobilization, 50% mid-point, 30% final)  
- **Retention**: 10% held until commissioning sign-off  
- **Timeline**: Align with project Phase 1 & 2 schedules in root roadmap  

---

*All contracting documents must adhere to Inferno taxonomy and local regulations. Changes require Phase 0 review and sign-off.*

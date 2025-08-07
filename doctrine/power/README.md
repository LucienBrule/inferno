# ⚡ Power Architecture

This document outlines the electrical design and power distribution for Project Inferno at **Avernus (1544 Bel Aire Dr)**. All naming conventions follow the Inferno taxonomy.

## Site Electrical Overview

- **Service Entrance**: Standard residential 240V split-phase service.
- **Dedicated Subpanel**: A new 60A subpanel dedicated to Inferno in *Avernus*.
  - Fed from the main panel via 6 AWG copper conductors.
  - Labeled `"INFERNO SUBPANEL"` in the main breaker box.

## Rack Power Feed

- **Primary Outlet**:  
  - Location: Front wall near Circle 2 (GPU Compute rack).  
  - Outlet Type: NEMA 6-30R (240V, 30A).  
  - Circuit: Dedicated 30A breaker in the Inferno subpanel.  
  - Cable: 10 AWG stranded, conduit run concealed.

- **Secondary Outlet(s)**:  
  - Additional NEMA 6-20R outlets near Circle 1 and Circle 3 for future expansion.  
  - Each on its own 20A breaker.

## Power Distribution Units (PDU)

Each rack (“Circle”) is equipped with one or more rack-mount PDUs:

- **Naming**: `inferno-pdu-circle<N>-<index>`
- **Specification**:  
  - Input: 240V L6-30 (for GPU-heavy racks) or 120V C20 (for auxiliary racks).  
  - Outputs:  
    - (8) C13 outlets  
    - (2) C19 outlets
  - Metering: Local display + SNMP monitoring.
- **Mounting**:  
  - Rear vertical rail of each rack.  
  - Power cables bundled and labeled per the taxonomy.

## Rack-Level Power Budget

| Rack (Circle) | CPU & Node TDP | GPU TDP | Total Estimated Draw | PDU Circuit |
|--------------|----------------|---------|----------------------|-------------|
| Circle 1 (Limbo) | ≈800W         | 0W      | ≈800W                | 20A @120V   |
| Circle 2 (Lust)  | 800W          | 1300W   | ≈2100W               | 30A @240V   |
| Circle 3 (Gluttony) | 500W       | 0W      | ≈500W                | 30A @240V   |

> **Note:** Ensure each PDU input breaker has at least 20% headroom above total draw.

## Surge Protection & Safety

- **Surge Protective Device (SPD)**: Installed at subpanel main feed.
- **Grounding**:  
  - All racks and PDUs bonded to a single ground bus bar.  
  - Conform to NEC Article 250.

- **Emergency Shutoff**:  
  - A clearly labeled, lockable disconnect switch mounted next to the garage entry.

## Future Scaling

- **3-Phase Option**: Space and conduit reserved for potential 3-phase 208V feed.
- **Additional Circuits**: Subpanel has spare breaker slots for up to 6 more circuits.
- **UPS Integration**: Provision space for a 10 kVA UPS downstream of the subpanel.

---

*All cables, breakers, and devices must be labeled according to the Inferno taxonomy and local electrical codes.*
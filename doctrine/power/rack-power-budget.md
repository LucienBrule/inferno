

# Rack Power Budget

This document outlines the estimated power draw for each Inferno rack based on expected server density, networking gear, and supporting components. Each rack is provisioned with a dedicated 240V 30A circuit (7.2 kW peak, 5.76 kW continuous @ 80% load).

---

## ⚡ Avernus-West (rack-1)

- **GPU Server (8× GPU)**: ~2000W
- **Storage Node (12× SSD)**: ~400W
- **SN2410 ToR Switch**: ~150W
- **Auxiliary / Fans / Margin**: ~200W

**Estimated Continuous Draw**: ~2750W  
**Circuit Headroom**: 5.76 kW - 2.75 kW = **3.01 kW available**

---

## ⚡ Avernus-East (rack-2)

- **Dual 2U Servers**: ~2 × 300W = 600W
- **SN2410 ToR Switch**: ~150W
- **Auxiliary / Margin**: ~200W

**Estimated Continuous Draw**: ~950W  
**Circuit Headroom**: 5.76 kW - 0.95 kW = **4.81 kW available**

---

## ⚡ Avernus-North (rack-3)

- **General Compute Nodes**: ~4 × 400W = 1600W
- **SN2410 ToR Switch**: ~150W
- **Auxiliary / Margin**: ~250W

**Estimated Continuous Draw**: ~2000W  
**Circuit Headroom**: 5.76 kW - 2.00 kW = **3.76 kW available**

---

## ⚡ Avernus-Crypt (rack-4)

- **Mixed Role Nodes (GPU + Storage)**: ~2400W
- **SN2410 ToR Switch**: ~150W
- **Auxiliary / Margin**: ~250W

**Estimated Continuous Draw**: ~2800W  
**Circuit Headroom**: 5.76 kW - 2.80 kW = **2.96 kW available**

---

## ⚠️ Notes

- All estimates assume 80% safe loading threshold per circuit.
- Actual consumption may vary by workload, fan ramping, and PSU efficiency.
- PDU telemetry and smart UPS monitoring are recommended for validation.
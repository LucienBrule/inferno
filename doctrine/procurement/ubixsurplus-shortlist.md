# 🔎 UnixSurplus Hardware Shortlist

Curated shortlist of high-value nodes identified from UnixSurplus (August 2025) for potential inclusion in the Inferno
compute fabric. Focused on capability, thermal/power feasibility, rack integration, and surplus viability.

---

## ✅ Nodes by Role

---

### 🧠 General Compute: SuperMicro SYS-6029U-E1CR4T

[ebay](https://www.ebay.com/itm/134712027666)

- **Price**: $899 USD
- **CPU**: 2× Intel Xeon Gold 6148 (20 cores @ 2.4 GHz)
- **RAM**: 128 GB DDR4 ECC (expandable)
- **Storage**:
    - 12-bay SAS3 backplane (4 wired to NVMe)
- **Networking**:
    - 4× 10GBase-T onboard
- **Chassis**: 2U rackmount, Supermicro
- **Fit**: Ideal for batch compute, Kubernetes nodes, high-thread ephemeral workloads
- **Qty Available**: 5 (bulk discount potential)

---

### 🧊 Warm Storage: Supermicro 2028U-TNRT+

[ebay](https://www.ebay.com/itm/156617230186)

- **Price**: ~$1,200 USD
- **CPU**: 2× Intel Xeon E5-2699v3 (18 cores @ 2.3 GHz)
- **RAM**: 64 GB DDR4 ECC
- **Storage**:
    - 4× 800 GB U.2 NVMe SSDs (included)
    - 24× 2.5" SAS/SATA bays (with trays)
    - Triple HBA SAS3 controllers
- **Networking**:
    - 2× 10G SFP+
- **Chassis**: 2U Supermicro
- **Fit**: Warm SSD tier, ZFS pool, ceph OSD, high-throughput ingest node

---

### 🚀 Flash Compute / Ingest: Lenovo SR635

[ebay](https://www.ebay.com/itm/135580343308)

- **Price**: ~$2,700 USD
- **CPU**: AMD EPYC 7702P (64 cores @ 2.0 GHz)
- **RAM**: 256 GB DDR4 ECC
- **Storage**:
    - 14× U.2 NVMe front bays
- **Expansion**:
    - PCIe Gen 4 (4× slots)
- **Chassis**: 1U full depth
- **Fit**: NVMe inference, cache buffer, high-speed warm tier

---

### 🧪 Experimental / Cold Archive: QuantaGrid Q71L

[ebay](https://www.ebay.com/itm/144691069378)

- **Price**: $899 USD (new)
- **CPU**: 4× Xeon E7-8867 v3 (16C each = 64 cores total)
- **RAM**: 256 GB DDR4 ECC
    - Supports 96 DIMM slots
- **Expansion**:
    - 10× PCIe Gen 3 slots, OCP mezzanine
- **Storage**:
    - Chassis supports up to 78× 3.5" drives
- **Power**:
    - 4× 1600W Platinum redundant PSUs
- **Fit**: Cold tier ZFS head, memory prototyper, JBOD controller

---

### 🔥 GPU Inference Slab: Inspur NF5288M5 (“DeepSeek” Variant)

[ebay](https://www.ebay.com/itm/167512048877)

- **Price**: $5,950 USD (bulk discounts to $5,712 for 3+)
- **CPU**: 2× Intel Xeon Gold 6148 (20C @ 2.4GHz)
- **RAM**: 256 GB DDR4 ECC (expandable)
- **GPU**:
    - 8× Nvidia Tesla V100 32 GB SXM2 w/ NVLink (256 GB total VRAM)
- **Storage**:
    - 2× 1.92 TB Samsung enterprise SSDs
- **Networking**:
    - 4× 10G SFP+
    - 2× 100G Mellanox ConnectX‑5 (RoCE/RDMA capable)
- **Chassis**: 2U Inspur NF5288M5 rackmount
- **Fit**: High-throughput inference, MoE model sharding, vLLM optimized decoding
- **Notes**:
    - Same specs as “DeepSeek” branding, but cheaper and with better bulk pricing
    - Available directly from UnixPlus eBay storefront with 60-day returns
    - Recommended over older listing due to pricing, availability, and seller flexibility

---

### 🧠 Training Core: A100 8x 80GB SXM4 HGX Node

[ebay](https://www.ebay.com/itm/167597424372)

- **Price**: $79,500 USD
- **CPU**: 2× AMD EPYC 7742 (64 cores @ 2.25GHz)
- **RAM**: 512 GB DDR4 ECC
- **GPU**:
  - 8× NVIDIA A100 80GB SXM4 (640 GB total VRAM)
  - HGX A100 carrier board with full NVLink fabric
- **Storage**:
  - 2× 1.92 TB U.2 NVMe SSD
  - 6× 2.5" NVMe hot-swap bays (2 CPU direct, 4 via switch)
- **Networking**:
  - Dual onboard Ethernet ports
  - Expandable via PCIe risers
- **Motherboard**: Supermicro H12DGO-6
- **Chassis**: 4U Supermicro (AS-4124GO-NART)
- **Power**: Redundant PSU slots (fully populated)
- **Fit**: Unified VRAM training + inference slab. FlashAttention, GPT-J, DeepSpeed, vLLM all optimized. Sovereign LLM shard hub.

---

## 📝 Notes

- All pricing sourced from UnixSurplus eBay listings, August 2025.
- All units assumed to include basic 30-day warranty unless noted otherwise.
- Chassis and PSU compatibility verified against standard Inferno rack geometry.
- Power draw and cooling capacity accounted for in Inferno thermal modeling.
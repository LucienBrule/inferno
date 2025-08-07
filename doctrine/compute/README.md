# 🖥️ Compute Architecture

This document describes the compute layer design for **Project Inferno** in *Avernus* (1544 Bel Aire Dr). It covers hardware profiles, software orchestration, naming, and scheduling policies. All names follow the Inferno taxonomy.

---

## Node Classes & Rack Assignment

### Circle 2: Lust (GPU Compute)
- **Rack ID**: `circle-2-lust`
- **Hosts**:
  - `inferno-host-compute-1` (primary)
- **Hardware Profile**:
  - **Chassis**: Supermicro AS-4125GS-TNR (4U, 8× GPU)
  - **CPU**: 2× AMD EPYC 9655 (96‑core, 2.6 GHz, 400 W)
  - **Memory**: 24× 32 GB DDR5‑6400 ECC RDIMM (=768 GB, 1:4 core:GB)
  - **GPUs**: 4× NVIDIA RTX PRO 6000 Blackwell (96 GB, 300 W)
  - **Storage**:
    - 4× 3.84 TB PCIe 5.0 NVMe (scratch/model store)
    - 2× 960 GB SATA SSD (boot, mirrored)
- **Power**: ~2.3 kW draw, fed from NEMA 6‑30R → `inferno-pdu-circle2-1`
- **Use Cases**: High‑density inference, model fine‑tuning, batch training.

### Circle 6: Heresy (Experimental & Alchemy)
- **Rack ID**: `circle-6-heresy`
- **Hosts**:
  - `inferno-host-exper-1`
- **Hardware Profile**:
  - **Chassis**: Supermicro AS-4125GS-TNR (4U)
  - **CPU**: 1× AMD EPYC 9334 (32‑core, 2.7 GHz, 210 W)
  - **Memory**: 16× 32 GB DDR5‑6400 ECC RDIMM (=512 GB)
  - **GPUs**: 2× NVIDIA L40S (48 GB, 350 W)
  - **Storage**: 2× 3.84 TB NVMe scratch
- **Power**: ~1.1 kW, fed from NEMA 6‑20R → `inferno-pdu-circle6-1`
- **Use Cases**: Prototype architectures, side‑by‑side benchmarks, sandbox ML experiments.

### Circle 1: Limbo (Compute‑Light & Orchestration)
- **Rack ID**: `circle-1-limbo`
- **Hosts**:
  - `inferno-host-master`
- **Hardware Profile**:
  - **Chassis**: Supermicro EATX server (2U)
  - **CPU**: 2× AMD EPYC 9354 (32‑core, 3.25 GHz, 280 W)
  - **Memory**: 8× 32 GB DDR5‑6400 ECC (=256 GB)
  - **Storage**: 2× 960 GB SSD (OS & control plane)
- **Power**: ~600 W, fed from C20 → `inferno-pdu-circle1-1`
- **Use Cases**: OpenShift masters, DNS, registry, CI/CD runners.

---

## Node Pool & Scheduling

- **Kubernetes Node Pools**:
  - `inferno-pool-gpu` → label `inferno.circle=2`
  - `inferno-pool-exper` → label `inferno.circle=6`
  - `inferno-pool-master` → label `inferno.circle=1`
- **Taints & Tolerations**:
  - GPU nodes: `inferno/gpu=true:NoSchedule`
  - Experimental: `inferno/experiment=true:PreferNoSchedule`
- **Resource Reservations**:
  - Reserve 10% CPU & 1 GB RAM for node daemons.
  - GPU nodes expose `nvidia.com/gpu` resources.

---

## Networking & Fabric

- **Host Interfaces**:
  - `eth0`: Management network (10 GbE)
  - `eth1`: Data plane (25 GbE) → connected to `inferno-switch-aggregation-1`
  - `ib0` (optional): RoCEv2 for NVMe‑oF
- **CNI**: Calico with IP‑per‑Pod.  
- **Ingress/Egress**: Egress via DPU (BlueField-3) for offloaded NVMe‑oF or iSCSI.

---

## Software Stack

- **OS**: Rocky Linux 9.3, tuned for HPC.
- **Container Runtime**: CRI‑O
- **Kubernetes**: OpenShift 4.14
- **GPU Operator**: NVIDIA GPU Operator for driver & runtime.
- **Storage CSI**:  
  - ZFS LocalPV for NVMe scratch volumes.  
  - Rook Ceph for warm tier connectivity (optional).
- **Monitoring & Logging**:
  - Prometheus + Node Exporter  
  - ELK stack on Circle 1  
  - SNMP via PDU and BMC

---

## Daemon Services & Namespaces

- **Namespaces**:
  - `inferno-circle-2` (GPU workloads)
  - `inferno-circle-6` (experimental)
  - `inferno-circle-1` (platform services)
- **DaemonSets/Deployments**:
  - `daemon-gpu-watcher`  
  - `daemon-storage-sync`  
  - `daemon-hvac-monitor`  
  - `daemon-power-monitor`

---

*All components, node labels, and resource definitions must adhere to the Inferno taxonomy and be reviewed under Phase 1 planning.*
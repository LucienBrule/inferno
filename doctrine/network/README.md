# 🌐 Network Architecture

This document describes the physical and logical network design for **Project Inferno** in *Avernus* (1544 Bel Aire Dr). All device names and VLANs follow the Inferno taxonomy.

---

## 1. Physical Topology

```
[ Spectrum Fiber Entry ]───┐
                           │
                   [ Inferno-Core Switch ]───┬──[ inferno-switch-aggregation-1 ]
                           │                   │
                           │                   └──[ inferno-switch-aggregation-2 ]
                           │
  ┌────────────────────────┴────────────────────────┐
  │                                              │
[ inferno-switch-leaf-1 ]                      [ inferno-switch-leaf-2 ]
  │       │       │                              │       │       │
  │       │       │                              │       │       │
  └─Circle-1 Rack Patch Panel                  └─Circle-2 Rack Patch Panel
```

- **Edge Fiber**: Single-mode fiber from Spectrum demarcation to the Core switch.
- **Core Switch**: Top-of-rack 100/200/400GbE capable modular switch.
- **Aggregation**: Two 25/100GbE SFP28 uplinks from each leaf to the core, forming redundant paths.
- **Leaf Switches**: 
  - `inferno-switch-leaf-1` serves Circle 1 (Limbo) and Circle 2 (Lust).
  - `inferno-switch-leaf-2` serves Circle 3 (Gluttony) and Circle 6 (Heresy).

- **Rack Patch Panels**: 
  - Standard 24‑port LC patch panels in each rack.
  - Labeled per rack: `panel-circle-<n>`.

- **Interconnect Cables**:
  - **Fiber**: OS2 single‑mode LC‑LC, 10GbE–400GbE as needed.
  - **Copper**: Cat6A for 1/10GbE RJ45 connections (management & cameras).
  - **Conduit**: Existing conduit to network closet used for spare fiber runs.

---

## 2. Logical Topology

| VLAN ID | Name               | Purpose                               |
|---------|--------------------|---------------------------------------|
| 10      | management         | Out‑of‑band BMC, IPMI, PDU, sensors   |
| 20      | storage            | ZFS/Ceph traffic, NVMe‑oF             |
| 30      | compute            | Kubernetes data plane (25/100GbE)     |
| 40      | ingress            | North‑south ingress (public services) |
| 50      | daemon-control     | DaemonSet telemetry & orchestration   |
| 60      | hvac               | HVAC sensors & controller traffic     |

- **Subnetting**:
  - Management (VLAN10): 10.154.10.0/24
  - Storage (VLAN20): 10.154.20.0/24
  - Compute (VLAN30): 10.154.30.0/24
  - Ingress (VLAN40): Routed via Spectrum edge
  - Daemon-Control (VLAN50): 10.154.50.0/24
  - HVAC (VLAN60): 10.154.60.0/24

- **Routing**:
  - Core switch handles inter-VLAN routing.
  - Firewall rules applied at Circle 5 rack (Wrath) for north‑south traffic.

---

## 3. Device Naming

- **Core**: `inferno-switch-core-1`
- **Aggregation**: `inferno-switch-aggregation-1`, `inferno-switch-aggregation-2`
- **Leaf**: `inferno-switch-leaf-1`, `inferno-switch-leaf-2`
- **Patch Panel**: `panel-circle-<n>`
- **Transceivers**: Labeled `<device>-<port>-<speed>` (e.g., `leaf1-1-100G`)

---

## 4. DPU Integration

- **BlueField-3 DPUs** on GPU hosts:
  - `inferno-host-compute-1` with `ib0` for RoCEv2 NVMe-oF.
  - DPUs connected to leaf switches via 25/100GbE ports.
- **Offload**: iSCSI and NVMe‑oF traffic can be hardware‑offloaded by DPU to reduce CPU load.

---

## 5. Management & Monitoring

- **Out‑of‑band**:
  - Dedicated management VLAN (10) ports on each switch and PDU.
  - KVM-over-IP and BMC network on VLAN10.
- **Telemetry**:
  - SNMP on switches polled by Prometheus node exporter.
  - sFlow/NetFlow export on Core switch to `inferno-host-master`.
- **Configuration**:
  - Switch configs stored in Git under `network/`.
  - Automated provisioning via Ansible playbooks (inventory in `network/ansible/`).

---

## 6. High-Availability & Future Scaling

- **Redundancy**:
  - Dual uplinks between leaf and aggregation.
  - Dual aggregation uplinks to core.
- **Spare Ports**:
  - Each switch has at least 20% spare port capacity.
- **3‑phase Power**:
  - Core switch PDU on 240V L6‑30R circuit.

---

*All network components and VLAN assignments must adhere to the Inferno taxonomy and local codes.*

---

## 7. Switch Selection & Planning

A variety of candidate switch families were evaluated for the Inferno cluster:

- **MikroTik CRS518 / CRS504** – extremely cost-effective, RouterOS-based, lacks advanced L3
- **Ubiquiti UniFi Aggregation / Leaf** – user-friendly, UniFi-managed, but limited L3 and open NOS options
- **FS.com S5850 Series** – open NOS-capable, high density, strong value; noisier and less battle-tested
- **Cisco Nexus 93180YC / 92160YC** – enterprise-grade refurbished, but require licensing and are power hungry
- **Arista 7050SX3 / 7060CX** – excellent EOS OS and telemetry, solid refurbished market
- **Mellanox SN2010 / SN2410 / SN2700** – high-throughput, low-latency, SONiC/Cumulus/Onyx support

Detailed evaluations are maintained in:
- `network/options/mikrotik.md`
- `network/options/ubiquiti.md`
- `network/options/fs.md`
- `network/options/cisco.md`
- `network/options/arista.md`
- `network/options/mellanox.md`

### 🔧 Preferred Plan: Mellanox

Inferno will deploy:
- **1× Mellanox SN2700** as the spine/core
- **4× Mellanox SN2410** as per-rack ToR switches

Each ToR will uplink to the spine via dual 100G QSFP28, supporting 48x25G to hosts.
All switches will run **Cumulus Linux** (SONiC-compatible), with automation via Ansible and telemetry via SNMP/sFlow.

This platform was selected based on:
- Performance consistency under load
- Strong RoCEv2 + DPU support
- Affordable pricing in the refurbished market
- Flexible open NOS ecosystem

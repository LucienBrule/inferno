

# 🔥 Inferno Project Roadmap

This document tracks the buildout of the Inferno cluster at *Avernus* (1544 Bel Aire Dr).  
It is organized by phase and structured around core components: environment, infrastructure, compute, and runtime.

---

## ✅ Phase 0: Invocation & Taxonomy

- [x] Define project identity, glyphs, and sigils
- [x] Create `README.md` manifesto and structure
- [x] Establish Inferno naming schema and circle taxonomy
- [x] Scaffold `doctrine/` and `packages/` directories
- [x] Initialize UV workspace and Gradle project scaffolds

---

## 🔧 Phase 1: Symbolic Infrastructure

- [x] `racks.yaml`: Defined 4 physical racks
- [x] `circles.yaml`: Defined 10 logical circles (including Circle 0)
- [x] Graphviz render of physical topology from YAML
- [x] Circle roles assigned and rendered
- [x] Loader functions for racks/circles
- [x] CLI `inferno graph rack` command
- [x] Physical topology visualization via `graphviz`

---

## 🧱 Phase 2: Physical Architecture Design

- [x] Power layer (`power/README.md`)
- [x] HVAC airflow and containment plan (`hvac/README.md`)
- [x] Compute node planning (`compute/README.md`)
- [x] Network topology and VLAN schema (`network/README.md`)
- [x] Defined `topology.yaml` for leaf–spine fabric
- [x] Created `network.py` schema and loader for topology
- [x] Implemented `render_network_topology()` and CLI command `inferno graph network`
- [x] Generated `bringup.md` deployment guide
- [x] Procurement process and vendor logic (`procurement/README.md`)
- [x] Delivery checklist and manifest structure (`delivery/README.md`)
- [x] Contracting SOW and commissioning lifecycle (`contracting/README.md`)

---

## 🧬 Phase 3: Runtime Surface (Emergence)

- [ ] Create `nodes.yaml` with actual hardware spec
- [ ] Define `Node` schema and loader
- [ ] Add CLI: `inferno graph nodes --rack <rack-id>`
- [ ] Render per-rack node diagrams with labels and roles
- [ ] Generate circle-wise runtime service map
- [ ] Create `plane.yaml` for Daemonic Plane runtime overlays
- [ ] Map DaemonSets to logical zones
- [ ] Seed core controller daemons (HVAC monitor, GPU watcher, etc.)

---

## 🧪 Phase 4: Simulation, Planning, Deployment

- [ ] Power draw and rack load simulation
- [ ] Thermal simulation and airflow mapping
- [ ] Rack-space allocation (U height planning)
- [ ] Inventory and delivery scheduling logic
- [ ] Roadmap-driven checklist for hardware arrival & install
- [ ] Circle boot sequence logic

---

## 🛠 Phase 5: Forge Integration (Optional)

- [ ] Define Forge services for VM/hypervisor bootstrapping
- [ ] Package Inferno topology as DRPC-compatible bundle
- [ ] Enable rack-level runtime provisioning via DaemonForge

---

_This document evolves with the system. Each checkbox is a ritual, each phase a turning of the wheel._
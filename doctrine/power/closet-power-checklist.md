

# Server Closet — Power Bring‑Up Checklist (120 V now, 240 V later)

**Context**
- Closet has **three dedicated 120 V / 20 A circuits** (breakers labeled *Server Plug 1–3*).
- Wall outlets currently have **15 A duplex receptacle faces** even on 20 A circuits (installer used the wrong device). We will correct this.
- Target node: **Inspur NF5288M5 (8× V100 SXM2)** — dual 3,000 W PSUs that support **100–240 V AC**; IEC **C20** inlets (use **C19** cordsets).

---
## 0) Safety + Tools
- Non‑contact voltage tester; plug‑in outlet tester.
- Clamp meter (optional) to observe inrush/steady current.
- Label maker or painter’s tape + Sharpie.

---
## 1) Panel + Circuit Verification
- [ ] Identify breakers **#7, #8, #16** as *Server Plug 3/2/1* — all **20 A single‑pole**.
- [ ] With the breakers **OFF**, verify the associated receptacles de‑energize.
- [ ] Open one device box and confirm **wire gauge ≥ 12 AWG copper** on the 20 A circuits.
- [ ] Label each breaker with the **room + receptacle location** (e.g., “Closet – East wall – Upper duplex”).

> Note: A 15 A duplex is legal on a 20 A multi‑outlet branch, but for a single high‑draw device we will **upgrade to 5‑20R** for proper plug/cord and mechanical fit.

---
## 2) Receptacle Corrections (fast win)
For each 20 A server circuit:
- [ ] Replace the existing 15 A duplex with **NEMA 5‑20R duplex** (the one with the **T‑slot**).
- [ ] Use spec‑grade or hospital‑grade devices; torque to manufacturer spec; ensure ground bond.
- [ ] Update wall plate labeling: `120 V / 20 A – Server` + breaker number.

**Cordsets to plan:**
- **NEMA 5‑20P → IEC C19**, **12 AWG** (6–10 ft). Two cords if feeding both PSUs.

---
## 3) Bring‑Up Plan on 120 V (Now)
**Goal:** Safe POST, IPMI check, light compute until 240 V is installed.

- [ ] Use **one dedicated 5‑20R** for **PSU‑A**. Leave PSU‑B unplugged initially.
- [ ] Power‑on → verify BIOS/IPMI, fans, sensors.
- [ ] Light load test (CPU‑only or 1–2 GPUs at low power). Watch current; keep < **12–14 A** continuous per circuit.
- [ ] Optionally plug **PSU‑B** into a **second 5‑20R circuit** for redundancy and slightly higher headroom.
- [ ] No power strips. If a PDU is required, use a **5‑20P input** PDU with **C13/C19** outlets rated 20 A.

**Monitoring**
- [ ] Record idle and light‑load watts via IPMI/OS + (optional) inline meter.
- [ ] Add alert if current draw exceeds **16 A** (80% of 20 A) on any circuit.

---
## 4) 240 V Upgrade Scope (Soon)
**Why:** Better PSU efficiency and full GPU load headroom.

**Electrician work order**
- [ ] Install **L6‑30R, 240 V / 30 A** receptacle in closet; dedicated breaker; label `AI Node / Rack`.
- [ ] If practical, add **two** L6‑30R drops (future second rack) on separate breakers.
- [ ] Provide short **whip or surface conduit** with proper strain relief; label at panel and outlet.

**Cords after upgrade**
- Node uses two **IEC C19** inlets → procure **L6‑30P → C19** cords or feed via a **240 V UPS/PDU**.

---
## 5) Optional — UPS/PDU Integration
- UPS: **APC SRT3000RMXLT‑NC (3 kVA, online)** on 240 V preferred; 120 V acceptable for brief ride‑through.
- PDU: Metered/switched **C13/C19** outputs; SNMP/HTTP telemetry.
- [ ] Verify shutdown integration from UPS to hosts; add Prometheus SNMP scrape.

---
## 6) Acceptance Test (sign‑off)
- [ ] Inspur boots reliably; IPMI reachable; sensors nominal.
- [ ] Under representative load, **no breaker trips**, receptacles cool to touch.
- [ ] Labels present on panel and receptacles; documentation updated in repo.

---
## 7) Quick Map (today)
- **SP‑1 (Breaker #16)** → 120 V/20 A → *replace with 5‑20R* → preferred for PSU‑A.
- **SP‑2 (Breaker #8)**  → 120 V/20 A → *replace with 5‑20R* → PSU‑B / redundancy.
- **SP‑3 (Breaker #7)**  → 120 V/20 A → *replace with 5‑20R* → spare / tools.

---
### Notes
- The closet also has 15 A lighting circuits — keep compute loads off those.
- After 240 V is installed, move the node to the L6‑30R and free the 120 V circuits for auxiliary gear.
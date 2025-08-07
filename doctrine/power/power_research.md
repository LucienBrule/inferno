Rack Power Infrastructure for Inferno (Research Report)

Overview

This report provides recommendations for rack-level power distribution and backup for the Inferno project. We focus on enterprise-grade solutions for a 42U rack (applicable to 48U as well) including smart PDUs, online UPS systems, and a strategy for power monitoring and automation. We also summarize relevant electrical code requirements for a residential deployment in Glendale, CA.

Key goals: Ensure each rack has reliable power distribution (with redundancy), short-term backup power (3–5 minute runtime) for graceful shutdown, and integrated telemetry/alerts. All recommendations favor research/enterprise-grade hardware (non-consumer) for high reliability.

⸻

1. Rack PDU Selection

Rack-mounted Power Distribution Units (PDUs) will distribute the 240 V/30 A circuit power to individual servers and devices. We recommend intelligent (networked) PDUs with the following features:
•	Input Rating: NEMA L6-30P plug, single-phase 208–240 V, 30 A (derated to 24 A continuous per NEC) ￼. Each PDU supports ~5 kW load (80% of 7.2 kW circuit capacity).
•	Outlet Configuration: Mix of IEC C13 and C19 outlets (C19 for high-draw servers, C13 for others). Typical 0U vertical PDUs offer ~24 × C13 + 6 × C19 outlets ￼ ￼, enough for a full rack of equipment.
•	Metering & Switching: Network monitoring of voltage, current, power, and energy per PDU (±1% accuracy in enterprise units ￼). Switched outlets to remotely power-cycle individual devices and prevent overloads. Ideally, per-outlet metering for granular usage data.
•	Form Factor: Vertical 0U PDUs mount in the rack’s rear or side without using U-space, suitable for 42U/48U racks. (Horizontal 1U PDUs are an option for smaller installs, but 0U is preferred for high outlet count).
•	Redundancy: Use two PDUs per rack (A and B feed) on separate circuits for dual-corded equipment. Each PDU on a dedicated L6-30R receptacle ensures no shared circuit between racks, per code (one branch circuit per PDU).

Enterprise PDU Options: Established brands include Raritan, Vertiv Geist, APC/Schneider, Server Technology, and Eaton. The table below compares a few representative models (new vs. refurbished where applicable):

PDU Model	Capacity	Outlets (C13/C19)	Features	Est. Cost (USD)
Raritan PX3-5870V (0U)	208–240 V, 30 A	24 × C13 + 6 × C19	Metered & switched; ±1% billing-grade accuracy ￼; SNMP, HTTP/SSH ￼	~$2,400 new ￼ (>$2k); ~$500–800 used (older models)
Vertiv Geist VP7N30 (0U)	208 V, 30 A	30 × C13 + 6 × C19	Switched per outlet; input & outlet power monitoring; locking IEC plugs ￼	~$1,200–1,500 new (Next Gen IMD); rare on used market
APC AP8941 (0U)	208 V, 30 A	21 × C13 + 3 × C19	Switched Rack PDU; SNMP/web mgmt (APC 8000-series); legacy but robust	~$1,000 new; ~$300–600 refurbished
CyberPower PDU81105 (0U)	200–240 V, 30 A	21 × C13 + 3 × C19	Metered-by-outlet + switched; basic web UI & SNMP; 3-year warranty ￼	~$1,200 new (discontinued model was $1,450 ￼); ~$500 used

Notes: All listed models use an L6-30P input cord (single-phase). They provide remote monitoring and control via SNMP/web interfaces. High-end units (Raritan, Geist, ServerTech) often have advanced features like outlet-level current limiting and environmental sensor ports, but can be costly new. Refurbished units (e.g. older Raritan PX or APC models) are a budget-friendly option, but ensure firmware supports modern protocols (SNMPv3, etc.) and that any used unit is tested/calibrated.

Mounting & Size: For a standard 42U rack (~78″ tall), a 0U PDU with 30+ outlets will span the rack length. Many models (~70″ tall) fit 42U perfectly; in a 48U rack they mount with a small gap or use an extended model if available. Always secure the PDU per manufacturer brackets and ensure the cord can reach the top/bottom L6-30 receptacle.

Reliability: These PDUs support hot-swap replacement in designs where a maintenance bypass or dual-cord devices are used (you can safely replace one PDU while the other carries load, if each device is dual-fed). They also typically have built-in overcurrent protection (such as a circuit breaker or fuse per PDU or per bank) to avoid cascading trips. High-quality units have durable components and can handle continuous high load (24 A) safely.

Refurb vs. New: Enterprise PDUs are built for long service life. A new unit comes with support/warranty and latest features (e.g. higher outlet count, updated web UI). Refurbished older models (Raritan PX2, APC AP7xxx series, etc.) can cost a fraction of new, but may lack per-outlet metering or modern security features. For a research lab on a budget, used units from reputable resellers (with new outlet retention clips or recent calibration) can be suitable, but avoid very old units that only support outdated protocols or have failing displays.

⸻

2. Rack-Mount UPS Systems

To provide short-term power backup and graceful shutdown ability, each rack should have a double-conversion (online) UPS sized around 3000–5000 VA. Online UPS systems continuously produce clean sine-wave output and quickly react to outages (zero transfer time). Key considerations for Inferno’s ~2–3 kW per rack loads:
•	Capacity: ~3000 VA (approx. 2700–3000 W) per UPS covers the current load (~2.8 kW max in rack-1【0†⚡ Avernus-West】) with some headroom. If future expansion could push continuous loads beyond ~3 kW, consider 5000–6000 VA units or using two UPS units (each on separate circuits to split load).
•	Output: 208/240 V output to match the PDU input. Most 3kVA UPS models have IEC C13/C19 outlets or a mix of IEC and NEMA. Ensure at least a couple C19 outlets for high-draw servers (some UPSes provide 2× C19 + 6–8× C13 on the rear panel).
•	Input Plug: Typically NEMA L6-30P input for 208–240 V models (some UPS are hardwire capable or have L6-20P if lower capacity). Make sure the UPS input plug matches your rack circuit receptacle (L6-30R) or use a compatible pigtail.
•	Form Factor: Rack-mount 2U or 3U units for 3kVA. Verify depth fits your rack (some are ~27″ deep). Include the rail kit for mounting.
•	Runtime: With ~2.5–3 kW load on a 3kVA UPS, expect 3–6 minutes of battery runtime (just enough to safely shut down systems) ￼ ￼. For example, a 3kVA online UPS (2500 W load) gives ~6 min runtime on internal batteries ￼, and ~15 min at half load ￼. This meets the “3–5 minutes is fine” requirement. If longer runtime is needed, most models support external battery packs to extend runtime (optional).
•	Management & Alerts: All recommended UPS models support SNMP/HTTP management via a network management card (often optional on 3kVA units). This allows remote monitoring of battery status, input/output power, and integration with auto-shutdown software.
•	Bypass: Online UPSes have an internal automatic bypass. Some also allow adding a maintenance bypass PDU for servicing without downtime, though for small setups this may not be critical.

UPS Model Comparison: (All are online double-conversion, rack-mount units.)

UPS Model	VA / Watt	Outlet Configuration	Runtime (full/half load)	Network Management	Approx. Cost
APC Smart-UPS SRT 3000	3000 VA / 2700 W ￼	2U unit; 208V output; Outlets: 6 × C13, 2 × C19 (IEC) (some models have 1× L6-30R instead)	~4–5 min @ 2700 W ￼; ~11 min @ 50% load ￼	AP9630/9631 NIC slot (optional card for SNMP/Web)	~$3,000 new (w/ card); $600–1200 used (plus new batteries)
Eaton 9PX 3000	3000 VA / 3000 W (unity PF)	2U; 208V output; Outlets: 6 × C13, 2 × C19 (or 1 × L6-30R + 4 × 5-20R on some)	~5–7 min @ 3000 W; ~14 min @ 1500 W ￼ (internal batt)	Network-MS card optional (Web/SNMP); Eaton Intelligent Power Manager software	~$3,000–3,500 new; ~$800–1500 used (battery age varies)
Vertiv Liebert GXT5-3000	3000 VA / 3000 W (PF=1)	2U; 208V in/out (configurable 208/120); Outlets: 6 × C13, 2 × C19 (IEC)	~3 min @ 3000 W; ~9–10 min @ 1500 W (internal battery) ￼. Longer if Li-Ion model (PSI5 series).	NIC RDU101 optional (SNMP/Web); 3-year full warranty ￼	~$3,500–4,000 new (with card); used not common (newer model)
CyberPower OL3000 (HV)	3000 VA / 2700 W	2U; 208/240V output; Outlets: 3 × NEMA (e.g. 2× L6-20R, 1× L6-30R) or some models with 8× IEC (model-dependent) ￼	~5–6 min @ 2700 W (estimate); ~12–15 min @ 1350 W (internal)	Included RMCARD (on some -HVN SKU) for web/SNMP; or optional card	~$1,100–1,500 new (cost-effective); limited used market

Notes on UPS models:
•	APC SRT 3000: A popular online UPS with 2.7 kW capacity. If buying new, consider the XLA or XLT variants for correct voltage (XLA usually 120 V, XLT 208 V). It provides sine wave output and pure online conditioning. The network management card (if installed) allows integration with APC’s PowerChute or apcupsd for automated shutdown. It has hot-swappable battery modules. Used units: Many are available ex-data-center, but plan to replace the batteries (APC RBC packs) for reliability.
•	Eaton 9PX 3000: High-efficiency (up to 95% online) UPS with unity power factor (can support full 3000 W). Known for excellent build and the Eaton Intelligent Power software support. The LCD interface is very informative. Unity PF means extra power capacity if needed. It’s often pricier and highly regarded in enterprise environments (with a correspondingly higher new price).
•	Vertiv Liebert GXT5: The GXT series is a workhorse for server rooms. The GXT5-3000MVRT model (for 208 V) has internal batteries giving around 3–5 minutes at full load. Vertiv also offers a lithium-ion based PSI5-3000 that can have longer life and runtime. The GXT5 supports external battery cabinets for expansion ￼. Network management is via an optional card. Liebert units are known for reliability and fast transient response.
•	CyberPower OL3000: A budget-friendly online UPS. Some models (OL3000RTXL2UHVN) come with an SNMP card pre-installed ￼, making them ready for network monitoring out-of-box. CyberPower’s outlets on high-voltage models can be limited (often a few large receptacles) – you might need to plug a small rack PDU into it to get multiple C13 outlets for all devices. It’s a good value new; just verify the exact outlet config meets your needs (e.g. the HV model might have only 3 outlets, which could then feed your primary PDU).
•	Form Factor & Weight: These UPS units are heavy (3kVA with batteries ~ 25–45 kg). Ensure your rack has mounting rails and consider placing the UPS in the lower part of the rack for stability. Provide adequate ventilation space as they output heat (online mode losses).
•	Noise: Fans in online UPSes run continuously; plan for audible noise (comparable to a server).
•	Maintenance: Batteries in VRLA (lead-acid) UPS need replacement every ~3-5 years. All models allow hot-swap battery replacement (via front panel modules or trays) without dropping the load (the load will go to bypass or rely on the other feed if redundant).

UPS Redundancy & Deployment: Ideally, each rack could have two smaller UPSes for A/B feed (each UPS on a different circuit backing one PDU), which allows zero downtime maintenance. However, this doubles cost. A simpler approach is one UPS per rack on one circuit/PDU, with the other PDU being a direct feed (no UPS) – this gives partial backup and is simpler: during an outage, equipment on the UPS-backed PDU stays on briefly, equipment on the other PDU loses power immediately. This is not true 100% power redundancy, but could be acceptable if the goal is just to safely shut down the major loads. Alternatively, use one UPS and connect both server PSUs to it (i.e. both A and B cords of each server go into the UPS via a suitable PDU or adapter). This sacrifices feed redundancy but ensures everything is on battery backup. The strategy should be chosen based on whether runtime or feed redundancy is more important.

For Inferno’s use-case, since “clean shutdown” is the priority, you might choose a single UPS per rack and plug the critical components into it (possibly through a small sub-PDU). That UPS-backed sub-PDU would carry most of the load during outages, and non-critical devices could stay on the non-UPS PDU (and drop immediately on outage). This way battery capacity is focused on critical gear. In any case, ensure not to exceed 80% load on the UPS continuously (allow battery recharge and avoid overload).

⸻

3. Electrical Code & Installation (Glendale, CA)

Deploying this equipment in a residential setting requires compliance with the California Electrical Code (based on NEC 2020) and any Glendale-specific amendments. Key points for a safe, code-compliant installation:
•	Dedicated Branch Circuits: Each rack’s power should come from its own dedicated 30 A branch circuit (no daisy-chaining or sharing circuits between racks). A “branch circuit, individual” means it supplies only one outlet/device ￼. For four racks, plan for four dedicated 240 V circuits (or more if dual feed per rack). Extension cords must not be used as permanent wiring ￼ – hardwire the circuits to proper receptacles behind each rack. (Temporary use of a PDU’s cord is fine, but no cheap power strips or run of flexible cord in lieu of fixed wiring, per NEC 400.8 ￼.)
•	Receptacles: Use NEMA L6-30R locking outlets for these 30 A circuits (matching the PDU/UPS plugs). Per code, the receptacle rating must meet or exceed the circuit rating (30 A receptacle on 30 A circuit) ￼. Typically, a single outlet is on each 30 A circuit (a multi-outlet on 30A would require each receptacle also be 30 A rated, which is uncommon except for some duplex 30A designs – simpler to use one outlet per circuit).
•	Breaker & Continuous Load: The circuit breaker (overcurrent device) must be sized for 125% of the continuous load ￼. In practice, that means do not exceed 24 A draw on a 30 A breaker (24 A is 80%). Our rack budgets (~12 A per rack at ~2750 W) are within this limit, leaving headroom【0†⚡ Avernus-West】 ￼. Use standard 2-pole 30 A breakers (with common trip) for 240 V feeds. (If using a subpanel, ensure it’s rated for the load and properly fed from main).
•	Conductor Size: Use #10 AWG copper wire (or larger) for 30 A branch circuits ￼. Typically 10/2 with ground (for 240 V no neutral is needed; just two hot legs and ground). If runs are long, consider voltage drop, but for typical residential distances #10 is fine.
•	Outlet Location & Enclosure: Install the L6-30R receptacle in a suitable outlet box or enclosed receptacle panel, securely mounted on wall or in a structured wiring panel near the rack. It should be accessible (you mentioned behind rack – ensure there is a way to reach it without moving heavy equipment, or mount it just outside the rear of the rack). Use proper strain relief and if metal boxes, they must be grounded. The receptacle should be labeled (e.g. “Rack 1 – Circuit 5, Panel A”) for clarity.
•	GFCI Protection: As this is a residence, under NEC 2020 many 240 V outlets now require GFCI if in certain locations. Specifically, 125 V to 250 V receptacles on single-phase <=150 V to ground (which includes 240 V circuits) must have GFCI protection in dwelling unit locations listed in 210.8(A) ￼. Those locations include garages, basements, laundry areas, outdoors, etc. ￼. For example, if your racks are in a garage or basement, GFCI is definitely required by current code. This can be achieved by using a 2-pole 30A GFCI breaker in the panel or a GFCI receptacle (if one exists for 30A, more commonly you’d use the breaker type). If the rack room is a regular room inside the house (bedroom/office), it’s not explicitly listed in 210.8(A) so GFCI may not be mandated unless it falls within a specific area (like near a sink or in an “indoor damp location”). However, Glendale’s code likely mirrors NEC—err on the side of GFCI for safety if there’s any doubt (and an inspector may require it).
•	AFCI Protection: Arc-Fault Circuit Interrupter protection is generally required for most branch circuits in dwellings (NEC 210.12) except certain areas like garages or kitchens where other exceptions apply. If the rack circuits originate in a part of the dwelling that requires AFCI (e.g. a bedroom circuit feeding an adjacent closet with rack), you might need a combination AFCI breaker or an outlet AFCI. California’s code (2019 Title 24) required AFCI in all habitable areas. A garage is typically not considered habitable, so AFCI might not be required there (just GFCI). Check with the local AHJ: in many cases using a dual-function 30A breaker (AFCI+GFCI) can cover both if needed. Keep in mind that some UPS units or PDU power supplies can trip AFCIs due to their electrical noise; if nuisance tripping occurs, a standard breaker might be allowed if that circuit is exempt from AFCI (or use an AFCI with higher immunity).
•	Panel and Wiring Methods: Use proper conduit or cable for running the circuits (NM-B 10/2 cable if allowed and protected within walls; or EMT conduit with THHN wires for a cleaner install, especially if surface-running in a garage). All wiring must follow NEC/CEC for support, bend radius, and protection. Ensure a solid equipment ground is provided (via the grounding conductor).
•	Breaker Labeling: Clearly label the new breakers in the main panel (e.g. “Server Rack 1 - west wall”), and label the receptacles with the circuit ID. Glendale code likely requires an electrician to pull permits for new circuits; they will ensure labeling and panel schedules are updated.
•	Physical Placement: Maintain required clearances around electrical equipment. NEC requires 36″ depth of clear working space in front of panelboards – don’t block electrical panels with the rack. The rack itself should have some clearance from walls for cooling and access. Keep cabling tidy and use flame-rated cable ties or management. Any wall penetrations for cables (if running networking or power) should be fire-stopped as required.
•	Thermal & Fire Safety: Racks and UPS equipment can produce heat – ensure the room has adequate ventilation or cooling. Don’t overload the house’s HVAC or cause hot spots that could trip breakers. All equipment should be UL listed for the intended use. Having a smoke detector in the room is wise since it’s high-power equipment (and possibly a small extinguisher in an emergency, though sprinklers or suppression aren’t typically required in a home office, it’s worth considering because of the equipment density).
•	Surge Protection: Not a code requirement but a recommendation – consider whole-house surge protection at the main panel, or point-of-use surge protectors, to protect sensitive server equipment from voltage spikes on the grid.

Finally, always consult with a licensed electrician and pull the necessary permits for these installations. Glendale’s inspectors will reference the California Electrical Code which in 2025 should be based on NEC 2020 or 2023. Engaging the inspector early about things like GFCI/AFCI requirements for your specific room (especially if it’s a grey area like a closet turned server room) can save headaches. Following code not only ensures safety but also protects insurance coverage.

Summary Checklist (Electrical):
•	✅ Dedicated 30A/240V circuit per rack (min #10 AWG copper, <80% load) ￼ ￼
•	✅ NEMA L6-30R receptacle in proper box, one per circuit (30A rated)
•	✅ Two-pole 30A breaker (common trip) – GFCI/AFCI type as required by code ￼
•	✅ Label panel breaker and receptacle (rack name/number, circuit ID)
•	✅ No extension cords – use permanent wiring to rack vicinity ￼
•	✅ Grounding – verify ground connections for each circuit and rack (use bonding jumpers if needed for rack frame)
•	✅ Clearances – maintain access to disconnects and panel; don’t block egress or cooling vents
•	✅ Permits & Inspection – schedule inspection after install; fix any deficiencies noted by the AHJ.

⸻

4. Power Monitoring & Telemetry

Implementing a robust power monitoring and automation system will help you track energy usage, get alerts for anomalies, and automate safe shutdowns during outages. The strategy includes:

a. PDU & UPS Telemetry: Leverage the networked capabilities of the smart PDUs and UPS units:
•	SNMP Monitoring: Most enterprise PDUs and UPSes support SNMP (v2c/v3). You can poll metrics like load (amps), watts, voltage, frequency, battery status, etc. For example, Raritan PDUs provide current, voltage, kW, kWh with billing-grade accuracy ￼. Use an SNMP collector to gather these regularly (e.g., every minute).
•	Prometheus + SNMP Exporter: A modern approach is to use Prometheus (time-series database) with the snmp_exporter module ￼. This translates SNMP data into Prometheus metrics. Prebuilt Grafana dashboards exist for APC UPSs ￼, Eaton UPSs ￼, etc. and can be adapted to other brands. You can chart load trends, remaining battery, PDU per-outlet current, etc., over time.
•	Vendor APIs: Some devices have REST/HTTP APIs (e.g., Raritan JSON-RPC ￼). These can be used if SNMP is insufficient. However, SNMP is the most universal solution.
•	Software Tools: Alternatively, vendor-specific software can poll devices: APC’s PowerChute Network Shutdown, Eaton’s Intelligent Power Manager, Vertiv’s Power Insight, etc. These can integrate with hypervisors or OS to initiate shutdowns. They’re usually free for basic use, but can be complex. If you prefer open-source, Network UPS Tools (NUT) is excellent: it can unify many brands of UPS/PDU under one monitoring service ￼ ￼. NUT’s snmp-ups driver supports APC, Eaton, CyberPower, Liebert, and even PDU MIBs (Raritan, Geist) ￼ ￼.
•	Metrics to Track: At minimum, monitor per-rack load (to ensure you stay under 24 A and to see trends), UPS battery charge and runtime, input voltage (to catch any sags/swells), and outlet status. Set thresholds for alerts (e.g. if a rack draws >20 A sustained or if UPS battery < X minutes).

b. Alerts & Integration:
•	Alerting: Use a system like Prometheus Alertmanager or Grafana alerts to notify if, say, a UPS goes on battery or if remaining time falls below a threshold. The UPS can also usually send SNMP traps or emails on events (e.g., mains power loss).
•	Logging: Keep event logs from UPS (most record when power fails, returns, battery self-tests, etc.). This helps with post-mortem analysis of any power incidents.
•	Redfish/IPMI (Future): As noted, integration with Redfish (standard RESTful API for server management) could provide power metrics per server from its PSU/BMC. This is separate from the facility power but gives insight into which server is using how much power. Some newer servers’ Redfish can report real-time consumption ￼. You might plan to pull that into the same monitoring stack to correlate rack PDU readings with individual server readings.

c. Automated Shutdown Plan:

When running on UPS battery during an outage, you have limited time. Automation ensures everything shuts down cleanly before batteries exhaust:
•	UPS Signaling: The UPS NMC or software should signal when battery is low (or on a timer after x minutes on battery). For example, with apcupsd (for APC UPS), you can configure it to trigger at, say, 5 minutes remaining.
•	Shutdown Sequence: Gracefully shut down the most important systems last. e.g., initiate shutdown of less critical nodes first to reduce load (extending UPS runtime for critical nodes). In the Inferno racks, perhaps storage nodes and GPU servers (with long shutdown times) go first, while network gear and critical controller nodes go last.
•	Scripting: Using tools like apcupsd or NUT, you can run scripts when on-battery or low-battery. A common method: have one machine act as the “UPS server” that monitors status, and other machines run a client that listens for a shutdown signal. Alternatively, as the user suggested, a script can use SSH or API calls to instruct each server to shut down. For instance, one user set up apcupsd to run a custom script that SSHes into multiple servers to trigger shutdown -h now when 10 minutes of runtime remain ￼ ￼.
•	Hypervisors/VMs: If running virtualization, ensure the shutdown automation accounts for VMs (either shutting them down via hypervisor tools or letting the host handle it).
•	Startup: After power is restored, some UPSes can cycle outlets to power servers back on. Many servers support AC power auto-on (return to last state). You may need to manually power on some gear or use wake-on-LAN. Document the power restore procedure and consider staggering the startup to avoid all servers drawing inrush current simultaneously.

d. Metrics Hosting (Self-Host): Since you prefer self-hosting metrics, you can run a small VM or container for Prometheus + Grafana on the management network. Collect SNMP data from PDUs/UPS there. Grafana will allow dashboards accessible to your team. Self-hosting ensures data privacy and customization (just remember to also put the monitoring server on a UPS so it doesn’t go down before it can alert you!).

e. Example Telemetry Stack:
•	Prometheus SNMP Exporter: Polls PDU and UPS SNMP OIDs (e.g., using standard UPS-MIB for battery status ￼, and vendor MIB for PDU outlet loads).
•	Node Exporter / Redfish: If using Redfish for servers, use a Redfish exporter or script to poll per-server power draw and temps.
•	Grafana: Visualize trends (power usage per rack over time, number of power events, battery autonomy).
•	Alertmanager: Sends email/SMS/Slack alert if (for example) “UPS on battery > 1 min”, “UPS remaining < 2 min”, or “Rack circuit load > 90%” etc.
•	Syslog/SNMP Traps: Optionally, configure UPS to send SNMP traps to a listener or emails to an admin on events as redundancy.

f. Future Integration: Down the line, you can explore deeper integration like automatic load shedding – e.g., script the PDU to turn off some non-essential outlets when on battery to extend runtime. Some PDUs allow outlet control via SNMP set commands or API. Coupled with a monitoring system, you could automate: “If UPS on battery and load > X, turn off outlets for test servers or high-draw GPUs after 1 minute.” This adds complexity but is possible with switched PDUs.

⸻

Conclusion & Recommendations

Power Distribution: Use enterprise-grade smart PDUs (0U vertical) in each rack, fed by dedicated 30A circuits. Our top picks are Raritan or Vertiv Geist for feature set, but APC and ServerTech units are also solid. Ensure each PDU’s load stays under ~24 A (80% of breaker) ￼ – our power budget shows plenty of headroom per rack. Redundant PDUs (A/B feeds) are advised if you plan dual-corded equipment; if not, a single PDU per rack is acceptable but any downtime on that circuit affects the whole rack.

UPS Backup: Deploy one online UPS (3kVA class) per rack to handle ~2–3 kW load for a few minutes. The UPS will smooth power and give time for an orderly shutdown. We recommend models like APC SRT 3000 or Eaton 9PX 3000 for high quality, or CyberPower OL3000 for a budget-conscious choice, all of which will support ~5 minutes at full load ￼. Perform periodic battery self-tests and plan battery replacements to maintain runtime. If budget allows, consider two smaller UPS units for each rack (for A/B feeds), otherwise concentrate critical loads on the single UPS-backed feed.

Code Compliance: Adhere to NEC/CEC rules in installation: professional wiring, correct breaker sizing, and required GFCI/AFCI protection in the residential environment ￼. Glendale’s inspectors will expect work to be to code – dedicate circuits, use proper receptacles, and label everything clearly. This not only passes inspection but ensures safety (the power system you build will handle the load without overheating wires or tripping breakers spuriously).

Monitoring & Automation: Implement an integrated monitoring stack. Use the network capabilities of your PDUs and UPS to collect real-time power data. Tools like Prometheus with SNMP or vendor software will give insight into usage and enable alerting on anomalies. Tie the UPS status to an automated shutdown sequence (via apcupsd, NUT, or scripts) so that even if an outage occurs when no one is around, the Inferno cluster powers down gracefully before UPS batteries deplete. Testing this process periodically (e.g., a simulated power outage drill) is wise – to confirm all pieces (monitoring, alerts, shutdown scripts) work as expected.

By following these recommendations, Inferno’s power infrastructure will be robust, safe, and manageable. You’ll have the data to optimize power usage and the peace of mind that even in an emergency, your hardware (and data) are protected from power loss.

jsii on codex will likely be helpful in retrieving relevant citations.
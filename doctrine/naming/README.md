


## Covenant & Ethos

*Inferno is a project guided by a spirit of curiosity, respect, and technical rigor.*

*We value openness and learning above all else.*

## Taxonomy

A structured naming scheme for all elements in Project Inferno:

- **Site**  
  - `Site Name`: Avernus  
  - Represents the physical location: the second garage at 1544 Bel Aire Dr.

- **Architecture**  
  - `Architecture Name`: Crucible  
  - The overall system design and deployment pattern.

- **Subprojects**  
  - Use lowercase folder names matching these keys:  
    - `hvac/`  
    - `power/`  
    - `network/`  
    - `compute/`  
    - `procurement/`  
    - `contracting/`  
    - `delivery/`  
    - `naming/`  

- **Racks (Circles)**  
  - Format: `circle-<number>-<role>`  
  - `<number>`: 1–9 mapped to Dantean Circles  
  - `<role>`: short descriptor, e.g., `limbo`, `lust`, `gluttony`, etc.

- **Nodes (Units within Racks)**  
  - Format: `inferno-<circle>-node<index>`  
  - `<circle>`: same as rack number  
  - `<index>`: sequential per rack, starting at 1

- **Server Hosts**  
  - Format: `inferno-host-<role>`  
  - `<role>`: primary service, e.g., `compute`, `storage`, `master`

- **Network Devices**  
  - Format: `inferno-switch-<tier>-<index>`  
  - `<tier>`: `core`, `aggregation`, `leaf`  
  - `<index>`: sequential per tier

- **Power & PDU**  
  - Format: `inferno-pdu-<rack>-<index>`  
  - `<rack>`: `circle1`, `circle2`, etc.  
  - `<index>`: sequential per rack

- **Daemon Services**  
  - Kubernetes namespaces and service names mirror rack names:  
    - Namespace: `inferno-circle-<number>`  
    - DaemonSet/Deployment: `daemon-<service>`

- **Legend**  
  - Use consistent lowercase hyphen-delimited names.  
  - Reflect both functional role and mythic context.
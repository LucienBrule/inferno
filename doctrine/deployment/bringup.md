## Phase 0: Physical Layout

- **Position racks**  
  Arrange racks in the designated data center space according to the floor plan, ensuring adequate spacing for airflow and maintenance access.

- **Verify environmental requirements**  
  Confirm that temperature, humidity, and airflow meet specifications to prevent hardware damage and ensure optimal performance.

## Phase 1: Power Wiring

- **Mount PDUs**  
  Secure Power Distribution Units (PDUs) inside each rack in their designated positions.

- **Connect circuits**  
  Wire PDUs to the appropriate power circuits, following electrical codes and data center standards.

- **Sequential power-up order**  
  Plan and execute power-up in a sequence that minimizes inrush current and prevents power disruptions.

## Phase 2: Network Wiring

- **Intra-rack ToR→node patching**  
  Connect Top-of-Rack (ToR) switches to individual servers/nodes within the same rack using appropriate cables.

- **ToR→spine uplinks**  
  Establish uplink connections from ToR switches to spine switches to form the network fabric.

- **Optional patch panel wiring**  
  If applicable, connect patch panels between servers and switches to facilitate cable management and flexibility.

## Phase 3: Bring-up & Validation

- **Link light checks**  
  Verify link lights on all network interfaces to ensure physical connectivity.

- **LLDP/neighbors**  
  Use Link Layer Discovery Protocol (LLDP) to confirm neighbor relationships between devices.

- **VLAN/trunk/routing checks**  
  Validate VLAN configurations, trunk ports, and routing protocols for correct network segmentation and traffic flow.

- **Throughput tests**  
  Perform network throughput tests to confirm performance meets design expectations.

## Phase 4: Operational Best Practices

- **Optional Out-of-Band (OOB) management**  
  Set up OOB management interfaces for remote access and troubleshooting.

- **Redundancy**  
  Implement redundant power and network paths to improve reliability.

- **Labeling**  
  Clearly label all cables, ports, and devices to facilitate maintenance and future upgrades.

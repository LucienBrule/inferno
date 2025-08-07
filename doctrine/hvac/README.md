# 🌀 HVAC Architecture

This document outlines the environmental control and airflow design for **Project Inferno** at *Avernus* (1544 Bel Aire Dr). All naming follows the Inferno taxonomy.

## Ambient Cooling (Cold Zone)

- **Minisplit Unit**  
  - Type: Ceiling cassette, multi-zone capable  
  - Model example: HAIER FlexFit Pro or equivalent  
  - Capacity: ≥12,000 BTU/h with low-ambient kit  
  - Placement: Centered above the cold aisle between Circle 2 and Circle 6  
  - Drain: External condensate pump routed to exterior  
  - Controls: WiFi-enabled thermostat, setpoint 60°F–65°F

- **Supply & Return**  
  - Supply: Diffused through 4-way ceiling cassette vanes  
  - Return: Passive return via perforated grille above Circle 4  
  - Filtration: MERV 8 washable prefilter

## Hot Aisle Containment

- **Rack Arrangement**  
  - Racks placed back-to-back: `circle-2-lust` and `circle-3-gluttony`  
  - Hot aisle width: 36″ between rear doors

- **Containment Lid**  
  - Material: 2″ rigid foam (Owens Corning Foamular) or polycarbonate panel  
  - Sealing: Weatherstrip gasket around lid perimeter  
  - Access: Hinge/magnetic latch on front of hot aisle lid for service access

- **Duct Fan**  
  - Model: AC Infinity CLOUDLINE T6 (6″ inline duct fan)  
  - Mount: Top-center of lid, exhaust port upward  
  - Control: Thermostat or relay via PDU outlet, runtime triggered at 85°F inlet

## Exhaust Ducting

- **Duct Path**  
  - Flex duct: 6″ UV-rated insulated flex from duct fan to garage door manifold  
  - Manifold: Quick-disconnect flange mounted in door panel at Circle 3  
  - Exterior hood: Louvered aluminum grille with backdraft damper

- **Quick-Release Coupling**  
  - Flange type: Camlock or bayonet for fast connect/disconnect  
  - Storage: Hooked inside door recess for stowing when rolling door is raised

## Airflow Diagram

```
Cold Zone (Garage Ambient)
     ↓
Front of Racks → (cold air intake)
     ↑
Back of Racks (hot air exhaust)
     → Hot Aisle Containment → Duct Fan → Flex Duct → Door Manifold → Outdoors
```

## Thermal Management

- **Temperature Targets**  
  - Cold Zone: 60°F–65°F  
  - Hot Aisle: < 140°F at fan inlet  
  - Inlet Delta-T: ≤ 20°F under full GPU load

- **Monitoring**  
  - Sensors: DS18B20 (temperature) + DHT22 (humidity) at front/rear of racks  
  - Integration: MQTT to Home Assistant, alerts at 75°F inlet or humidity > 60%

## Future Scaling

- **Supplemental Ventilation**  
  - Optional wall-mounted exhaust fans for Circle 5 (Wrath) security rack  
  - Bypass duct for door open scenarios

- **Environmental Controls**  
  - Integration with Nebbiolo controller or similar for automated damper control  
  - Provision for adding secondary minisplit head if ambient > 75°F

---

*All components must comply with manufacturer guidelines and local codes. Indoor unit installation by licensed HVAC contractor. Electrical and condensate lines routed per best practices.*

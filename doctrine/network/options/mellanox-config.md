

# Mellanox Configuration Examples

This document provides reference configurations for deploying your Mellanox SN2700 spine and SN2410 leaf switches on **Cumulus Linux** (SONiC-compatible). Use these examples as a starting point and adapt interface names, IPs, and AS numbers to your environment.

---

## 1. Spine Switch (SN2700)

### 1.1. Network Interfaces

Create `/etc/network/interfaces.d/50-spine.cfg`:

```bash
# SPINE SN2700 interface definitions

auto lo
iface lo inet loopback

# Peer links to leafs (ToR switches)
auto swp1
iface swp1
    description ToR-West Uplink
    mtu 9216
    address 192.168.100.1/31

auto swp2
iface swp2
    description ToR-East Uplink
    mtu 9216
    address 192.168.100.3/31

auto swp3
iface swp3
    description ToR-North Uplink
    mtu 9216
    address 192.168.100.5/31

auto swp4
iface swp4
    description ToR-Crypt Uplink
    mtu 9216
    address 192.168.100.7/31
```

### 1.2. FRR (BGP EVPN) Configuration

Edit `/etc/frr/frr.conf`:

```bash
frr version 9.0
!
hostname spine-1
log syslog informational
!
no ipv4 forwarding
no ipv6 forwarding
!
router bgp 65000
  bgp router-id 10.0.100.1
  no bgp default ipv4-unicast
  neighbor LEAFS peer-group
  neighbor LEAFS remote-as 65000
  neighbor LEAFS capability extended-nexthop
!
address-family l2vpn evpn
  neighbor LEAFS activate
  advertise-l2vpn evpn
exit-address-family
!
interface swp1
  description ToR-West Uplink
  mtu 9216
!
interface swp2
  description ToR-East Uplink
  mtu 9216
!
interface swp3
  description ToR-North Uplink
  mtu 9216
!
interface swp4
  description ToR-Crypt Uplink
  mtu 9216
!
line vty
```

---

## 2. Leaf Switch (SN2410)

### 2.1. Network Interfaces

Create `/etc/network/interfaces.d/50-leaf.cfg`:

```bash
# LEAF SN2410 interface definitions

auto lo
iface lo inet loopback

# Uplink to spine
auto swp1
iface swp1
    description Spine-1 Uplink1
    mtu 9216
    address 192.168.100.0/31

auto swp2
iface swp2
    description Spine-1 Uplink2
    mtu 9216
    address 192.168.100.2/31

# Server-facing VLAN trunk (1460 for MTU)
auto swp3
iface swp3
    description Server Uplink Trunk
    mtu 9216
    bridge-access vlans 10-12
    bridge-ports swp3
```

### 2.2. VLAN & Bridge Configuration

In `/etc/cumulus/vlans`, define:

```bash
10   servers
20   mgmt
30   storage
```

Create `/etc/network/interfaces.d/br0.cfg`:

```bash
auto br0
iface br0
    bridge-ports swp3
    bridge-vlan-aware yes
    bridge-vids 10 20 30
    mtu 9216
    address 10.0.0.2/24
```

### 2.3. FRR (BGP EVPN) Configuration

Edit `/etc/frr/frr.conf` on the leaf:

```bash
frr version 9.0
!
hostname leaf-west-1
log syslog informational
!
router bgp 65000
  bgp router-id 10.0.0.2
  no bgp default ipv4-unicast
  neighbor spine-1 peer-group
  neighbor spine-1 remote-as 65000
!
address-family l2vpn evpn
  neighbor spine-1 activate
  advertise-l2vpn evpn
exit-address-family
!
line vty
```

---

## 3. Automation Playbook Snippet (Ansible)

```yaml
- name: Configure Mellanox Cumulus switches
  hosts: all_switches
  become: true
  vars:
    ansible_user: cumulus
  tasks:
    - name: Push interface configurations
      template:
        src: "templates/{{ inventory_hostname }}-50-interfaces.j2"
        dest: "/etc/network/interfaces.d/50-interfaces.cfg"

    - name: Push BGP FRR config
      template:
        src: "templates/{{ inventory_hostname }}-frr.conf.j2"
        dest: "/etc/frr/frr.conf"

    - name: Restart networking
      service:
        name: networking
        state: restarted

    - name: Enable and start FRR
      service:
        name: frr
        state: started
        enabled: yes
```

These examples provide a baseline Cumulus Linux setup for your Mellanox spine and leaf switches. Adjust IP addresses, VLAN IDs, and BGP AS numbers as needed.
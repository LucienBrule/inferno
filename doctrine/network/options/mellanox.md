# Mellanox Switch Options

Mellanox Spectrum switches offer high performance, low latency, and open NOS compatibility, making them an ideal choice for the Inferno cluster's production-grade fabric.

## Refurbished Pricing (eBay Spot Rates)
- **SN2700 (32×100G QSFP28)**: ~$800 each
- **SN2410 (48×25G SFP28 + 8×100G QSFP28)**: ~$800 each
- **SN2010 (18×10/25G SFP28 + 4×40/100G QSFP28)**: $1,000–$2,500

## Key Benefits
- **Ultra-Low Latency**: Sub-microsecond forwarding ideal for AI/ML and storage traffic.
- **High Throughput**: Non-blocking fabric (6.4 Tbps on SN2700, 1.7 Tbps on SN2010).
- **RDMA & RoCE Support**: Full support for DCQCN and PFC for lossless Ethernet.
- **Open Networking**: ONIE loader allows SONiC, Cumulus Linux, or Mellanox Onyx.
- **Flexible Port Configurations**: SN2700 for spine, SN2410 for ToR, SN2010 for leaf or aggregation roles.
- **Community & Documentation**: Extensive open-source community resources and templates.

## Deployment Recommendations
- **Spine:** Deploy SN2700 as the core fabric switch.
- **ToR:** Use SN2410 for per-rack leaf switches (48×25G, 8×100G uplinks).
- **Specialized Leaf:** Optionally use SN2010 for half-rack or lab roles.
- **Operating System:** Standardize on Cumulus Linux (SONiC-compatible) for automation, telemetry, and CLI consistency.

For detailed configuration examples and playbooks, see `network/options/mellanox-config.md`.

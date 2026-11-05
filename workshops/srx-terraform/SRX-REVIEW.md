# Junos preview: review sheet for an SRX engineer

The Dojo WAN simulator renders each gateway's Mist config (template, hub profile, device settings, org networks,
services and service policies) as Junos `set` lines. Students see it with `dojo wan config <device>` and in the
portal. It is invented by `modules/wan-cloud/wan-api/renderer.py` and labelled a preview, but students will read it as
how an SRX is configured, so it needs a check by someone who runs SRX with Mist before the first class.

**How to see it:** `./dojo srx-terraform --test 1 --fast`, wait for the bot to finish, then in `/admin` > Dojo WAN pick
`testuser1`, or in its terminal `dojo wan config ottawa-01-gw` (a spoke with a device override) and `halifax-01-gw`,
or `dojo wan config <name, MAC or serial>` for the hub. A static sample is
the `test_renderer.py` fixture.

## Already checked (2026-11-05, against Junos knowledge, not a device)

Statement names and hierarchy are valid for: `system host-name`/`name-server`/`ntp server`, `vlan-tagging` and
`unit N vlan-id`, `family inet address|dhcp`, zones with `host-inbound-traffic system-services`, `nat source rule-set`
with `then source-nat interface`, custom `applications`, the global `address-book`, zone-pair `policies`,
`routing-options static`, `access address-assignment pool` and `dhcp-local-server`. Fixed: an untagged network on a
port with tagged VLANs no longer renders `unit 0` (Junos refuses it).

## What Mist's docs settle (2026-11-05)

Sources: the WAN Assurance [configuration hierarchy](https://networkingdocs.hpe.com/documentation/us/en/software/mist/mist-wan/topics/concept/mist-wan-assurance-config-hierarchy.html)
page and the [JVD WAN Edge for SRX](https://networkingdocs.hpe.com/documentation/us/en/software/jvd/jvd-wan-edge-for-srx.pdf).
Neither shows Mist-generated SRX config; the JVD is a GUI walkthrough with a few `show` outputs.

- Hubs take hub profiles and spokes take WAN Edge templates (JVD). Lab 5 teaches this.
- A device can override only DNS and the application policy, through "Override Template Settings", not WANs, LANs
  or NTP (hierarchy page). Lab 5's device override is DNS for this reason.
- Site variables are defined in the site configuration; no precedence across levels is documented.
- The JVD's `show` output has overlay tunnels on `st0.N` units and a `vpn_OrgOverlay` routing instance, a hub LAN on a
  tagged unit (`ge-0/0/4.1066`) and a spoke LAN on `irb.1099`, so both LAN styles occur.
- `GET /api/v1/sites/{site_id}/devices/{device_id}/config_cmd` returns the `set` commands Mist pushes (documented
  for switches). Run against one hub and one spoke SRX in a real org, it would answer most questions below at once.

A Chrome-AI summary claimed `irb` LANs, `dns-proxy`, `junos-*` applications, one NAT rule set and a vars precedence
order. None is in the docs, and its claims about hub template plus profile and device NTP are contradicted, so
nothing was changed on its word.

## Questions only a person can settle

1. Does Mist render SRX LANs as `ge-x/x/x` units with `vlan-tagging`, or as `irb` units on switching ports (SRX300)?
2. How does Mist name zones, policies and address sets (by network, by tenant)?
3. LAN zones get `host-inbound-traffic system-services dns`. Does Mist also enable `system services dns dns-proxy`, or
   should `dns` come out?
4. Does Mist use predefined `junos-*` applications for well-known services, or custom ones as the preview does?
5. Global address book plus zone-pair policies, or per-zone address books?
6. DHCP server: `dhcp-local-server` + `access address-assignment`, as rendered?
7. Source NAT: the preview makes one rule set per LAN zone with a rule `all`. What does Mist emit?
8. The preview leaves out management, root-authentication and the hub/spoke IPsec overlay (`security ike`/`ipsec`,
   `st0`, a VPN zone), and says so in its header. Is that acceptable for teaching Lab 5's roles, or should a minimal
   overlay be shown?

Record answers under each question with the date and the reviewer, then fix the renderer and close ROADMAP T4.

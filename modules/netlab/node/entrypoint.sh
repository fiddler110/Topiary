#!/bin/sh
# netlab node start-up. Everything it needs comes from the environment (modules/netlab/generate.py):
#   NODE_ROLE       pc | sw | fw | web
#   NODE_NAME       the container's name, shown in the web page
#   ROOT_PASSWORD   the pod's derived root password (SSH only)
#   MGMT_CIDR       the management network; its interface is left alone and is the only place SSH is allowed
#   NODE_PORTS      space-separated "<docker /29>|<mode>|<vlans>|<lab address>[|<gateway>]" entries, one per data
#                   interface. mode: plain (address on the interface), access, trunk (sw ports), tagged (fw
#                   802.1Q subinterfaces, <lab address> is "<vid>=<addr> ...", comma separated).
# Interface names differ between runtimes (podman ignores interface_name), so each one is found by its address.
set -eu

: "${NODE_ROLE:?}" "${ROOT_PASSWORD:?}" "${MGMT_CIDR:?}"
NODE_NAME="${NODE_NAME:-$(hostname)}"
NODE_PORTS="${NODE_PORTS:-}"

# Interface whose IPv4 address lies in the given /N network (shell arithmetic, no python needed).
ip2int() { IFS=. read -r a b c d <<EOF2
$1
EOF2
  echo $(( (a << 24) | (b << 16) | (c << 8) | d )); }
iface_in() {
  net=${1%/*}; len=${1#*/}
  mask=$(( (0xFFFFFFFF << (32 - len)) & 0xFFFFFFFF ))
  want=$(( $(ip2int "$net") & mask ))
  ip -o -4 addr show | while read -r _ dev _ cidr _; do
    [ "$(( $(ip2int "${cidr%/*}") & mask ))" -eq "$want" ] && { echo "$dev"; break; }
  done
}

mgmt_if=$(iface_in "$MGMT_CIDR")
[ -n "$mgmt_if" ] || { echo "netlab: no interface in $MGMT_CIDR" >&2; exit 1; }

# --- data interfaces -------------------------------------------------------------------------------
sw_ports=""
for entry in $NODE_PORTS; do
  IFS='|' read -r docker mode vlans addr gw <<EOF2
$entry
EOF2
  dev=$(iface_in "$docker")
  [ -n "$dev" ] || { echo "netlab: no interface in $docker" >&2; exit 1; }
  ip addr flush dev "$dev"
  ip link set "$dev" up
  case "$mode" in
    plain)  ip addr add "$addr" dev "$dev"
            [ -z "${gw:-}" ] || ip route add default via "$gw" dev "$dev" ;;
    access|trunk) sw_ports="$sw_ports $dev|$mode|$vlans" ;;
    tagged) for pair in $(echo "$addr" | tr ',' ' '); do
              vid=${pair%%=*}
              ip link add link "$dev" name "$dev.$vid" type vlan id "$vid"
              ip addr add "${pair#*=}" dev "$dev.$vid"
              ip link set "$dev.$vid" up
            done ;;
  esac
done

if [ "$NODE_ROLE" = sw ]; then
  ip link add br0 type bridge vlan_filtering 1
  for p in $sw_ports; do
    IFS='|' read -r dev mode vlans <<EOF2
$p
EOF2
    ip link set "$dev" master br0
    bridge vlan del dev "$dev" vid 1
    if [ "$mode" = access ]; then bridge vlan add dev "$dev" vid "$vlans" pvid untagged
    else for v in $(echo "$vlans" | tr ',' ' '); do bridge vlan add dev "$dev" vid "$v"; done; fi
  done
  ip link set br0 up
fi

# --- firewall baseline: closed, student rules go in LAB ------------------------------------------------
if [ "$NODE_ROLE" = fw ]; then
  sysctl -qw net.ipv4.ip_forward=1 2>/dev/null || true
  iptables -P INPUT DROP
  iptables -P FORWARD DROP
  iptables -A INPUT -i lo -j ACCEPT
  iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A INPUT -i "$mgmt_if" -p tcp --dport 22 -j ACCEPT
  iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT
  iptables -N LAB
  iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A FORWARD -p icmp --icmp-type echo-request -j ACCEPT
  iptables -A FORWARD -j LAB
fi

# --- web server -----------------------------------------------------------------------------------------
if [ "$NODE_ROLE" = web ]; then
  mkdir -p /var/www/html /run/nginx
  printf '<!doctype html><title>%s</title><h1>%s</h1><p>nginx default page.</p>\n' "$NODE_NAME" "$NODE_NAME" > /var/www/html/index.html
  cat > /etc/nginx/nginx.conf <<NGINX
worker_processes 1;
pid /run/nginx/nginx.pid;
events { worker_connections 64; }
http {
  include /etc/nginx/mime.types;
  include /etc/nginx/http.d/*.conf;
  access_log /dev/stdout;
  error_log /dev/stderr;
}
NGINX
  cat > /etc/nginx/http.d/default.conf <<NGINX
server {
  listen 80 default_server;
  root /var/www/html;
}
NGINX
  nginx
fi

# --- ssh ---------------------------------------------------------------------------------------------------
echo "root:$ROOT_PASSWORD" | chpasswd -c sha512 2>/dev/null || echo "root:$ROOT_PASSWORD" | chpasswd
unset ROOT_PASSWORD
ssh-keygen -A >/dev/null
mkdir -p /run/sshd
cat > /etc/ssh/sshd_config <<SSHD
Port 22
PermitRootLogin yes
PasswordAuthentication yes
PrintMotd no
Subsystem sftp internal-sftp
SSHD
exec /usr/sbin/sshd -D -e

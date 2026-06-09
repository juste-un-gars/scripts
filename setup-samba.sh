#!/bin/sh
#
# setup-samba.sh — Installe et configure un partage Samba simple sur Alpine (LXC).
# Crée un utilisateur dédié (sans shell), un sous-dossier partagé, et un accès SMB RW.
#
# Sécurité par défaut : SMB2 minimum, pas d'invité, [homes] désactivé,
# accès restreint au subnet LAN.
#
# Usage : exécuter en root dans le LXC.
#   ./setup-samba.sh
#
set -eu

# ─── Paramètres (à adapter) ──────────────────────────────────────────────
SHARE_USER="share"                 # nom de l'utilisateur Samba/Unix
SHARE_NAME="partage"               # nom du partage visible sur le réseau
SHARE_DIR="/home/${SHARE_USER}/share"  # sous-dossier partagé (pas tout le home)
WORKGROUP="WORKGROUP"
# ALLOW_SUBNET est détecté automatiquement plus bas (modifiable à l'exécution).
# ─────────────────────────────────────────────────────────────────────────

[ "$(id -u)" -eq 0 ] || { echo "Erreur : à exécuter en root." >&2; exit 1; }

# ─── Détection du subnet LAN ─────────────────────────────────────────────
# Récupère l'interface de la route par défaut, puis son réseau CIDR,
# et en dérive un préfixe pour 'hosts allow' (ex: 192.168.1.0/24 -> 192.168.1.).
detect_subnet() {
    _iface=$(ip route show default 2>/dev/null | awk '/default/ {print $5; exit}')
    [ -n "${_iface}" ] || return 1
    _cidr=$(ip -o -f inet addr show "${_iface}" 2>/dev/null \
            | awk '{print $4; exit}')
    [ -n "${_cidr}" ] || return 1

    _ip=${_cidr%/*}
    _mask=${_cidr#*/}
    # Préfixe par classe selon le masque ; au-delà de /24 on retombe sur /24.
    case "${_mask}" in
        8)        echo "${_ip%%.*}." ;;
        16)       echo "$(echo "${_ip}" | cut -d. -f1-2)." ;;
        24|2[5-9]|3[0-2]) echo "$(echo "${_ip}" | cut -d. -f1-3)." ;;
        *)        echo "$(echo "${_ip}" | cut -d. -f1-3)." ;;
    esac
}

DETECTED_SUBNET=$(detect_subnet || true)

if [ -n "${DETECTED_SUBNET}" ]; then
    printf ">>> Subnet LAN détecté : %s0/24 (préfixe : %s)\n" \
        "${DETECTED_SUBNET}" "${DETECTED_SUBNET}"
    printf "    Entrée pour valider, ou saisis un autre préfixe (ex: 10.0.0.) : "
else
    printf ">>> Subnet non détecté automatiquement.\n"
    printf "    Saisis le préfixe autorisé (ex: 192.168.1.) : "
fi

read -r _input
if [ -n "${_input}" ]; then
    ALLOW_SUBNET="${_input}"
else
    ALLOW_SUBNET="${DETECTED_SUBNET}"
fi

[ -n "${ALLOW_SUBNET}" ] || { echo "Erreur : aucun subnet défini." >&2; exit 1; }
echo "    Subnet autorisé : ${ALLOW_SUBNET}"
# ─────────────────────────────────────────────────────────────────────────

echo ">>> Installation de Samba..."
apk update
apk add --no-cache samba samba-common-tools iproute2

echo ">>> Création de l'utilisateur système '${SHARE_USER}' (sans shell)..."
if ! id "${SHARE_USER}" >/dev/null 2>&1; then
    adduser -D -s /sbin/nologin "${SHARE_USER}"
fi

echo ">>> Création du dossier partagé '${SHARE_DIR}'..."
mkdir -p "${SHARE_DIR}"
chown "${SHARE_USER}:${SHARE_USER}" "${SHARE_DIR}"
chmod 0750 "${SHARE_DIR}"

echo ">>> Définition du mot de passe Samba pour '${SHARE_USER}'..."
echo "    (saisis le mot de passe SMB — distinct du mot de passe Unix)"
smbpasswd -a "${SHARE_USER}"
smbpasswd -e "${SHARE_USER}"

echo ">>> Écriture de /etc/samba/smb.conf..."
cat > /etc/samba/smb.conf <<EOF
[global]
   workgroup = ${WORKGROUP}
   server string = Samba LXC
   security = user
   map to guest = never
   server min protocol = SMB2
   client min protocol = SMB2
   # Restreint l'accès au LAN
   hosts allow = ${ALLOW_SUBNET} 127.
   hosts deny = 0.0.0.0/0
   # Durcissement
   disable netbios = yes
   smb ports = 445
   restrict anonymous = 2
   load printers = no
   printing = bsd
   printcap name = /dev/null
   disable spoolss = yes

[${SHARE_NAME}]
   path = ${SHARE_DIR}
   valid users = ${SHARE_USER}
   writable = yes
   browsable = yes
   guest ok = no
   create mask = 0640
   directory mask = 0750
   force user = ${SHARE_USER}
EOF

echo ">>> Validation de la configuration..."
testparm -s >/dev/null

echo ">>> Activation et démarrage du service..."
rc-update add samba default
rc-service samba restart

echo ""
echo "✅ Terminé."
echo "   Partage : \\\\$(hostname -i | awk '{print $1}')\\${SHARE_NAME}"
echo "   User    : ${SHARE_USER}"
echo "   Dossier : ${SHARE_DIR}"

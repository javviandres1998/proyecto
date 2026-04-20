#!/usr/bin/env bash
# =============================================================================
# setup_cron.sh — Instala el cron job del Newsletter ÚLTIMA HORA
# Uso: bash setup_cron.sh
# =============================================================================

set -euo pipefail

# ---------- Colores ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
fail() { echo -e "${RED}✗ $*${NC}"; exit 1; }

echo "============================================="
echo "  ÚLTIMA HORA — Instalador de Cron Job"
echo "============================================="
echo ""

# ---------- 1. Verificar que .env existe ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
NEWSLETTER_SCRIPT="$SCRIPT_DIR/newsletter.py"

if [[ ! -f "$ENV_FILE" ]]; then
  fail ".env no encontrado en $SCRIPT_DIR. Cópialo desde .env.example y configúralo."
fi
ok ".env encontrado"

if [[ ! -f "$NEWSLETTER_SCRIPT" ]]; then
  fail "newsletter.py no encontrado en $SCRIPT_DIR"
fi
ok "newsletter.py encontrado"

# ---------- 2. Detectar Python ----------
PYTHON_BIN=""
for candidate in python3 python3.11 python3.10 python3.9; do
  if command -v "$candidate" &>/dev/null; then
    PYTHON_BIN="$(command -v "$candidate")"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  fail "No se encontró python3. Instala con: sudo apt install python3"
fi
ok "Python encontrado: $PYTHON_BIN ($(${PYTHON_BIN} --version))"

# ---------- 3. Verificar dependencias ----------
echo ""
echo "Verificando dependencias Python…"
if ! "$PYTHON_BIN" -c "import requests, dotenv, pytz" 2>/dev/null; then
  warn "Faltan dependencias. Instalando desde requirements.txt…"
  "$PYTHON_BIN" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
  ok "Dependencias instaladas"
else
  ok "Dependencias OK"
fi

# ---------- 4. Leer SEND_HOUR y TIMEZONE del .env ----------
SEND_HOUR=$(grep -E "^SEND_HOUR=" "$ENV_FILE" | cut -d= -f2 | tr -d ' "' || echo "8")
SEND_HOUR="${SEND_HOUR:-8}"

TIMEZONE=$(grep -E "^TIMEZONE=" "$ENV_FILE" | cut -d= -f2 | tr -d ' "' || echo "Europe/Madrid")
TIMEZONE="${TIMEZONE:-Europe/Madrid}"

LOG_FILE=$(grep -E "^LOG_FILE=" "$ENV_FILE" | cut -d= -f2 | tr -d ' "' || echo "/var/log/newsletter.log")
LOG_FILE="${LOG_FILE:-/var/log/newsletter.log}"

echo ""
echo "  Hora de envío:  $SEND_HOUR:00"
echo "  Zona horaria:   $TIMEZONE"
echo "  Log:            $LOG_FILE"
echo ""

# ---------- 5. Crear archivo de log si no existe ----------
LOG_DIR="$(dirname "$LOG_FILE")"
if [[ ! -d "$LOG_DIR" ]]; then
  warn "Directorio $LOG_DIR no existe. Intentando crear (puede pedir sudo)…"
  sudo mkdir -p "$LOG_DIR"
fi

if [[ ! -f "$LOG_FILE" ]]; then
  warn "Creando archivo de log $LOG_FILE…"
  sudo touch "$LOG_FILE"
  sudo chown "$(whoami):$(whoami)" "$LOG_FILE" 2>/dev/null || true
fi
ok "Archivo de log listo: $LOG_FILE"

# ---------- 6. Construir línea de cron ----------
# Notas sobre la línea generada:
#   -u  → Python en modo unbuffered: stdout/stderr se escriben de inmediato,
#          sin quedar atrapados en el buffer si el proceso termina abruptamente.
#   Sin 'cd': la ruta del .env se resuelve de forma absoluta dentro del script,
#          así que el directorio de trabajo del cron (normalmente $HOME) no importa.
#   2>&1 → stderr se mezcla con stdout y ambos van al mismo archivo de log.
CRON_LINE="0 $SEND_HOUR * * * $PYTHON_BIN -u $NEWSLETTER_SCRIPT >> $LOG_FILE 2>&1"
CRON_MARKER="# newsletter-ultima-hora"

# ---------- 7. Instalar cron (evitar duplicados) ----------
echo ""
EXISTING_CRON=$(crontab -l 2>/dev/null || true)

if echo "$EXISTING_CRON" | grep -q "newsletter-ultima-hora"; then
  warn "Ya existe un cron del newsletter. Reemplazando…"
  NEW_CRON=$(echo "$EXISTING_CRON" | grep -v "newsletter-ultima-hora" | grep -v "newsletter.py")
else
  NEW_CRON="$EXISTING_CRON"
fi

# Añadir nueva línea (marcador en línea separada para que crontab -l sea legible)
{
  echo "$NEW_CRON"
  echo "$CRON_MARKER"
  echo "$CRON_LINE"
} | grep -v '^$' | crontab -

ok "Cron instalado correctamente"

# ---------- 8. Mostrar resultado ----------
echo ""
echo "============================================="
echo -e "${GREEN}  ✓ Instalación completada${NC}"
echo "============================================="
echo ""
echo "  Cron activo (verificar con: crontab -l):"
echo "  $CRON_LINE"
echo ""
echo "  El newsletter se enviará todos los días a las $SEND_HOUR:00 ($TIMEZONE)"
echo "  Logs disponibles en: $LOG_FILE"
echo ""
echo "  Comandos útiles:"
echo "    Ver cron activo:     crontab -l"
echo "    Ver logs en vivo:    tail -f $LOG_FILE"
echo "    Test manual:         $PYTHON_BIN $NEWSLETTER_SCRIPT --test"
echo "    Test de conexión:    $PYTHON_BIN $SCRIPT_DIR/test_conexion.py"
echo ""

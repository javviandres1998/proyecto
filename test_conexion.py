#!/usr/bin/env python3
"""
Script de verificación de conexiones para el Newsletter ÚLTIMA HORA.
Ejecutar con: python3 test_conexion.py
"""

import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone

import requests

# Cargar .env antes de importar config
from dotenv import load_dotenv
load_dotenv()

import config


def check(label: str, ok: bool, detail: str = "") -> bool:
    status = "\033[92m✓ OK\033[0m" if ok else "\033[91m✗ FALLO\033[0m"
    msg = f"  {status}  {label}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    return ok


def test_news_api() -> bool:
    print("\n🌐 1. Conexión a GNews API")
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        resp = requests.get(
            config.NEWS_API_URL,
            params={
                "apikey": config.NEWS_API_KEY,
                "q": "inteligencia artificial | OpenAI | Anthropic",
                "sortby": "publishedAt",
                "from": since,
                "max": 3,
                "lang": "es",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            return check("GNews", False, f"Error: {data['errors']}")
        count = len(data.get("articles", []))
        return check("GNews", True, f"Respuesta OK · {count} artículos de prueba obtenidos")
    except requests.exceptions.ConnectionError:
        return check("GNews", False, "Sin conexión a Internet o DNS fallido")
    except requests.exceptions.Timeout:
        return check("GNews", False, "Timeout — el servidor tardó demasiado")
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response else "?"
        if code == 403:
            return check("GNews", False, "API Key inválida o expirada (403 Forbidden)")
        if code == 429:
            return check("GNews", False, "Límite de peticiones alcanzado (429 Too Many Requests)")
        return check("GNews", False, f"HTTP {code}")
    except Exception as exc:
        return check("GNews", False, str(exc))


def test_smtp() -> bool:
    print("\n📧 2. Conexión SMTP")
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        return check(
            f"SMTP {config.SMTP_HOST}:{config.SMTP_PORT}",
            True,
            f"Login exitoso como {config.SMTP_USER}",
        )
    except smtplib.SMTPAuthenticationError:
        return check("SMTP Auth", False, "Contraseña incorrecta o App Password no configurada")
    except smtplib.SMTPConnectError:
        return check("SMTP Connect", False, f"No se pudo conectar a {config.SMTP_HOST}:{config.SMTP_PORT}")
    except OSError as exc:
        return check("SMTP Network", False, str(exc))
    except Exception as exc:
        return check("SMTP", False, str(exc))


def test_log_write() -> bool:
    print("\n📝 3. Permisos de escritura en logs")
    log_path = config.LOG_FILE
    log_dir = os.path.dirname(log_path)

    if not os.path.isdir(log_dir):
        return check(f"Directorio {log_dir}", False, f"El directorio no existe. Crear con: sudo mkdir -p {log_dir}")

    if not os.access(log_dir, os.W_OK):
        user = os.getenv("USER", "tu_usuario")
        return check(
            f"Escritura en {log_dir}", False,
            f"Sin permiso. Ejecutar: sudo touch {log_path} && sudo chown {user}:{user} {log_path}",
        )

    try:
        with open(log_path, "a") as f:
            f.write(f"# Test de conexión ejecutado el {datetime.now().isoformat()}\n")
        return check(f"Log en {log_path}", True, "Escritura correcta")
    except PermissionError:
        user = os.getenv("USER", "tu_usuario")
        return check(
            f"Log en {log_path}", False,
            f"Sin permiso. Ejecutar: sudo touch {log_path} && sudo chown {user}:{user} {log_path}",
        )
    except Exception as exc:
        return check(f"Log en {log_path}", False, str(exc))


def test_config() -> bool:
    print("\n⚙️  0. Variables de entorno (.env)")
    required = {
        "NEWS_API_KEY": config.NEWS_API_KEY,
        "SMTP_USER": config.SMTP_USER,
        "SMTP_PASSWORD": config.SMTP_PASSWORD,
        "RECIPIENT_EMAIL": ", ".join(config.RECIPIENT_EMAILS),
    }
    all_ok = True
    for key, val in required.items():
        if val and val.strip():
            check(key, True, f"= {val[:6]}{'*' * max(0, len(val)-6)}")
        else:
            check(key, False, "No configurada en .env")
            all_ok = False
    return all_ok


def main():
    print("=" * 55)
    print("  ÚLTIMA HORA — Verificación de conexiones")
    print("=" * 55)

    results = [
        test_config(),
        test_news_api(),
        test_smtp(),
        test_log_write(),
    ]

    total = len(results)
    passed = sum(results)

    print("\n" + "=" * 55)
    if passed == total:
        print(f"\033[92m  ✓ Todo OK ({passed}/{total} checks pasados)\033[0m")
        print("  El sistema está listo para ejecutar newsletter.py")
    else:
        print(f"\033[91m  ✗ {total - passed} check(s) fallaron ({passed}/{total} pasados)\033[0m")
        print("  Revisa los errores anteriores antes de desplegar.")
    print("=" * 55 + "\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

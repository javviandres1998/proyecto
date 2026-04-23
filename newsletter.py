#!/usr/bin/env python3
"""
ÚLTIMA HORA - Newsletter de Noticias IA & Tecnología
Ejecutar con: python3 newsletter.py [--test]
"""

import argparse
import logging
import smtplib
import sys
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Insertar el directorio del script en sys.path ANTES de cualquier import
# local. Cuando cron ejecuta "python3 /ruta/absoluta/newsletter.py" Python
# pone el directorio del script en sys.path[0], pero hacerlo explícito evita
# cualquier edge case con entornos virtuales o PYTHONPATH raros en el VPS.
_PROJECT_DIR = Path(__file__).resolve().parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

import pytz
import requests

import config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("newsletter")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Toda la salida va a stdout. El cron redirige con ">> log 2>&1",
    # así que tanto stdout como stderr quedan en el mismo archivo de log.
    # Un FileHandler adicional crearía entradas duplicadas en el log.
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


# ---------------------------------------------------------------------------
# Obtención de noticias
# ---------------------------------------------------------------------------

def fetch_news(query: str, logger: logging.Logger, max_retries: int = 3) -> list[dict]:
    # GNews API — funciona desde servidores en plan gratuito (100 req/día).
    # El plan gratuito no soporta el parámetro 'from'; devuelve 0 resultados
    # si se incluye. GNews aplica un retraso de 12h en el plan gratuito,
    # lo que es suficiente para un newsletter diario.
    params = {
        "apikey": config.NEWS_API_KEY,
        "q": query,
        "sortby": "publishedAt",
        "max": config.MAX_ARTICLES_PER_CATEGORY,
        "lang": config.NEWS_LANGUAGE.split(",")[0],
    }

    articles = []
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(config.NEWS_API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if "errors" in data:
                raise ValueError(f"GNews error: {data['errors']}")

            articles = [
                a for a in data.get("articles", [])
                if a.get("title") and a.get("url")
            ]
            logger.info("Categoría '%s': %d artículos obtenidos.", query[:60], len(articles))
            return articles

        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response else 0
            wait = 60 if code == 429 else 2 ** attempt
            logger.warning("Intento %d/%d fallido (HTTP %s) para query '%s'. Esperando %ds…",
                           attempt, max_retries, code, query[:60], wait)
            if attempt < max_retries:
                time.sleep(wait)
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Intento %d/%d fallido para query '%s': %s", attempt, max_retries, query[:60], exc)
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    logger.error("No se pudieron obtener noticias para la query tras %d intentos.", max_retries)
    return []


def collect_all_news(logger: logging.Logger) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = {}
    seen_urls: set[str] = set()
    categories = list(config.CATEGORY_QUERIES.items())

    for i, (category, query) in enumerate(categories):
        articles = fetch_news(query, logger)
        unique = []
        for art in articles:
            url = art.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(art)
        results[category] = unique[: config.MAX_ARTICLES_PER_CATEGORY]
        # Pausa entre peticiones para respetar el rate limit de GNews
        if i < len(categories) - 1:
            time.sleep(2)

    return results


# ---------------------------------------------------------------------------
# Generación del HTML
# ---------------------------------------------------------------------------

CATEGORY_META = {
    "urgente":   {"icon": "🔥", "label": "URGENTE / BREAKING",       "color": "#ef4444", "bg": "#1a0a0a"},
    "ia":        {"icon": "🤖", "label": "INTELIGENCIA ARTIFICIAL",  "color": "#a78bfa", "bg": "#0d0a1a"},
    "empresas":  {"icon": "🏢", "label": "EMPRESAS TECH",            "color": "#34d399", "bg": "#0a1a12"},
    "tecnologia":{"icon": "💻", "label": "TECNOLOGÍA GENERAL",       "color": "#60a5fa", "bg": "#0a0f1a"},
}

MONTHS_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
WEEKDAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def format_date_es(dt: datetime) -> str:
    weekday = WEEKDAYS_ES[dt.weekday()].capitalize()
    month = MONTHS_ES[dt.month]
    return f"{weekday}, {dt.day} de {month} de {dt.year}"


def format_article_date(published_at: str) -> str:
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M UTC")
    except Exception:
        return published_at or "Fecha desconocida"


def _article_card(article: dict, accent: str) -> str:
    title = article.get("title", "Sin título").replace("<", "&lt;").replace(">", "&gt;")
    description = (article.get("description") or article.get("content") or "").strip()
    description = description[:280] + ("…" if len(description) > 280 else "")
    description = description.replace("<", "&lt;").replace(">", "&gt;")
    url = article.get("url", "#")
    source = (article.get("source") or {}).get("name", "Fuente desconocida")
    pub_date = format_article_date(article.get("publishedAt", ""))
    img = article.get("image", "") or article.get("urlToImage", "")

    img_block = ""
    if img:
        img_block = f'<img src="{img}" alt="" style="width:100%;max-height:200px;object-fit:cover;border-radius:8px 8px 0 0;display:block;">'

    return f"""
    <div style="background:#1e1e2e;border-radius:12px;margin-bottom:20px;overflow:hidden;border:1px solid #2d2d3f;box-shadow:0 4px 16px rgba(0,0,0,0.4);">
      {img_block}
      <div style="padding:20px;">
        <h3 style="margin:0 0 10px;font-size:17px;line-height:1.4;color:#f1f1f5;">{title}</h3>
        <p style="margin:0 0 16px;font-size:14px;color:#a0a0b8;line-height:1.6;">{description}</p>
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <span style="font-size:12px;color:#6b6b85;">📰 {source} &nbsp;·&nbsp; 🕐 {pub_date}</span>
          <a href="{url}" target="_blank"
             style="background:{accent};color:#fff;text-decoration:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:600;display:inline-block;">
            Leer artículo completo &rarr;
          </a>
        </div>
      </div>
    </div>
    """


def _category_section(category: str, articles: list[dict]) -> str:
    meta = CATEGORY_META[category]
    cards = "".join(_article_card(a, meta["color"]) for a in articles)
    return f"""
    <div style="margin-bottom:40px;">
      <div style="background:{meta['bg']};border-left:4px solid {meta['color']};padding:14px 20px;border-radius:8px;margin-bottom:20px;">
        <h2 style="margin:0;font-size:20px;color:{meta['color']};letter-spacing:1px;">
          {meta['icon']} {meta['label']}
        </h2>
      </div>
      {cards}
    </div>
    """


def build_html(news: dict[str, list[dict]], send_time: datetime) -> str:
    tz = pytz.timezone(config.TIMEZONE)
    now = send_time.astimezone(tz)
    date_str = format_date_es(now)
    time_str = now.strftime("%H:%M")
    tz_name = config.TIMEZONE

    total = sum(len(v) for v in news.values())

    sections_html = ""
    for cat in ["urgente", "ia", "empresas", "tecnologia"]:
        articles = news.get(cat, [])
        if articles:
            sections_html += _category_section(cat, articles)

    if not sections_html:
        sections_html = """
        <div style="text-align:center;padding:60px 20px;color:#6b6b85;">
          <p style="font-size:18px;">No se encontraron noticias nuevas en las últimas 24 horas.</p>
          <p>Esto puede deberse a límites de la API o falta de noticias relevantes.</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ÚLTIMA HORA - {date_str}</title>
</head>
<body style="margin:0;padding:0;background-color:#0d0d1a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d1a;padding:20px 0;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width:680px;margin:0 auto;">

          <!-- HEADER -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
                        border-radius:16px 16px 0 0;padding:40px 30px;text-align:center;
                        border-bottom:3px solid #e94560;">
              <div style="font-size:11px;letter-spacing:4px;color:#e94560;font-weight:700;margin-bottom:8px;text-transform:uppercase;">
                ● EN VIVO
              </div>
              <h1 style="margin:0;font-size:42px;font-weight:900;color:#ffffff;letter-spacing:2px;
                          text-shadow:0 0 30px rgba(233,69,96,0.5);">
                ÚLTIMA HORA
              </h1>
              <div style="margin-top:12px;font-size:16px;color:#a0a0c0;font-weight:400;">
                {date_str}
              </div>
              <div style="margin-top:16px;background:rgba(233,69,96,0.15);border:1px solid rgba(233,69,96,0.3);
                          border-radius:20px;padding:6px 18px;display:inline-block;">
                <span style="color:#e94560;font-size:13px;font-weight:600;">
                  {total} noticias · IA &amp; Tecnología
                </span>
              </div>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="background:#13131f;padding:30px 25px;">
              {sections_html}
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background:#0d0d1a;border-top:1px solid #1e1e2e;border-radius:0 0 16px 16px;
                        padding:24px 30px;text-align:center;">
              <p style="margin:0 0 8px;font-size:13px;color:#6b6b85;">
                Newsletter enviado el {date_str} a las {time_str} ({tz_name})
              </p>
              <p style="margin:0;font-size:12px;color:#4a4a60;">
                Noticias obtenidas automáticamente · Fuentes: GNews API
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Envío de email
# ---------------------------------------------------------------------------

def send_email(html: str, subject: str, logger: logging.Logger) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.SMTP_USER
    msg["To"] = ", ".join(config.RECIPIENT_EMAILS)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_USER, config.RECIPIENT_EMAILS, msg.as_string())
        logger.info("Email enviado correctamente a: %s", ", ".join(config.RECIPIENT_EMAILS))
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Error de autenticación SMTP. Verifica SMTP_USER y SMTP_PASSWORD.")
    except smtplib.SMTPException as exc:
        logger.error("Error SMTP al enviar: %s", exc)
    except OSError as exc:
        logger.error("Error de red al conectar al servidor SMTP: %s", exc)
    return False


def send_warning_email(reason: str, logger: logging.Logger) -> None:
    subject = "⚠️ Newsletter ÚLTIMA HORA — Sin noticias hoy"
    html = f"""<!DOCTYPE html>
<html lang="es"><body style="background:#0d0d1a;color:#f1f1f5;font-family:sans-serif;padding:40px;">
  <h2 style="color:#e94560;">⚠️ Aviso del sistema de Newsletter</h2>
  <p>{reason}</p>
  <p style="color:#6b6b85;font-size:13px;">Mensaje automático del sistema Newsletter ÚLTIMA HORA</p>
</body></html>"""
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = config.SMTP_USER
            msg["To"] = ", ".join(config.RECIPIENT_EMAILS)
            msg.attach(MIMEText(html, "html", "utf-8"))
            server.sendmail(config.SMTP_USER, config.RECIPIENT_EMAILS, msg.as_string())
        logger.info("Email de aviso enviado.")
    except Exception as exc:
        logger.error("No se pudo enviar el email de aviso: %s", exc)


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Newsletter ÚLTIMA HORA - IA & Tecnología")
    parser.add_argument("--test", action="store_true", help="Modo test: envía el email sin esperar el horario")
    args = parser.parse_args()

    logger = setup_logging()
    logger.info("=== Iniciando Newsletter ÚLTIMA HORA (modo %s) ===", "TEST" if args.test else "producción")
    logger.info(".env cargado desde: %s", _PROJECT_DIR / ".env")

    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)

    # En producción el cron gestiona el horario, pero por si se usa APScheduler futuro
    logger.info("Hora actual: %s", now.strftime("%Y-%m-%d %H:%M %Z"))

    # Recolectar noticias
    logger.info("Buscando noticias de las últimas 24 horas…")
    news = collect_all_news(logger)

    total = sum(len(v) for v in news.values())
    logger.info("Total de artículos únicos recopilados: %d", total)

    if total == 0:
        reason = "No se encontraron noticias nuevas en las últimas 24 horas. Puede ser un límite de la API."
        logger.warning(reason)
        send_warning_email(reason, logger)
        sys.exit(0)

    # Generar email
    subject = f"ÚLTIMA HORA — {format_date_es(now)}"
    html = build_html(news, now)

    if args.test:
        # En modo test también guardamos el HTML para revisarlo
        output_path = "/tmp/newsletter_preview.html"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            logger.info("HTML de previsualización guardado en: %s", output_path)
        except OSError as exc:
            logger.warning("No se pudo guardar la previsualización: %s", exc)

    # Enviar
    success = send_email(html, subject, logger)
    if success:
        logger.info("=== Newsletter enviado exitosamente ===")
    else:
        logger.error("=== Fallo al enviar el newsletter ===")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Newsletter ÚLTIMA HORA — Contexto del proyecto

## Qué es este proyecto
Sistema automatizado de newsletter diario de noticias sobre IA y Tecnología.
Se ejecuta en un VPS Ubuntu (Hostinger) mediante cron job.

## Estado del despliegue
- **VPS**: 45.93.138.147 (Hostinger, Ubuntu 24.04)
- **Ruta del proyecto**: `/root/newsletter/`
- **Python**: `/root/newsletter/venv/bin/python` (entorno virtual, obligatorio en Ubuntu 24.04)
- **Cron activo**: `0 8 * * *` — envía todos los días a las 8:00 AM Europe/Madrid
- **Log**: `/var/log/newsletter.log`

## API de noticias
- **Proveedor**: GNews API (gnews.io) — plan gratuito
- **Limitaciones conocidas del plan gratuito**:
  - Trata espacios como AND (múltiples palabras = 0 resultados)
  - No soporta `sortby` (devuelve 0 artículos silenciosamente)
  - No soporta `from` para filtrar por fecha
  - Sí funciona desde servidores VPS (a diferencia de NewsAPI)
  - 100 peticiones/día, delay de 12h en las noticias
- **Queries actuales**: una sola keyword por categoría (`AI`, `ChatGPT`, `OpenAI`, `technology`)

## Configuración SMTP
- Servidor: smtp.gmail.com:587
- Remitente y destinatario: javviandres1998@gmail.com
- Autenticación: Gmail App Password (verificación en dos pasos activada)

## Decisiones técnicas importantes
- `load_dotenv()` usa ruta absoluta via `Path(__file__).resolve().parent / ".env"` para que funcione en cron
- `sys.path.insert(0, str(_PROJECT_DIR))` antes de `import config` por robustez en cron
- Solo `StreamHandler(stdout)` en logging — el cron captura todo con `>> log 2>&1` (sin FileHandler para evitar duplicados)
- Python con flag `-u` en el cron para output unbuffered
- Pausa de 2s entre peticiones a GNews para evitar rate limiting (429)
- Error 429 espera 60s antes de reintentar

## Comandos habituales en el VPS
```bash
# Test manual
/root/newsletter/venv/bin/python /root/newsletter/newsletter.py --test

# Ver logs en vivo
tail -f /var/log/newsletter.log

# Verificar cron
crontab -l

# Actualizar código desde GitHub
cd /root/newsletter && git pull origin claude/news-newsletter-automation-GmZk4
```

## Rama de desarrollo
`claude/news-newsletter-automation-GmZk4` en `javviandres1998/proyecto`

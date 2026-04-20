# ÚLTIMA HORA — Newsletter Automatizado de IA & Tecnología

Sistema de newsletter automático que envía cada día un resumen de las noticias más relevantes sobre Inteligencia Artificial y Tecnología. Funciona 24/7 en un VPS Ubuntu mediante cron jobs.

---

## Requisitos

- Ubuntu 20.04 / 22.04 / 24.04 (VPS Hostinger u otro)
- Python 3.9 o superior
- Cuenta en [NewsAPI.org](https://newsapi.org) (gratuita)
- Cuenta de Gmail con App Password configurada

---

## Estructura del proyecto

```
newsletter/
├── newsletter.py        # Script principal
├── config.py            # Carga de configuración desde .env
├── test_conexion.py     # Verificación de conexiones antes de desplegar
├── setup_cron.sh        # Instalador del cron job
├── requirements.txt     # Dependencias Python
├── .env                 # Credenciales (NO subir a Git)
└── .env.example         # Plantilla del .env
```

---

## Instalación paso a paso

### 1. Clonar el repositorio en el VPS

```bash
ssh usuario@ip-del-vps
git clone https://github.com/tu-usuario/newsletter.git
cd newsletter
```

### 2. Instalar dependencias Python

```bash
pip3 install -r requirements.txt
```

Si pip3 no está disponible:

```bash
sudo apt update && sudo apt install python3-pip -y
pip3 install -r requirements.txt
```

### 3. Obtener API Key de NewsAPI (gratis)

1. Ir a [https://newsapi.org/register](https://newsapi.org/register)
2. Crear una cuenta gratuita (plan Developer: 100 peticiones/día)
3. Copiar la API Key que aparece en el dashboard

> **Nota:** El plan gratuito tiene un retraso de 24h en noticias. Para noticias en tiempo real se necesita el plan de pago. El sistema funciona correctamente con el plan gratuito.

### 4. Configurar contraseña de aplicación en Gmail

Gmail requiere una "App Password" (no la contraseña normal) para SMTP:

1. Ir a [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Activar **Verificación en dos pasos** (obligatorio)
3. Buscar **Contraseñas de aplicaciones** (App Passwords)
4. Crear una nueva: seleccionar "Correo" y "Otro (nombre personalizado)" → "Newsletter"
5. Copiar la contraseña de 16 caracteres generada

### 5. Configurar el archivo .env

```bash
cp .env.example .env
nano .env
```

Rellenar con tus datos:

```env
NEWS_API_KEY=abc123tu_api_key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
RECIPIENT_EMAIL=destino@gmail.com
SEND_HOUR=8
TIMEZONE=Europe/Madrid
LOG_FILE=/var/log/newsletter.log
```

> Para enviar a múltiples destinatarios: `RECIPIENT_EMAIL=uno@gmail.com,dos@gmail.com`

### 6. Verificar que todo funciona antes de desplegar

```bash
python3 test_conexion.py
```

Salida esperada:

```
=====================================================
  ÚLTIMA HORA — Verificación de conexiones
=====================================================

⚙️  0. Variables de entorno (.env)
  ✓ OK  NEWS_API_KEY   = abc123...
  ✓ OK  SMTP_USER      = tu_em...
  ...

🌐 1. Conexión a NewsAPI.org
  ✓ OK  NewsAPI   Respuesta OK · 3 artículos de prueba obtenidos

📧 2. Conexión SMTP
  ✓ OK  SMTP smtp.gmail.com:587   Login exitoso como tu_email@gmail.com

📝 3. Permisos de escritura en logs
  ✓ OK  Log en /var/log/newsletter.log   Escritura correcta

=====================================================
  ✓ Todo OK (4/4 checks pasados)
  El sistema está listo para ejecutar newsletter.py
=====================================================
```

### 7. Test manual del newsletter completo

Envía el newsletter inmediatamente para verificar que llega correctamente:

```bash
python3 newsletter.py --test
```

Esto:
- Busca noticias reales
- Genera el HTML del email
- Guarda una previsualización en `/tmp/newsletter_preview.html`
- Envía el email al destinatario configurado

### 8. Instalar el cron job automático

```bash
bash setup_cron.sh
```

El script:
- Detecta automáticamente la ruta de Python
- Instala las dependencias si faltan
- Crea el archivo de log con los permisos correctos
- Instala el cron job sin duplicados

### 9. Verificar que el cron está activo

```bash
crontab -l
```

Salida esperada:

```
# newsletter-ultima-hora
0 8 * * * cd /home/usuario/newsletter && /usr/bin/python3 /home/usuario/newsletter/newsletter.py >> /var/log/newsletter.log 2>&1
```

---

## Comandos útiles en producción

```bash
# Ver los últimos logs
tail -50 /var/log/newsletter.log

# Seguir los logs en tiempo real
tail -f /var/log/newsletter.log

# Ejecutar manualmente (sin modo test, igual que el cron)
python3 /home/usuario/newsletter/newsletter.py

# Ejecutar en modo test (con preview HTML)
python3 /home/usuario/newsletter/newsletter.py --test

# Ver cron activo
crontab -l

# Eliminar el cron (si necesitas desinstalarlo)
crontab -l | grep -v "newsletter" | crontab -
```

---

## Categorías del newsletter

| Categoría | Descripción |
|-----------|-------------|
| 🔥 URGENTE / BREAKING | Noticias de última hora sobre IA |
| 🤖 INTELIGENCIA ARTIFICIAL | LLMs, modelos generativos, investigación |
| 🏢 EMPRESAS TECH | OpenAI, Anthropic, Google, Meta, Microsoft, xAI |
| 💻 TECNOLOGÍA GENERAL | Hardware, ciberseguridad, robótica, quantum |

---

## Solución de problemas

### El email no llega

1. Verificar los logs: `tail -f /var/log/newsletter.log`
2. Comprobar que el App Password de Gmail es correcto (sin espacios o con espacios, ambos funcionan)
3. Ejecutar `python3 test_conexion.py` para diagnóstico
4. Verificar que Gmail no tiene bloqueado el acceso de apps menos seguras

### "No se encontraron noticias"

- El plan gratuito de NewsAPI tiene delay de 24h
- Verificar que NEWS_API_KEY es válida en [newsapi.org/account](https://newsapi.org/account)
- El sistema envía un email de aviso cuando no hay noticias

### El cron no se ejecuta

```bash
# Ver si el servicio cron está activo
sudo systemctl status cron

# Activarlo si está parado
sudo systemctl enable cron && sudo systemctl start cron

# Verificar que el log tiene permisos de escritura
ls -la /var/log/newsletter.log
```

### Error de permisos en el log

```bash
sudo touch /var/log/newsletter.log
sudo chown $(whoami):$(whoami) /var/log/newsletter.log
```

---

## Variables de entorno — referencia completa

| Variable | Requerida | Por defecto | Descripción |
|----------|-----------|-------------|-------------|
| `NEWS_API_KEY` | ✓ | — | API Key de newsapi.org |
| `SMTP_HOST` | — | smtp.gmail.com | Servidor SMTP |
| `SMTP_PORT` | — | 587 | Puerto SMTP (587 = STARTTLS) |
| `SMTP_USER` | ✓ | — | Email del remitente |
| `SMTP_PASSWORD` | ✓ | — | App Password de Gmail |
| `RECIPIENT_EMAIL` | ✓ | — | Destinatario(s), separados por coma |
| `SEND_HOUR` | — | 8 | Hora de envío (0-23) |
| `TIMEZONE` | — | Europe/Madrid | Zona horaria (formato pytz) |
| `MAX_ARTICLES_PER_CATEGORY` | — | 5 | Máximo artículos por categoría |
| `NEWS_LANGUAGE` | — | es,en | Idioma preferido (NewsAPI usa el primero) |
| `LOG_FILE` | — | /var/log/newsletter.log | Ruta del archivo de log |

---

## Alternativas a NewsAPI si llegas al límite gratuito

- **GNews API** — [gnews.io](https://gnews.io) — 100 req/día gratis
- **TheNewsAPI** — [thenewsapi.com](https://www.thenewsapi.com) — 100 req/día gratis
- **Currents API** — [currentsapi.services](https://currentsapi.services) — 600 req/día gratis

Para usar una alternativa, modificar en `config.py` la variable `NEWS_API_URL` y adaptar los parámetros en la función `fetch_news()` de `newsletter.py`.

# PoC 1 - Agentes con LangGraph

Repositorio con dos agentes en Python orientados a pruebas de concepto (PoC):

- `dollar-agent`: analisis por escenarios para presion direccional USD/COP.
- `santafe-agente`: busqueda, filtrado y resumen de noticias de Independiente Santa Fe.

## Estructura del repo

```text
PoC 1/
  dollar-agent/
  santafe-agente/
```

## Requisitos

- Python 3.11+
- `pip`
- Clave de OpenAI (`OPENAI_API_KEY`)

## Configuracion rapida

1. Crear entorno virtual en la raiz:

```bash
python -m venv .venv
```

2. Activar entorno virtual:

Windows (PowerShell):

```bash
.\\.venv\\Scripts\\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

3. Instalar dependencias (ambos agentes):

```bash
pip install -r dollar-agent/requirements.txt
pip install -r santafe-agente/requirements.txt
```

## Variables de entorno

Cada agente usa su propio archivo `.env` dentro de su carpeta.

### `santafe-agente/.env` (minimo)

```env
OPENAI_API_KEY=tu_api_key
OPENAI_MODEL=gpt-4.1-mini
```

### `dollar-agent/.env` (minimo recomendado para pruebas locales)

```env
OPENAI_API_KEY=tu_api_key
OPENAI_MODEL=gpt-4.1-mini
SEND_EMAIL_ENABLED=false
RUN_START_HOUR=0
RUN_END_HOUR=23
```

Notas:
- Si `SEND_EMAIL_ENABLED=true`, tambien debes configurar `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` y `SENDGRID_TO_EMAIL`.
- `dollar-agent` por defecto ejecuta solo entre las horas definidas por `RUN_START_HOUR` y `RUN_END_HOUR`.

## Como ejecutar

### 1) Agente USD/COP

```bash
cd dollar-agent
python -m app.main
```

Resultado esperado:
- imprime un resumen ejecutivo en consola.
- guarda historicos en `dollar-agent/data/history/`.

### 2) Agente de noticias de Santa Fe

```bash
cd santafe-agente
python -m app.main --query "ultimas noticias"
```

Resultado esperado:
- imprime conteos de noticias, noticias filtradas y respuesta final.

## Stack tecnico

- LangGraph
- LangChain / LangChain OpenAI
- Python dotenv
- Requests / Feedparser

## Estado

Proyecto en fase PoC. No usar como sistema de trading ni como asesoria financiera.

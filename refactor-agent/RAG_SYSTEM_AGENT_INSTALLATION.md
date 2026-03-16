# Integracion del Engineering Governance Agent en rag_system

Este documento resume como mover el agente desde `Agents---PoC/refactor-agent` hacia `rag_system`, como conectarlo con el workflow existente `unit-tests`, y cual es la diferencia entre los dos workflows YAML actuales.

## Objetivo

Mantener el workflow actual de `rag_system` para pruebas unitarias y agregar un workflow separado que ejecute el agente solo despues de que `unit-tests` termine correctamente.

La secuencia objetivo queda asi:

`unit-tests` -> `governance-agent-after-unit-tests` -> materializacion de review branch -> validacion de review branch -> PR/comentario

## Paso a paso para mover e instalar el agente

1. Copiar el agente dentro de `rag_system`.

Ruta recomendada:

```text
rag_system/
  tools/
    refactor-agent/
```

2. Verificar que dentro de `rag_system/tools/refactor-agent` existan al menos estos archivos:

```text
tools/refactor-agent/requirements.txt
tools/refactor-agent/app/entrypoints/github_actions/runner.py
tools/refactor-agent/app/
tools/refactor-agent/policies/
tools/refactor-agent/prompt-guidance/
```

La carpeta `policies/` contiene politicas tecnicas por perfil para documentacion, scope y seguridad de refactor.

La carpeta `prompt-guidance/` contiene la guia estructural del repositorio que se inyecta en el prompt del LLM, por ejemplo:

- framework o plataforma principal
- arquitectura esperada
- principios de diseno
- nombres de carpetas por capa
- restricciones de dependencias entre capas
- guardrails de refactor y naming conventions

Archivo esperado por defecto:

```text
tools/refactor-agent/prompt-guidance/repository-guidance.yaml
```

3. No modificar ni reemplazar el workflow actual `unit-tests`.

Tu workflow actual sigue siendo el gate primario de salud del repo. El agente no debe ejecutarse antes de ese gate.

4. Crear un workflow nuevo en `rag_system`:

```text
.github/workflows/governance-agent-after-unit-tests.yml
```

El contenido base debe salir de:

`refactor-agent/.github/workflows/rag_system_governance_after_unit_tests.yml`

5. Configurar secretos en `rag_system`.

Minimo requerido:

```text
OPENAI_API_KEY
```

`GITHUB_TOKEN` lo inyecta GitHub Actions automaticamente en la mayoria de los casos. Solo haria falta un PAT si despues decides soportar escenarios que el token por defecto no cubra.

6. Mantener permisos del workflow nuevo para mutaciones controladas.

El workflow nuevo usa:

```yaml
permissions:
  contents: write
  pull-requests: write
  issues: write
```

Eso es necesario para push de review branch, creacion/reutilizacion de PR y publicacion de comentarios.

7. Instalar dependencias del agente en un entorno aislado.

La plantilla ya lo hace creando:

```text
.venv-governance-agent
```

Eso evita mezclar dependencias del agente con las dependencias del backend de `rag_system`.

8. Hacer una prueba manual antes del rollout automatico.

Usar `workflow_dispatch` del workflow nuevo con:

```text
agent_path=tools/refactor-agent
base_ref=<base real>
head_ref=<head real>
create_review_pull_request=false
```

Con eso validas:

- checkout correcto
- instalacion del agente
- diff correcto
- generacion de reporte
- ejecucion del runner

9. Hacer la primera prueba automatica con un PR del mismo repo.

La plantilla esta pensada para correr automaticamente solo cuando:

- `unit-tests` termina con `success`
- el evento origen fue `pull_request`
- el PR pertenece al mismo repo y no a un fork

10. Confirmar el flujo completo en `rag_system`.

Resultado esperado:

- `unit-tests` termina bien
- corre `governance-agent-after-unit-tests`
- el agente analiza el diff del PR
- materializa review branch
- valida la review branch
- solo si esa validacion pasa, crea o reutiliza PR y publica comentario

11. Configurar la guia estructural del repo destino para el LLM.

Crear o adaptar este archivo en `rag_system`:

```text
tools/refactor-agent/prompt-guidance/repository-guidance.yaml
```

Ese archivo no reemplaza `policies/`. Cumple otro rol: darle al LLM contexto arquitectonico y convenciones concretas del repo destino para que las sugerencias y refactors respeten tu estructura real.

Ejemplos de contenido util:

- `.NET 8` como framework
- `Hexagonal Architecture` o `Clean Architecture`
- carpeta de `Api`
- carpeta de `Persistence`
- carpeta de `Application`
- carpeta de `Domain`
- reglas de imports entre capas
- principios SOLID esperados
- restricciones para repositorios, handlers y servicios

## Los dos YAML estan duplicados?

No. Se parecen porque ambos ejecutan el mismo runner del agente, pero cumplen papeles distintos.

### 1. `governance_agent.yml`

Archivo:

`refactor-agent/.github/workflows/governance_agent.yml`

Rol:

- workflow propio del proyecto del agente
- sirve para desarrollar, probar y operar el agente dentro de `refactor-agent`
- dispara por `pull_request` y `workflow_dispatch`
- asume que el repo actual ya es el repo del agente
- instala dependencias desde `requirements.txt` en la raiz de `refactor-agent`
- ejecuta `python -m app.entrypoints.github_actions.runner`

En otras palabras: este YAML pertenece al repositorio fuente del agente.

### 2. `rag_system_governance_after_unit_tests.yml`

Archivo:

`refactor-agent/.github/workflows/rag_system_governance_after_unit_tests.yml`

Rol:

- plantilla de integracion para el repo destino `rag_system`
- no reemplaza `unit-tests`
- se dispara por `workflow_run` despues de `unit-tests`
- resuelve el contexto real del PR una vez que `unit-tests` ya acabo
- hace checkout del repo destino
- ejecuta el agente embebido en `tools/refactor-agent`
- crea un virtualenv aislado solo para el agente

En otras palabras: este YAML no es para seguir viviendo en `refactor-agent` como workflow operativo principal; es una plantilla para copiar al repo destino.

## Entonces conviene mantener ambos?

Si, por ahora.

Conviene mantener ambos mientras el agente siga teniendo vida propia en `Agents---PoC` y todavia no se haya completado el cutoff hacia `rag_system`.

La regla practica es esta:

- `governance_agent.yml`: se queda en `refactor-agent` para desarrollar y validar el agente.
- `rag_system_governance_after_unit_tests.yml`: se copia a `rag_system` y alla se convierte en el workflow operativo real.

## Cuando si habria duplicacion real?

Habria duplicacion real si intentaras dejar ambos activos para el mismo fin dentro del mismo repo destino.

Ejemplo de mala configuracion:

- un workflow que corre el agente en cada `pull_request`
- y otro que corre el mismo agente despues de `unit-tests`

Eso duplicaria ejecucion, artefactos, comentarios y riesgo operativo.

## Recomendacion final

1. Mantener `governance_agent.yml` en `refactor-agent` como workflow de desarrollo del agente.
2. Copiar `rag_system_governance_after_unit_tests.yml` a `rag_system` como workflow de produccion.
3. No ejecutar ambos en `rag_system` al mismo tiempo.
4. Una vez completada la Fase 10 y estabilizado el rollout en `rag_system`, reevaluar si el workflow del repo fuente sigue siendo necesario o queda solo para mantenimiento del agente.
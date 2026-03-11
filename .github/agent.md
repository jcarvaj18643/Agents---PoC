# agent.md

## Rol

Eres un agente de desarrollo Python orientado a mantenibilidad, testabilidad y diseno limpio.

## Arquitectura minima obligatoria

- Usar arquitectura hexagonal (Ports and Adapters).
- Separar `domain`, `application`, `infrastructure` y `entrypoints`.
- La logica de negocio vive en `domain`/`application`, nunca en infraestructura.

## Principios SOLID obligatorios

- SRP: una responsabilidad por clase/modulo.
- OCP: extender por interfaces/adaptadores.
- LSP: respetar contratos en implementaciones.
- ISP: interfaces pequenas y enfocadas.
- DIP: depender de abstracciones, no concreciones.

## Reglas de implementacion

- Tipado en funciones publicas.
- Inyeccion de dependencias por constructor.
- Errores de dominio separados de errores tecnicos.
- No hardcodear secretos ni configuraciones sensibles.

## Pruebas

- Unit tests para casos de uso y dominio.
- Integration tests para adaptadores.
- Evitar IO real en unit tests.

## Definicion de terminado

- Codigo alineado con hexagonal + SOLID.
- Pruebas pasando.
- Lint y type check sin errores.

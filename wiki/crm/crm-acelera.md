# CRM - Acelera

Base de datos principal del pipeline comercial en Notion. Registra prospectos desde el primer contacto hasta el cierre (o descarte).

- **Icono / título**: 📋 CRM - Acelera
- **Notion URL**: https://www.notion.so/9b8e0b5662a143a7b7bd578722707b94
- **Database ID**: `9b8e0b56-62a1-43a7-b7bd-578722707b94`
- **Data source (collection)**: `cfb2bcf6-391d-4de1-b855-165f80686b95`
- **Página padre**: [CRM](https://www.notion.so/320c40c66f0980f5bff2dfdda30034d0)

## Key Takeaways

- Es el **pipeline completo**: prospectos + cerrados viven en la misma tabla, discriminados por `Estado Cliente`.
- El campo `Estado Cliente = "Cliente Cerrado"` **dispara automatización en Make** (trigger documentado en la descripción del campo).
- La carpeta de Drive asociada a cada prospecto se llena automáticamente desde Make en `📁 Link Carpeta Drive`.
- La vista [[clientes-cerrados]] es solo un filtro sobre esta misma base — no es una DB aparte.

## Schema (campos)

### Identidad / contacto
| Campo | Tipo | Notas |
|---|---|---|
| `Nombre Prospecto` | title | Campo principal |
| `Correo electrónico` | email | |
| `Teléfono` | phone | |
| `LinkedIn` | url | |

### Pipeline / estado
| Campo | Tipo | Opciones |
|---|---|---|
| `Estado Cliente` | select | `Prospecto`, `Cliente Cerrado` — **cambio a "Cliente Cerrado" activa automatización en Make** |
| `Prioridad follow-up` | select | `Alta` (rojo), `Media` (amarillo), `Baja` (gris), `No contactar` (café) |
| `Siguiente acción` | select | `Enviar mensaje`, `Llamar`, `Enviar propuesta/info`, `Reagendar`, `Cerrar ciclo` |
| `Resultado llamada` | select | `Cerrada`, `Consiguiendo dinero`, `Seguimiento`, `No dinero`, `Perdida`, `No show`, `Reagendada`, `Agendar`, `No contesto`, `Agendado`, `Descartado` |
| `Asistió llamada` | checkbox | |

### Fechas
| Campo | Tipo | Notas |
|---|---|---|
| `Fecha Agregado` | created_time | Automático |
| `Fecha llamada` | date | Fecha de la llamada registrada |
| `Fecha Ultima Llamada` | date | |
| `Fecha próximo contacto` | date | Usado por la vista de follow-up |

### Métricas
| Campo | Tipo | Notas |
|---|---|---|
| `Calificado` | number | Entero (precision 0), formato con comas |
| `Cash collected` | number | Formato dólar, precision 0 |

### Notas y enlaces
| Campo | Tipo | Notas |
|---|---|---|
| `Notas / Plan de pago` | text | |
| `Notas llamada` | text | |
| `Link Grabacion` | url | |
| `📁 Link Carpeta Drive` | url | Lo llena Make automáticamente |

## Vistas en Notion

1. **Todas** — Tabla completa ordenada por `Fecha llamada` desc. Muestra todos los campos.
2. **📌 Follow-up (Hoy y vencidos)** — Filtro `Fecha próximo contacto <= today`, ordenado por `Prioridad follow-up` asc, luego `Fecha próximo contacto` asc. Sirve como cola de trabajo diaria.

## Flujos / automatizaciones

- **Make**: al cambiar `Estado Cliente` a `Cliente Cerrado`, Make dispara (entre otras cosas) la creación de la carpeta en Google Drive y rellena `📁 Link Carpeta Drive`.
- Los prospectos cerrados siguen viviendo aquí — se filtran vía [[clientes-cerrados]] para reportes.

## Relaciones

- Derivada: [[clientes-cerrados]] — vista filtrada de esta base.
- Relacionada (no enlazada por schema): **CRM - Llamadas** en Notion (`a8379103-9ada-490e-813b-c0e89a787181`) — fuera del vault por ahora.

## Open questions / por documentar

- ¿Cómo se define `Calificado`? (número — falta criterio/rubrica).
- ¿Qué hace exactamente el escenario de Make completo? Solo conocemos el trigger y un efecto (carpeta Drive).
- Relación conceptual con `CRM - Llamadas` — ¿se sincronizan manualmente, vía Make, o son independientes?

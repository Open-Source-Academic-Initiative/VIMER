# Identidad visual VIMER / OpenSAI

## Propósito

VIMER es un producto de OpenSAI con identidad funcional propia. La interfaz
debe mostrar siempre la relación mediante el lockup:

> VIMER
> Un proyecto de OpenSAI

El nombre canónico de la organización en la interfaz es **OpenSAI**,
correspondiente a “Open Source Academic Initiative”. “OpenSci” no debe usarse
como variante salvo decisión institucional expresa.

## Activo institucional

El activo versionado de plataforma es:

`assets/vimer/images/opensai-glider.png`

Procede del archivo ya disponible en el entorno VIMER
`media/corporate/logos/logoGliderOpenSAIAzulPlano.png`. Se copió sin
transformaciones y no debe reutilizarse como logo de una organización
participante.

El glider:

- se muestra junto al nombre VIMER en la cabecera;
- conserva su proporción cuadrada;
- no se recolorea, distorsiona ni rota;
- puede usar texto alternativo vacío cuando el lockup textual adyacente ya
  comunica VIMER/OpenSAI.

## Paleta

| Token | Valor | Uso |
|---|---:|---|
| OpenSAI blue | `#2689e2` | Acentos y activo institucional; no usar para texto pequeño sobre blanco |
| Brand | `#0b5c98` | Botones, enlaces y controles con contraste suficiente |
| Brand ink | `#092d4d` | Cabecera, títulos y fondos oscuros |
| Brand pale | `#eaf4fc` | Superficies informativas |
| Ink | `#17212b` | Texto principal |
| Muted | `#4f5e6b` | Texto auxiliar |
| Border | `#71808c` | Límites de campos y componentes |
| Focus | `#ffbf47` | Indicador de foco visible |
| Danger | `#9f2323` | Acciones destructivas y errores |
| Success | `#206a3b` | Confirmaciones |
| Supply | `#1f7a4d` | Identidad del rol "organización proponente" (armoniza con el badge `supply_side` ya existente) |
| Supply ink | `#123f28` | Texto sobre `Supply pale` |
| Supply pale | `#eaf7ef` | Superficies del rol proponente |
| Accent industrial | `#c76e0f` | Acento cálido, complementario de `Brand` en la rueda de color; identidad del rol "equipo de evaluación" y detalle de las bandas fotográficas |
| Accent industrial ink | `#7a4308` | Texto sobre `Accent industrial pale` |
| Accent industrial pale | `#fbf0e2` | Superficies del rol de evaluación |
| Paper | `#f7f4ee` | Fondo cálido neutro para paneles de sección alternos |

No se comunica estado solo mediante color. Todo estado debe incluir texto o un
nombre accesible.

## Tipografía y jerarquía

La interfaz utiliza la pila de fuentes del sistema para evitar dependencias
externas y mejorar rendimiento. Los títulos usan peso alto, interlineado corto
y `Brand ink`; el cuerpo usa `Ink` y un interlineado mínimo de 1.6.

Excepción documentada: los títulos de la página de inicio (`landing.html`) usan
adicionalmente **Space Grotesk**, alojado localmente en
`assets/vimer/fonts/` (sin petición a terceros, sin costo de rendimiento
adicional frente a una fuente del sistema). Es la única excepción a la pila
de fuentes del sistema, limitada a los títulos de la portada; el resto de la
interfaz sigue usando la pila de fuentes del sistema sin cambios.

Debe existir un único `h1` descriptivo por página. Los niveles posteriores no
se eligen por tamaño visual sino por estructura del contenido.

## Componentes y accesibilidad

- Todos los controles tienen etiqueta visible.
- El foco usa el token `Focus` y nunca se elimina.
- Texto normal cumple contraste 4.5:1 y texto grande 3:1.
- Bordes o estados de controles necesarios para comprender la interfaz cumplen
  3:1 frente a superficies adyacentes.
- La cabecera incluye enlace para saltar al contenido y el contenido vive en
  un landmark `main`.
- Las acciones irreversibles explican consecuencias y solicitan confirmación
  explícita.
- La interfaz debe funcionar con teclado, zoom de 200 %/400 % y reflow de
  320 CSS px.

## Lenguaje

Términos canónicos:

- organización **convocante**;
- organización **proponente**;
- **desafío**;
- **propuesta**;
- **adjudicatario**.

No se publica lenguaje interno como “MVP”, “usuarios de prueba” o “validación
manual” en pantallas destinadas a participantes.

## Control de cambios

Cualquier reemplazo del logo, paleta o lockup requiere:

1. activo autorizado y versionado;
2. actualización de este documento;
3. comprobación de contraste;
4. regresión visual y de accesibilidad;
5. aprobación de la persona responsable de la identidad OpenSAI.

### Historial

- **2026-09-11** — se añaden los tokens `Supply`/`Supply ink`/`Supply pale`,
  `Accent industrial`/`Accent industrial ink`/`Accent industrial pale` y
  `Paper`, y se documenta la excepción tipográfica de `Space Grotesk` en los
  títulos de portada (alojada localmente). Cambio aprobado por el
  responsable del proyecto como parte del rediseño visual de VIMER; ningún
  token, logo o lockup existente se modifica o retira.

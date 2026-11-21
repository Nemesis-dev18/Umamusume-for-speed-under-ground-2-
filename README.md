# <div align="center">🏁 UMA // UNDERGROUND 2 🏁</div>

<div align="center">

**Nine Umamusume. One underground garage. One wildly ambitious NFSU2 conversion.**

*No es un selector cosmético: es una reconstrucción técnica experimental de personajes, animación, materiales, audio, geometría y runtime dentro de una copia aislada de Need for Speed Underground 2.*

---

![Estado](https://img.shields.io/badge/ESTADO-EXPERIMENTAL-orange)
![Personajes](https://img.shields.io/badge/ROSTER-9-yellow)
![Plataforma](https://img.shields.io/badge/NFSU2-PC-blue)
![Runtime](https://img.shields.io/badge/DIRECT3D-9-red)
![Compatibilidad](https://img.shields.io/badge/Proton-Wine-7653C9)
![Instalación](https://img.shields.io/badge/Copia-aislada-success)

</div>

> [!WARNING]
> **PROTOCOLO DE USO:** este proyecto es una investigación activa. No representa una versión comercial ni final. Usa siempre una copia separada del juego y conserva los respaldos incluidos en `modding/backups/`.

---

## ⚡ El proyecto en una mirada

`Uma // Underground 2` reemplaza una flota seleccionada de coches por personajes de Uma Musume dentro de Need for Speed Underground 2:

- **9 modelos del roster activos o preparados**
- **Animación idle y carrera** con clips retargeteados
- **Skinning, atlas de texturas y movimiento secundario**
- **Módulo Direct3D 9 en memoria** sin alterar instrucciones de `SPEED2.EXE`
- **Interfaz y rótulos en español**
- **Sombras, efectos, chispas y filtros de neumáticos**
- **Respaldos byte a byte y recibos SHA-256 por paquete**
- **Staging separado** para evitar mezclar candidatos con archivos activos
- **Sin hooks de red ni interacción con anticheat**

```text
 ┌─────────────────── FLUJO DEL MOD ───────────────────┐
 │                                                       │
 │  Steam local ──▶ extracción ──▶ retarget ──▶ UMAB     │
 │       │                                      │        │
 │       └──── materiales / UV / atlas ◀────────┘        │
 │                                                       │
 │  Blender / C / D3D9 ──▶ staging ──▶ respaldo ──▶ NFS │
 │                                                       │
 └───────────────────────────────────────────────────────┘
```

---

## 👑 Roster integrado

| Slot del juego | Personaje | Estado destacado |
|:--|:--|:--|
| Toyota Corolla | **Kitasan Black** | Modelo principal, movimiento retargeteado y sistema secundario |
| Nissan 240SX | **Haru Urara** | Idle/carrera independiente y texturas propias |
| Mazda Miata | **Agnes Tachyon** | Casilla integrada y desbloqueo verificable |
| Ford Focus | **Matikanetannhauser / Mambo** | Perfil secundario de ropa y preview visual |
| Peugeot 206 | **T.M. Opera O** | Modelo, atlas y animación propios |
| Peugeot 106 | **Oguri Cap** | Modelo integrado; estabilidad visual en revisión |
| Opel Corsa | **Meisho Doto** | Retrato regional y modelo integrado |
| Nissan 350Z | **Gentildonna** | Modelo PMX autorizado, tamaño corregido y cloth en validación |
| Mitsubishi Lancer Evo VIII | **Satono Diamond** | Noveno slot; ojos verificados, corte visual pendiente |

> [!NOTE]
> Los nombres de casilla representan compatibilidad técnica con la estructura del juego. No son reemplazos oficiales ni se afirma una apariencia final dentro de cada modo.

---

## ✅ Confirmado / ⚠️ Pendiente

### Confirmado por pruebas independientes

- Los nueve modelos pueden cargarse y dibujarse con hosts D3D9 aislados.
- Los clips idle/carrera, posiciones locales, normales y jerarquías pasan verificadores.
- Los uploads exactos pueden asociarse a perfiles sin usar solo el número de vértices.
- Las texturas, materiales, mips, índices y archivos ajenos pasan comparaciones byte a byte.
- Los módulos pasan carga, `Reset`, retiro de hooks y conservación de estado gráfico en hosts aislados.
- Los paquetes incluyen respaldos reproducibles y recibos SHA-256.

### Evidencia confirmada dentro de NFSU2

- El runtime carga los nueve perfiles.
- Los personajes aparecen en selección y carrera.
- Los ojos de Diamond fueron confirmados visibles.
- Las ruedas laterales y el residuo al chocar fueron corregidos en casos concretos.
- Las luces flotantes y matrículas de pruebas anteriores quedaron retiradas.
- La interfaz española está instalada.

### Todavía pendiente de aceptación

- **Ropa / cabello / cola:** naturalidad sin penetración ni tirones.
- **Gentildonna:** carrera profesional, choques, posición y estabilidad prolongada.
- **Diamond:** integridad visual, expresiones, contacto con el escenario y carrera completa.
- **Sombras, FPS y colisiones:** medición prolongada dentro del juego.
- **Chispas y partículas:** sincronía, tamaño y apariencia real.
- **Cámaras y reflejos:** prevenir poses estáticas, orientación incorrecta o duplicados.
- **Estabilidad:** lapsos largos, carga de menús y recuperación tras choques.

> Una llamada DIP exitosa, una captura o un comando que termina con código cero nunca se presenta aquí como prueba de aceptación final.





https://github.com/user-attachments/assets/0d9f5f21-b30e-4fbc-9fcd-c99d2d6803dc





https://github.com/user-attachments/assets/30507dc0-87b0-49f5-8fcb-d70416c05fb8




---

## 🚀 Inicio rápido

### Requisitos

- Una copia **original y legal** de *Need for Speed Underground 2* para PC.
- Linux probado con Steam y Proton Experimental.
- Wine/Direct3D 9 disponible para compilación y pruebas `i686`.
- Una copia aislada para pruebas. **No uses una instalación personal sin respaldos.**

### Abrir la copia de prueba

Desde la raíz del proyecto:

```sh
chmod +x ./Iniciar-prueba.sh
./Iniciar-prueba.sh
```

El lanzador usa el prefijo Proton configurado en [Iniciar-prueba.sh](./Iniciar-prueba.sh). Mantén el juego cerrado hasta preparar o autorizar una prueba.

### Archivo activo del runtime

```text
scripts/UmaRunner.asi
```

Los modelos, clips y atlas se almacenan bajo:

```text
modding/runtime/fleet/
```

---

## 🧰 Herramientas y validación

### Pruebas Python principales

Desde la raíz:

```sh
python -B -m unittest discover -s modding/tests -v
```

### Verificación de movimiento

```sh
python -B modding/runtime/verify_motion.py
python -B modding/scripts/verify_steam_fleet.py
```

### Inspección de recursos

```sh
python -B modding/scripts/inspect_assets.py \
  --inventory \
  --map CARS/COROLLA/GEOMETRY.BIN \
       CARS/COROLLA/TEXTURES.BIN \
       GLOBAL/GLOBALB.BUN \
       GLOBAL/GlobalB.lzc
```

### Hosts Direct3D independientes

Las pruebas gráficas usan dispositivos propios bajo Wine o hosts independientes. No lanzan `SPEED2.EXE` y no sustituyen una sesión real:

```text
modding/runtime/gentildonna-gpu/
modding/runtime/fleet-gpu/
modding/runtime/secondary-gpu/
modding/runtime/gpu-test/
```

Las trazas, capturas, previsualizaciones y recibos permanecen bajo `modding/`.

---

## 🗂️ Arquitectura del proyecto

| Ruta | Propósito |
|:--|:--|
| [CARS/](/home/nemesis/Vídeos/proyecto%20inginversa/NFSU2-Uma-Prueba/CARS/) | Geometría, texturas, colisiones y datos de vehículos |
| [FRONTEND/](/home/nemesis/Vídeos/proyecto%20inginversa/NFSU2-Uma-Prueba/FRONTEND/) | Interfaz, retratos, rótulos y recursos gráficos |
| [GLOBAL/](/home/nemesis/Vídeos/proyecto%20inginversa/NFSU2-Uma-Prueba/GLOBAL/) | Datos globales, materiales y fabricantes |
| [LANGUAGES/](/home/nemesis/Vídeos/proyecto%20inginversa/NFSU2-Uma-Prueba/LANGUAGES/) | Recursos de localización |
| [modding/](/home/nemesis/Vídeos/proyecto%20inginversa/NFSU2-Uma-Prueba/modding/) | Scripts, staging, recibos, respaldos, pruebas y diagnósticos |
| [scripts/](/home/nemesis/Vídeos/proyecto%20inginversa/NFSU2-Uma-Prueba/scripts/) | Runtime y módulos temporales o activos |
| [modding/runtime/fleet/](/home/nemesis/Vídeos/proyecto%20inginversa/NFSU2-Uma-Prueba/modding/runtime/fleet/) | Modelos UMAB, atlas y clips de la flota |
| [CLAUDE.md](/home/nemesis/Vídeos/proyecto%20inginversa/NFSU2-Uma-Prueba/CLAUDE.md) | Bitácora histórica técnica y decisiones |

> Las rutas absolutas están adaptadas al entorno local. Para publicar o compartir, usa rutas relativas y adapta el lanzador a tu instalación.

---

## 🛡️ Seguridad, integridad y rollback

La política operativa excluye:

- Leer o modificar `SPEED2.EXE`.
- Parchar DLL, direcciones protegidas o anticheat.
- Acceder a red o servicios online.
- Lanzar el juego sin una excepción aprobada.
- Mezclar respaldos históricos con el estado instalado actual.

Antes de una instalación real se crean:

1. Verificación SHA-256 de todos los destinos.
2. Copias `.bak` exactas.
3. Un checkpoint Git del estado anterior.
4. Escritura en archivos temporales.
5. Verificación posterior antes del reemplazo.
6. Un recibo con tamaños y hashes finales.

No existe una restauración universal: los cambios tienen alcances distintos. Consulta los recibos dentro de [modding/](/home/nemesis/Vídeos/proyecto%20inginversa/NFSU2-Uma-Prueba/modding/) y verifica el paquete concreto antes de revertir.

---

## 🌍 Traducción al español

La interfaz activa incluye traducciones españolas para los nombres de personaje y recursos de menú existentes.

- [_Parche español.reg](./_Parche%20espa%C3%B1ol.reg): parche regional del registro.
- [modding/fleet-language-plan.json](./modding/fleet-language-plan.json): preparación de nombres.
- [CREDITS/SPANISH.TXT](./CREDITS/SPANISH.TXT): créditos en español.

La traducción de cadenas no garantiza que toda la interfaz, voz, video o tipografía funcione correctamente en otros sistemas.

---

## 🔧 Desarrollo

El proyecto combina varias tuberías independientes:

```text
PMX / GLTF / Unity  ──▶  malla + huesos + pesos
                          │
                          ├──▶ UMAB: geometría y clips
                          ├──▶ UMAS: física secundaria
                          ├──▶ UMAM: materiales
                          └──▶ Atlas / DDS: apariencia

D3D9 captured state ──▶  bridge de cámara / shader
Uploads CPU           ──▶  identidad de malla
Actor state           ──▶  gait / speed / reflection
NFS resource formats  ──▶  shadow / wheel / UI isolation
```

### Reglas de ingeniería

- Los nombres truncados no son identidad; se usan hashes, offsets y bytes reales.
- `SHPI`, `FSH`, `TPK`, `JDLZ`, `HUFF` y DDS tienen validaciones distintas.
- Los vértices reducidos no eliminan piezas reales solo por coincidencia de cantidad.
- Las llamadas DIP exitosas no demuestran que un píxel sea visible.
- Los hosts de Wine no prueban por sí solos FPS, estabilidad ni carga dentro de Proton.
- Toda simulación secundaria usa límites medibles y sidecars separados.
- Un asset visual aprobado no implica compatibilidad con el runtime.

---

## 🎨 Créditos

- **Electronic Arts** — *Need for Speed Underground 2*.
- **Cygames** — personajes y universos de *Uma Musume Pretty Derby*.
- **Yossi** — fuente PMX de Gentildonna utilizada con autorización local confirmada.
- **MMD / Blender tooling** — conversión y revisión visual fuera del juego.
- **UmaExporter / UmaViewer** — lectores públicos utilizados localmente para depurar formatos.
- **Colaboradores y herramientas locales** — scripts, registros, hosts D3D9 y verificación documentados dentro de `modding/`.

Los nombres, marcas y activos pertenecen a sus respectivos titulares.

---

## ⚖️ Aviso legal

Este proyecto es una modificación experimental hecha por fans. No está afiliado, patrocinado ni respaldado por Electronic Arts, Cygames, Unity, Blender Foundation o los autores de los modelos utilizados.

Este repositorio no distribuye una copia comercial del juego ni pretende sustituirla. Necesitas tus propios archivos originales y legales para ejecutar una copia compatible.

No se garantiza compatibilidad con mods, guardados, anticheat, modos online, Steam o actualizaciones futuras.

---

## 📜 Licencia

Las herramientas originales deben llevar una licencia antes de redistribuirse públicamente. Los contenidos de terceros —incluidos modelos, texturas, fuentes, audio y archivos del juego— permanecen sujetos a sus permisos respectivos.

> **Uso personal y local.** No redistribuyas activos propietarios sin autorización.

---

<div align="center">

## 🏁 Estado del motor

**Investigación activa · Runtime montado · Gameplay en evolución**

*Vuelve despacio, frena limpio y conserva siempre el respaldo.*

</div>

# Umamusume para Need for Speed Underground 2

> ⚠️ **Estado: prototipo incompleto.** Este mod es experimental y no está terminado. Leé la sección [Estado actual](#estado-actual-y-problemas-conocidos) antes de instalarlo.

Modificación no oficial de *Need for Speed Underground 2* (PC) con temática de *Uma Musume Pretty Derby*. Esta copia local usa un módulo de dibujo y animación con ocho personajes en casillas distintas. También conserva los archivos de traducción y la variante invernal presentes en el proyecto.

## Tabla de contenidos

- [Umamusume para Need for Speed Underground 2](#umamusume-para-need-for-speed-underground-2)
  - [Tabla de contenidos](#tabla-de-contenidos)
  - [Estado actual y problemas conocidos](#estado-actual-y-problemas-conocidos)
  - [Requisitos](#requisitos)
  - [Instalación](#instalación)
  - [Cómo volver al juego original](#cómo-volver-al-juego-original)
  - [Estructura del repositorio](#estructura-del-repositorio)
  - [Traducción al español](#traducción-al-español)
  - [Créditos](#créditos)
  - [Aviso legal](#aviso-legal)
  - [Licencia](#licencia)

## Estado actual y problemas conocidos

Configuración del paquete local:

| Casilla original | Personaje |
|---|---|
| Toyota Corolla | Kitasan Black |
| Nissan 240SX | Haru Urara |
| Mazda Miata | Agnes Tachyon |
| Ford Focus | Matikane Tannhauser (Mambo) |
| Peugeot 206 | T.M. Opera O |
| Peugeot 106 | Oguri Cap |
| Opel Corsa | Meisho Doto |
| Nissan 350Z | Gentildonna |

El paquete de Gentildonna conserva su geometría y texturas a resolución original, adapta el ciclo de carrera y añade un rótulo y retrato de selección. El módulo incluye movimiento secundario de ropa, chispas en las suelas y un ajuste de orientación basado en el escenario. Los cambios se registran en `CLAUDE.md` y `modding/gentildonna-install-plan.json`.

Las pruebas independientes cubren carga y dibujo de los ocho personajes, materiales inválidos, animaciones, sombras, cambios de personaje, recuperación del dispositivo gráfico y reversión de archivos ante fallo. **La revisión dentro de NFS sigue pendiente para esta versión**: caídas tras choques, ropa atravesando el cuerpo, cambios de cámara y FPS deben comprobarse en carrera.

## Requisitos

- Una copia **original y legal** de *Need for Speed Underground 2* para PC.
- Entorno local probado: Linux con Proton Experimental y Direct3D 9. La compatibilidad con Windows no está verificada aquí.
- Para reconstruir: las herramientas locales y fuentes documentadas en `CLAUDE.md`; los scripts usan rutas de esta máquina.

## Instalación

Esta carpeta es la copia de trabajo aislada. Los paquetes se preparan en `modding/staged-runtime/` y se instalan con respaldo; no copies todo sobre tu instalación original.

Para iniciar la copia local desde su carpeta:

```sh
./Iniciar-prueba.sh
```

El lanzador usa el prefijo Proton aislado ya configurado. `scripts/UmaRunner.asi` contiene el módulo del mod y `modding/runtime/fleet/` sus modelos y texturas.

El paquete de Gentildonna se prepara e instala con `modding/scripts/install_gentildonna_package.py`; requiere juego cerrado, candidatos verificados y respaldo en un checkpoint Git. Su recibo enumera cada archivo y su hash.

## Cómo volver al juego original

La instalación original permanece en otra carpeta. Para jugar sin el mod, usa esa copia intacta. Los paquetes de esta copia tienen respaldos en `modding/backups/` y recibos con los archivos modificados; restaurar solo los dos archivos del Corolla ya no revierte el mod completo.

## Estructura del repositorio

| Carpeta / archivo | Contenido |
|---|---|
| `CARS/` | Contenedores de las ocho casillas convertidas y autos restantes. |
| `TRACKS/` | Circuitos. |
| `SOUND/`, `MOVIES/`, `NIS/`, `SUBTITLES/` | Audio, videos, escenas y subtítulos. |
| `FRONTEND/`, `GLOBAL/`, `SDATA/` | Interfaz y datos generales del juego. |
| `LANGUAGES/` | Archivos de idioma. |
| `Support/`, `modding/`, `scripts/` | Herramientas y scripts de apoyo. [TODO: describir]. |
| `Need for Speed Underground 2 - Winter Mod/` | Variante invernal. [TODO: describir]. |
| `memcard/` | Archivos de partidas guardadas. [TODO: confirmar]. |
| `FOOBAR/` | [TODO: describir]. |
| `CREDITS/` | Créditos del juego o del mod. [TODO: describir]. |

## Traducción al español

El archivo `_Parche español.reg` aplica la traducción al español. [TODO: explicar cómo se aplica, qué cambia en el registro de Windows y cómo deshacerlo].

## Créditos

- [TODO: autor del mod y colaboradores].
- Electronic Arts, por *Need for Speed Underground 2*.
- Cygames, por *Uma Musume Pretty Derby*.
- Yossi, fuente PMX de Gentildonna, utilizada localmente según el permiso confirmado por el usuario.
- Herramientas y versiones documentadas en `CLAUDE.md` y los recibos de preparación.

## Aviso legal

Este es un proyecto de fans, sin fines comerciales. No está afiliado ni respaldado por Electronic Arts, Cygames ni por los titulares de *Uma Musume Pretty Derby*. Este repositorio no incluye una copia legal del juego: necesitás tu propia copia original para usarlo.

## Licencia

[TODO: elegir una licencia, o indicar que el contenido es solo para uso personal].
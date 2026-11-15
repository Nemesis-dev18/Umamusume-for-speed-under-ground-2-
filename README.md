# Umamusume para Need for Speed Underground 2

> ⚠️ **Estado: prototipo incompleto.** Este mod es experimental y no está terminado. Leé la sección [Estado actual](#estado-actual-y-problemas-conocidos) antes de instalarlo.

Modificación no oficial de *Need for Speed Underground 2* (PC) con temática de *Uma Musume Pretty Derby*. Por ahora el mod modifica el Toyota Corolla (geometría y texturas) y también incluye archivos de traducción al español y una variante invernal.

## Tabla de contenidos

- [Estado actual](#estado-actual-y-problemas-conocidos)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Cómo volver al juego original](#cómo-volver-al-juego-original)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Traducción al español](#traducción-al-español)
- [Créditos](#créditos)
- [Aviso legal](#aviso-legal)
- [Licencia](#licencia)

## Estado actual y problemas conocidos

Este repositorio contiene el **primer prototipo** que se mostró en pantalla. Los cambios posteriores no están instalados porque fallaron las pruebas.

Problemas conocidos:

- El personaje aparece oscuro.
- Quedan restos de la rueda.
- Hay una sombra residual del carro.
- No hay animación de carrera.

## Requisitos

- Una copia **original y legal** de *Need for Speed Underground 2* para PC.
- Windows [TODO: confirmar versiones compatibles].
- [TODO: versión exacta del juego que se probó, por ejemplo idioma y parche].

## Instalación

1. Hacé una copia de seguridad de tu carpeta original de *Need for Speed Underground 2*. No trabajes directamente sobre la carpeta original.
2. Copiá los archivos de este repositorio en la carpeta del juego (o en una carpeta de prueba, como `NFSU2-Uma-Prueba`).
3. [TODO: explicar cómo iniciar el juego: qué ejecutar, si `SPEED2.EXE`, `Iniciar-prueba.sh` o `SafeMode.bat`, y para qué sirve cada uno].
4. [TODO: explicar qué hace `dinput8.dll` y si hace falta un cargador de mods].

## Cómo volver al juego original

Para revertir los cambios del prototipo, copiá estos dos archivos desde la carpeta original del juego:

- `CARS/COROLLA/GEOMETRY.BIN`
- `CARS/COROLLA/TEXTURES.BIN`

## Estructura del repositorio

| Carpeta / archivo | Contenido |
|---|---|
| `CARS/` | Modelos y texturas de autos (incluye el Corolla modificado). |
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
- [TODO: créditos de herramientas, traducciones y texturas].

## Aviso legal

Este es un proyecto de fans, sin fines comerciales. No está afiliado ni respaldado por Electronic Arts, Cygames ni por los titulares de *Uma Musume Pretty Derby*. Este repositorio no incluye una copia legal del juego: necesitás tu propia copia original para usarlo.

## Licencia

[TODO: elegir una licencia, o indicar que el contenido es solo para uso personal].

# Ciclo de carrera local: Steam Uma → Kitasan en NFSU2

Esta copia usa el modelo PMX existente y el clip local `anm_rac_type03_run02_base` adaptado a sus 282 huesos. No modifica la instalación de Steam ni el NFS original. El módulo privado reproduce el movimiento; no se presenta UMAB como formato nativo EAGL.

## Entradas y lectores fijados

- Instalación fuente: `/home/nemesis/.local/share/Steam/steamapps/common/UmamusumePrettyDerby/UmamusumePrettyDerby_Data/Persistent`.
- Modelo existente: `modding/character-source/{mesh.bin,skin.bin,skeleton.json}` y atlas propio ya instalado.
- Lector: [UmaExporter](https://github.com/mumu-lhl/UmaExporter), commit `dca091dad2947d13f99a0510bcccdec82941df0c`; únicamente helper de descifrado, sin ejecutar su aplicación.
- UnityPy y SQLite3MC privados: `modding/uma-steam/python-deps`; versiones completas en `modding/uma-steam/requirements-lock.txt`.
- Procedencia y hashes de los tres paquetes: `modding/uma-steam/bundles/*.source.json`.

Los scripts siguientes se ejecutan desde `/home/nemesis/Vídeos/proyecto inginversa/NFSU2-Uma-Prueba`. La extracción solo escribe copias bajo `modding/uma-steam`. Los paquetes source no se distribuyen como parte de un mod público.

## Reproducir sin alterar lo instalado

```sh
python modding/scripts/extract_uma_steam.py
python modding/scripts/retarget_uma_motion.py --output modding/animation-steam-rebuild
```

La carpeta de salida debe ser nueva: el exportador rechaza sobrescribirla. Para empaquetar la reconstrucción sin tocar el juego:

```sh
python - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, 'modding/scripts')
from pack_motion import pack
root = Path.cwd()
output = root / 'modding/staged-runtime/kitasan-steam-rebuild.umab'
output.write_bytes(pack(root / 'modding/animation-steam-rebuild'))
PY
python modding/scripts/verify_motion.py --asset modding/staged-runtime/kitasan-steam-rebuild.umab --clips modding/animation-steam-rebuild
```

La referencia instalada tiene SHA-256 `c1701a3227ce720bf2f4166b96f96219e96b4f307251a579d9c2f0059c8e0581`. Las matrices y el paquete UMAB se pueden comparar exactamente; el ZIP de NPZ puede contener fechas distintas.

Con el juego cerrado, `python modding/scripts/verify_runtime.py` compila el módulo candidato y ejecuta hosts independientes D3D9. Escribe resultados y el candidato bajo `modding/runtime`; no instala en `scripts/`. Las pruebas Python se ejecutan con `python -m unittest discover -s modding/tests -q` y requieren NumPy disponible.

## Instalación actual y vuelta atrás

El recibo vigente se encuentra en `modding/runner-installed.json`, campo `current_receipt`. Los cambios de colisión y los doce archivos de accesorios están en `modding/character-package-installed.json`; las mejoras posteriores del módulo/audio tienen su propio recibo. `steam-motion-installed.json` conserva el paso histórico que integró el clip, y no representa por sí solo todo lo instalado actualmente.

Para volver atrás, cerrar el juego y restaurar primero los archivos del recibo más reciente desde sus respaldos; después, si se quiere retirar también colisión/accesorios, restaurar los catorce respaldos del paquete de personaje. No basta restaurar tres archivos del recibo histórico de Steam. Conservar los logs antes de otra prueba. No restaurar el JSON del ciclo antiguo si se mantiene el UMAB nuevo.

Los generadores de colisión y accesorios usan sus respaldos como baseline cuando existen; pueden volver a preparar los mismos candidatos sin transformar dos veces el estado instalado. Se comprobó reproducción exacta de planes y SHA tras instalar.

## Pasos originales

`extract_uma_footsteps.py` lee la copia privada de `snd_sfx_race_000.acb` y resuelve cues de pista por las tablas CRI, no por el orden supuesto del archivo. Usa clHCA fijado y comprobado por SHA para decodificar, valida la clave/bloques y contrasta duración/canales/frecuencia con WaveformTable. Convierte a PCM16 mono22050Hz sin síntesis ni cambios de pitch o ganancia. Exporta diez variantes por pie y un manifiesto con procedencia/hashes. `make_hoof_audio.py` se conserva como experimento anterior, pero sus cascos sintéticos ya no corresponden a esta mejora.

El módulo utiliza dos salidas WaveOut para solapar las colas izquierda/derecha. La ruta silenciosa exclusiva del Corolla modifica únicamente datos de audio en memoria cuando encuentra una coincidencia única de las tablas completas; archivos SOUND y ejecutable sin modificar. Una clave incorrecta, muestras corruptas o perfiles distintos se rechazan. Fallos de reproducción restauran los parámetros originales si aún coinciden con los propios.

## Límites pendientes

El reposo y la dinámica secundaria de pelo/cola siguen siendo propios; no hay simulación completa de tela de Uma. Las catorce rutas del clip ausentes del prefab se excluyen explícitamente. Todos los Corolla reciben Kitasan y comparten el estado de movimiento; no se identifica exclusivamente al jugador. Las carrocerías principales de otros tipos se conservan; los accesorios compartidos se han retirado globalmente por instrucción del usuario. Las ruedas/accesorios y la calidad visual final requieren prueba dentro de NFS; tests gráficos independientes no los demuestran.

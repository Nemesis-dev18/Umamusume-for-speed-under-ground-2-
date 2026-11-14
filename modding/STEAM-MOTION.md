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

`modding/steam-motion-installed.json` registra el checkpoint, rutas, hashes y respaldos de los tres archivos instalados. La ampliación de cajas está descrita campo por campo en `modding/steam-motion-bounds-plan.json`: conserva tamaño, chunks y alineaciones. No cambiar cajas ni instalar otro módulo con el juego abierto.

Para volver al punto anterior, cerrar el juego y restaurar los tres respaldos indicados en ese recibo. Restaurar también `modding/runtime/kitasan.before-steam.json` como `kitasan.json` para que las referencias del verificador vuelvan al ciclo anterior. Conservar los registros de gameplay antes de otra prueba. `CLAUDE.md` contiene las pruebas reales y los cambios anteriores.

## Límites pendientes

El reposo y la dinámica secundaria de pelo/cola siguen siendo propios; no hay simulación completa de tela de Uma. Las catorce rutas del clip ausentes del prefab se excluyen explícitamente. Todos los Corolla reciben Kitasan y comparten el estado de movimiento; no se identifica exclusivamente al jugador. Otros tipos de coche conservan sus recursos. Las ruedas/accesorios y la calidad visual final requieren prueba dentro de NFS; tests gráficos independientes no los demuestran.

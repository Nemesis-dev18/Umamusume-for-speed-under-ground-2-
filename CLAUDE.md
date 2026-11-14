# NFSU2 — investigación local y estado comprobado

## Alcance y autorización

Raíz de trabajo: esta carpeta `NFSU2-Uma-Prueba`. El usuario confirmó Underground 2 y reutilizar Kitasan existente. El texto genérico del objetivo menciona Underground 2003 y un personaje original; esas partes no describen el artefacto elegido. No afirmar que Kitasan sea un diseño original nuestro. Las fases 1 y 2 fueron aprobadas explícitamente. La instalación original queda fuera de las escrituras.

No leer ni modificar ejecutables, DLL, ASI, red o anticheat. No lanzar el juego durante este análisis. Las modificaciones futuras de recursos requieren un plan concreto de archivos, rangos, tamaños, respaldos `.bak` y checkpoint Git antes de aplicarlas. Esta entrega solo crea herramientas, documentación y resultados derivados en `modding/`.

## Inventario: observaciones

`modding/inventory.json`: 716 archivos de datos con ruta, tamaño, SHA-256 y 16 bytes iniciales. Categorías por nombre son candidatas, no prueba de función. CARS: 231; GLOBAL: 31; NIS: 77; SOUND: 361; FRONTEND: 16. No existe CARS/DRIVER/GEOMETRY.BIN. Audio: inventariado, sin extracción ni interpretación del códec.

`modding/containers.json`: mapa de CARS/COROLLA/GEOMETRY.BIN y TEXTURES.BIN, GLOBAL/GLOBALB.BUN y GlobalB.lzc. Los offsets del último se refieren al búfer descomprimido, no al archivo comprimido.

`modding/animation-containers.json`: 71 archivos binarios candidatos de NIS y PARTS_ANIMATIONS; todos admiten recorrido estructural de chunks. No se ha identificado una jerarquía de huesos ni curvas de animación. Un chunk o nombre de archivo no demuestra esas estructuras.

## Estructuras implementadas

Todos los enteros multibyte descritos abajo son little-endian, excepto magic ASCII.

- bChunk: `id:u32` en +0, `payload_size:u32` en +4, datos desde +8. Siguiente hermano: offset+8+size. Bit alto del ID indica contenedor. Validar cada hijo contra su padre; máximo 32 niveles. ID cero describe padding y se conserva en el mapa.
- Geometría: SolidList `0x80134000`; solid `0x80134010` (no `0x00134010`); cabecera `0x00134011`; mesh header `0x00134900`; vértices `0x00134B01`; rangos de material `0x00134B02`; índices `0x00134B03`; markers `0x0013401A`.
- Mesh header: después del filler de palabras `0x11111111`, triángulos u32 en +36, vértices u32 en +52.
- Vértice estándar: 36 bytes, posición float3 en +0, normal float3 en +12, color BGRA en +24 y UV float2 en +28. Variante de 24 bytes: posición +0, color +12, UV +16; sin normal almacenada. Solo aceptar si el tamaño y filler encajan.
- Índices: u16; tres por triángulo; leer hacia delante después de filler por palabras. Validar contra número de vértices.
- Matriz local del solid: 16 floats desde +64 de su cabecera; no aplicarla implícitamente a los OBJ, conservarla en manifiesto.
- Marker: registro de 80 bytes después de filler por palabras; hash u32 en +0 y matriz float4x4 en +16. Son anclajes, no huesos.
- TPK observado: raíz del Corolla `0xB3300000`; tabla `0x33310003`, registros de 24 bytes: hash, offset absoluto del blob, longitud comprimida, longitud descomprimida, distancia de cabecera desde el final y palabra desconocida. Nunca interpretar estos datos como SHPI sin evidencia.
- OldTextureInfo en pool: `P=out_size-header_from_end+0x88`; hash en P+0 debe coincidir; nombre de 24 bytes antes de P; ancho u16 P+32, alto u16 P+34, formato u8 P+38. BGRA `0x20`, DXT1 `0x22`, DXT3 `0x24`, DXT5 `0x26`, paleta de índices de 8 bits `0x08/0x80/0x81`. Estos códigos no son los de FSH genérico.
- Paleta: diferencia entre u32 P+16 y P+12; tamaño u32 P+24 debe ser 1024. Verificar que esté después del mip superior y dentro del pool.
- JDLZ: bytes `4A 44 4C 5A`; entero LE `0x5A4C444A`. Cabecera de 16 bytes: versión/flags `02 10 00 00` en +4; longitud de salida +8; longitud comprimida incluyendo cabecera +12. Dos flujos de flags LSB y referencias solapables. Tope 256 MiB; rechazar referencia previa al inicio, salida excedida y truncamiento.

No extrapolar reglas de alineación de NFSU 2003 a todos los bloques de NFSU2. Los mapas registran módulo 16 del inicio y módulo 128 del payload. Para reempaquetar deberán verificarse las alineaciones de cada tipo, tamaños de padres, índices y referencias absolutas (incluido el puntero a colisiones), sin normalizar padding desconocido.

## Extracción comprobada

`python -B modding/scripts/extract_assets.py` extrae cuatro KIT00_BODY del Corolla a OBJ de coordenadas locales y JSON de transformaciones/markers; 14.512 vértices y 16.557 triángulos por LOD. El manifiesto no atribuye huesos ni curvas a estos datos.

56 descriptores de texturas; 43 decodificados a PNG, DDS del mip superior cuando aplica. 13 blobs HUFF pendientes: no se exportan como si fueran JDLZ. No se exporta todavía toda la cadena mip. Falta conexión OBJ/MTL con materiales. No se ha reempaquetado nada.

La descompresión en memoria de GLOBAL/GlobalB.lzc coincide byte a byte con GLOBAL/GLOBALB.BUN: vector real de validación para JDLZ. CarTypeInfo no está todavía interpretado por los nuevos scripts.

## Pruebas y reproducción

- `python -B -m unittest discover -s modding/tests -v`: JDLZ literal/copia solapada, truncado/tamaño excesivo/referencia inválida, límites de chunks, offsets anidados, confinamiento de entradas, cabecera DDS, geometría real y pareja GlobalB real.
- `python -B modding/scripts/inspect_assets.py --inventory --map CARS/COROLLA/GEOMETRY.BIN CARS/COROLLA/TEXTURES.BIN GLOBAL/GLOBALB.BUN GLOBAL/GlobalB.lzc`
- Los reportes y destinos existentes se rechazan para evitar sobrescrituras. Verificación de reproducibilidad pendiente en un destino aislado; no borrar resultados manualmente para simularla.
- Hashes fuente antes/después de extracción coinciden. La comparación completa con inventario se realiza al cierre de esta revisión.

## Estado del juego y próximos pasos

No se ejecutó el juego en esta revisión. La última evidencia del usuario sigue siendo cuerpo invisible en carrera, aunque visible en selección, con elementos del automóvil restantes. Las pruebas de parsers no prueban carga en el motor.

Pendiente: HUFF, mipmaps completos, asociación de materiales, búsqueda estructural del rig/curvas, CarTypeInfo, reempaquetado reversible y pruebas de carrera. No editar física para ocultar ruedas. No introducir hooks ni direcciones de otra versión. Blender MCP y Git MCP no están expuestos; filesystem MCP permite otra raíz. No se cambió configuración ni se instalaron herramientas. Git CLI está disponible.

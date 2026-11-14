# NFSU2 — investigación local y estado comprobado

## Alcance y autorización

Raíz de trabajo: esta carpeta `NFSU2-Uma-Prueba`. El usuario confirmó Underground 2 y reutilizar Kitasan existente. El texto genérico del objetivo menciona Underground 2003 y un personaje original; esas partes no describen el artefacto elegido. No afirmar que Kitasan sea un diseño original nuestro. Las fases 1 y 2 fueron aprobadas explícitamente. La instalación original queda fuera de las escrituras.

No leer ni modificar ejecutables, DLL, ASI, red o anticheat. No lanzar el juego durante este análisis. Las modificaciones futuras de recursos requieren un plan concreto de archivos, rangos, tamaños, respaldos `.bak` y checkpoint Git antes de aplicarlas. Esta entrega solo crea herramientas, documentación y resultados derivados en `modding/`.

## Inventario: observaciones

`modding/inventory.json`: 716 archivos de datos con ruta, tamaño, SHA-256 y 16 bytes iniciales. Categorías por nombre son candidatas, no prueba de función. CARS: 231; GLOBAL: 31; NIS: 77; SOUND: 361; FRONTEND: 16. No existe CARS/DRIVER/GEOMETRY.BIN. Audio: inventariado, sin extracción ni interpretación del códec.

`modding/containers.json`: mapa de CARS/COROLLA/GEOMETRY.BIN y TEXTURES.BIN, GLOBAL/GLOBALB.BUN y GlobalB.lzc. Los offsets del último se refieren al búfer descomprimido, no al archivo comprimido.

`modding/animation-containers.json`: 71 archivos binarios candidatos de NIS y PARTS_ANIMATIONS; todos admiten recorrido estructural de chunks. La primera pasada solo clasificó chunks. La revisión posterior de ELF de datos recuperó esqueletos y canales; ver sección de animación nativa. Un chunk o nombre de archivo por sí solo no demuestra esas estructuras.

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

56 descriptores de texturas; 43 decodificados a PNG, DDS del mip superior cuando aplica. El lector HUFF implementa exclusivamente el tipo observado 0x30fb, con tabla canónica, escape de repetición/literal y validación de longitudes interna/externa. Los 13 blobs se decodifican y sus hashes embebidos coinciden. La extracción final COROLLA-mips-materials incluye 56 texturas, 225 niveles mip originales, DDS con cadena completa cuando son DXT y PNG por nivel. OBJ/MTL conecta el material de cada LOD con la textura 1c9637a6. No se ha reempaquetado nada.

La descompresión en memoria de GLOBAL/GlobalB.lzc coincide byte a byte con GLOBAL/GLOBALB.BUN: vector real de validación para JDLZ. `modding/cartypes.json` identifica 46 registros candidatos CarTypeInfo de 0x890 bytes, con ruta GEOMETRY en +0x40, nombres repetidos en +0/+0x20, cuatro ruedas en +0x120 con stride 0x30 y masa almacenada float en +0x220. Se extraen posiciones y radios como interpretación de referencia; no se editan unidades ni física.

## Pruebas y reproducción

- `python -B -m unittest discover -s modding/tests -v`: JDLZ literal/copia solapada, truncado/tamaño excesivo/referencia inválida, límites de chunks, offsets anidados, confinamiento de entradas, cabecera DDS, geometría real y pareja GlobalB real.
- `python -B modding/scripts/inspect_assets.py --inventory --map CARS/COROLLA/GEOMETRY.BIN CARS/COROLLA/TEXTURES.BIN GLOBAL/GLOBALB.BUN GLOBAL/GlobalB.lzc`
- Los reportes y destinos existentes se rechazan para evitar sobrescrituras. La opción --output permite otro destino nuevo dentro de modding/. Dos extracciones finales separadas producen 340 archivos idénticos por SHA-256, incluidos manifiestos. No borrar resultados manualmente para simular repetibilidad.
- Hashes fuente antes/después de extracción coinciden. Los 716 hashes del inventario siguen iguales tras las extracciones. `modding/verification.json` registra 340 archivos reproducibles, 56 texturas y 225 mipmaps comprobados con Pillow.

## Estado del juego y próximos pasos

No se ejecutó el juego en esta revisión. La última evidencia del usuario sigue siendo cuerpo invisible en carrera, aunque visible en selección, con elementos del automóvil restantes. Las pruebas de parsers no prueban carga en el motor.

Pendiente: curvas comprimidas y vínculo de skinning, verificar unidades de CarTypeInfo en el motor, reempaquetado reversible y pruebas de carrera. No editar física para ocultar ruedas. No introducir hooks ni direcciones de otra versión. Blender MCP y Git MCP no están expuestos; filesystem MCP permite otra raíz. No se cambió configuración ni se instalaron herramientas. Git CLI está disponible.

## Cierre de esta revisión

13 pruebas automatizadas pasan, incluyendo HUFF sintético y sus 13 blobs reales, cadena mip exacta/rechazo de cadenas parciales, cabecera DDS con número de niveles y los 46 registros CarTypeInfo. Los 225 PNG de mipmap tienen las dimensiones declaradas y las imágenes superiores coinciden con la extracción anterior. El caso HUFF no tiene aún un vector independiente completo de salida conocido; tamaño/hash interno y decodificación gráfica no sustituyen esa comparación.

El primer checkpoint Git es ae7016b. Solo se versionan herramientas, manifiestos y documentación; los datos del juego y resultados grandes están excluidos. Ningún binario del juego fue sobrescrito, así que todavía no hay un respaldo .bak de una modificación nueva ni un checkpoint de bytes originales para reempaquetado. No confundir el commit de herramientas con un respaldo del juego.

## Animación nativa: segunda revisión

`extract_animation_banks.py` recorre los 71 candidatos registrados en animation-containers.json. Resultado completo en all-native-animation-skeletons.json: 784 objetos de datos (701 AnimationBank y 83 esqueletos), 2.023 canales, 576 curvas float4 decodificadas y 2.355 huesos con nombre/índice/parentesco. No se ejecuta ni se carga ningún ELF. Se rechazan secciones ejecutables y program headers. No se inspeccionó SPEED2.EXE.

- Chunk `0x00E34010`: objeto ELF32 little-endian, ET_REL=1, máquina MIPS=8. Cabecera de 52 bytes, sección de 40 bytes, símbolos de 16 bytes y relocaciones de 8 bytes. Solo se admiten referencias locales R_MIPS_32 tipo 2. Se conservan rangos absolutos en el archivo y relativos en .data.
- Símbolo `__AnimationBank:::bank`: cabecera de 28 bytes, número de canales u32 en +4; tablas de punteros a descriptores/nombres en +16/+20. Descriptor de 16 bytes: puntero a formato en +4, campos u16 crudos tipo/muestras en +8/+10, puntero a datos en +12. Los punteros deben estar en la tabla de relocación.
- Variante de valores admitida: firma u32 0x14000000, modo u32 2, componentes u32 4, número de muestras u32 en +12; valores float4 desde +32. El tamaño debe coincidir exactamente con el siguiente destino de relocación. Las curvas terminadas en _q tienen norma próxima a uno. En Corolla son 21 curvas y 611 muestras. No asumir frecuencia temporal hasta validarla.
- Chunk `0x00E34009`: objeto ELF de datos con símbolos `__Skeleton:::...` y `__Bone:::...`. Cada símbolo de hueso apunta a un registro con índice u32. La cabecera Skeleton contiene hash en +0 y número de huesos u32 en +8; registros desde +16 con stride 112: escala float3 +0, padre i32 +12, rotación float4 +16, traslación float3 +32, índice u32 +44 y matriz float16 +48.
- Se validaron índices únicos, todos los nombres, padres en rango, ausencia de ciclos y datos finitos. Además, las transformaciones locales reproducen las matrices nativas usando cuaternión xyzw y matriz inversa de reposo almacenada en convención de filas: world=inverse(stored_matrix.T). Para las 83 jerarquías/2.355 huesos, el máximo error de composición local es 2.875e-7. Esto corrobora la interpretación de padres y transformaciones; no prueba una asignación de pesos a una malla.
- Primer IntroNis01: tres esqueletos con 24, 24 y 35 huesos. Los bancos de personajes usan variantes comprimidas que se conservan como metadatos y SHA-256; no se reinterpretan como floats. Índices de skinning/material palettes todavía no vinculados a esos esqueletos.

## Visibilidad y reparación propuesta (no aplicada)

body-visibility-analysis.json muestra 23 mallas BASE/BODY: solo cuatro KIT00_BODY tienen extensión no nula; las otras 19 están colapsadas. Esto podría ocultar el modelo si la carrera selecciona un kit distinto; la selección real en carrera no se ha observado.

Se detectó además que las cuatro cabeceras KIT00_BODY declaran u32 0x38B040AD en payload+20 (951.074.989). La mitad superior contiene exactamente el número de vértices 14.512 y la inferior el de triángulos 16.557: firma de la escritura anterior de dos u16. En otras mallas, el u32 es un recuento pequeño, normalmente igual al número de triángulos; algunos originales difieren ligeramente, por lo que no se normalizan todas las cabeceras.

`plan_header_repair.py` calcula en memoria la corrección limitada a las cuatro cabeceras conocidas. `header-repair-plan.json` contiene hash fuente/resultante, tamaño 9.952.256 y cuatro escrituras: offsets absolutos 0x12FA4, 0xAE324, 0x147924, 0x1E0624, bytes AD 40 B0 38 -> AD 40 00 00. Solo ocho bytes distintos. Tamaños de chunks y offsets permanecen iguales. No cambia texturas, materiales ni física.

La aprobación de esa reparación se solicitó explícitamente al usuario. No se ha creado GEOMETRY.BIN.bak ni modificado GEOMETRY.BIN. Antes de aplicar: confirmar fuente SHA-256, juego cerrado, estado Git limpio; crear respaldo .bak exacto y commit; escribir temporal GEOMETRY.BIN.uma-header.tmp, validar y sustituir de forma atómica. La corrección no debe presentarse como prueba de que la carrera funciona.

Pruebas al cierre de la segunda revisión: 18 aprobadas. La reparación previa se prueba solo en memoria, comparando el árbol de chunks completo y los ocho offsets distintos, rechazando un archivo ya corregido y otro coche. Los 716 archivos de datos conservan sus hashes iniciales. Pendiente respuesta del usuario a la reparación concreta; no se abrió el juego.

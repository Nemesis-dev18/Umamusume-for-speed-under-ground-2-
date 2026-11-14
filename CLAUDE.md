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

## Skinning nativo: tercera revisión

`extract_native_skin.py` extrae cinco mallas de NIS/Scene_IntroNis01_BundleB.bun, con 4.265 vértices ponderados, a OBJ y skin.json dentro de modding/extracted/native-skin-validated. No modifica el bundle fuente. Conserva posiciones, normales, UV, índices, pesos y tablas por grupo sin forzar una asignación a un esqueleto concreto.

Layout observado de vértice de 60 bytes: posición float3 en +0, normal float3 +12, BGRA +24, UV float2 +28, tres pesos float3 +36 y tres índices locales almacenados como float3 en +48. Se comprueban finitud, pesos en [0,1], suma 1 (tolerancia 1e-5), índices enteros 0..15 y triángulos dentro del número de vértices. Solo se admite si todo el prefijo anterior a los registros es filler 0x11.

Tabla de rangos de 60 bytes: count u32 en +12 y offset u32 en +52; slot crudo u8 en +32 y paleta candidata de 16 bytes en +33..+48. Los índices locales usados se traducen por esa tabla; todos quedan dentro del byte de número de huesos de la cabecera. Los rangos deben cubrir exactamente los índices sin huecos. No se presenta todavía esta correspondencia como vínculo definitivo entre malla y nombre de esqueleto.

En la cabecera del solid, descontando filler inicial, el byte +24 coincide con los números de huesos de las cinco mallas: 24, 24, 24, 24 y 35. Se conserva como bone_count_byte y limita las entradas utilizadas de la paleta. La identificación del esqueleto específico de cada malla sigue pendiente; compartir 24 huesos no basta para elegir entre Bip02 y Bip03.

19 pruebas pasan: la nueva prueba cubre las cinco mallas, cobertura de rangos y límites de paletas, y rechaza peso 1.5 e índice local 16. Verificación completa repetida: los 716 SHA-256 fuente siguen iguales. No se ha aplicado la reparación de cabeceras ni creado su .bak; sigue pendiente la respuesta a la confirmación concreta.

## Reparación aprobada y aplicada

El usuario respondió explícitamente «Sí, aplica la reparación con respaldo». Antes del cambio se verificó estado Git limpio, ausencia de proceso SPEED2.EXE y coincidencia exacta del SHA-256 fuente con el plan. Se creó CARS/COROLLA/GEOMETRY.BIN.bak, se verificó byte a byte y se versionó en el commit e1aadcbbdb285900323130ba84f3080a08f9c4ec antes de modificar GEOMETRY.BIN.

Se escribió el temporal aprobado, se verificó su contenido, se conservó el modo de permisos y se sustituyó de forma atómica con fsync. Resultado: 9.952.256 bytes; SHA-256 1d16d7e3c9d1a7ed3f240224a6eb4e725140035188b45a2cc48fd17733d41808; exactamente ocho bytes distintos en los cuatro campos aprobados. El árbol completo de chunks coincide antes/después. Los cuatro recuentos u32 son ahora 16.557. Se conservaron todos los offsets, tamaños, materiales, texturas y referencias de colisión.

De los 716 archivos del inventario original, los otros 715 conservan su hash. El respaldo es una adición intencionada, no una modificación de otro recurso. El informe verificable está en modding/header-repair-applied.json. Las 19 pruebas pasan; la prueba de reparación usa el respaldo previo como entrada y exige que el archivo instalado coincida exactamente con la salida calculada.

No se abrió el juego. Visibilidad y estabilidad en carrera, ruedas residuales, materiales y animación siguen pendientes de una prueba real. Esta reparación no equivale al mod final ni demuestra equivalencia con el video. Los estados históricos anteriores a esta sección quedan superados únicamente respecto a la reparación de cabeceras.

## Prueba de usuario después de reparar las cabeceras

Se lanzó la copia de prueba a petición explícita del usuario. El usuario respondió «Carga, pero sigue invisible» en carrera y aportó captura con ruedas, luces y matrícula visibles sin el cuerpo. También informó que en selección sigue en pose de importación/T. Por tanto, reparar el recuento no resolvió la invisibilidad. No atribuir éxito de carga visual a las pruebas estructurales. La animación de Kitasan no está integrada.

Lectura de materiales de GLOBALB.BUN: los chunks 0x00135200 llevan hash en payload+12 y nombre ASCII desde +20. El hash 0x02A05578 corresponde a DECAL; 0x0FEDEE40 a DULLPLASTIC y 0x12C9453C a MOLDINGS. El primer rango de KIT00_BODY_A del Corolla usa el shader DECAL y el atlas de Kitasan. Este hallazgo es una hipótesis para una prueba aislada, no una causa confirmada. No se modificaron materiales ni GLOBAL.

Antes de otro cambio se solicitó comparar una carrera con Nissan 240SX, cuyos recursos no fueron modificados en este flujo. El resultado determinará si la investigación debe concentrarse en el Corolla o en un fallo general de renderizado de esta copia. No se aplicó ninguna segunda reparación.

## Referencia 240SX y prueba de material aprobada

El usuario confirmó que el Nissan 240SX sí muestra carrocería en carrera, mientras Kitasan sigue en pose de importación en selección. Esto acota el problema a los recursos/ruta de dibujo del Corolla, sin demostrar aún la causa exacta.

Se preparó en memoria material-probe-plan.json y plan_material_probe.py: el primer rango de cada KIT00_BODY usa DECAL (0x02A05578) y atlas 0x1C9637A6; la prueba cambia solo el hash del shader referenciado a DULLPLASTIC (0x0FEDEE40), cuya definición existe en GLOBALB.BUN. Cuatro escrituras u32 en 0x13080, 0xAE408, 0x147A10 y 0x1E0708: 78 55 A0 02 -> 40 EE ED 0F. Tamaño idéntico: 9.952.256 bytes. Sin cambios de malla, límites, texturas, pose, ruedas ni física.

Pasaron 21 pruebas, incluidas la identidad exacta de los 16 bytes distintos, preservación del árbol de chunks y definición nativa del material. El usuario aprobó explícitamente «Sí, ya cerré el juego; aplica la prueba». Se comprobó ausencia del proceso SPEED2.EXE. Antes de sustituir se creará GEOMETRY.BIN.before-material.bak y un commit de ese respaldo, manteniendo el .bak de la reparación anterior.


Prueba de material aplicada después de la aprobación: respaldo exacto GEOMETRY.BIN.before-material.bak versionado antes de sustituir, commit 81ce1576dd5855127f8423f391eb75f42cb946e2. Solo cambiaron los 16 bytes revisados; tamaño 9.952.256; hash instalado cedf717c16c342b449c32e312351bd2f93d21533446b9501488dd0b5a3664389. Se verificó la sustitución atómica y el árbol de chunks idéntico. Los otros 715 recursos del inventario mantienen sus hashes. Se conservan ambos respaldos. Las 21 pruebas pasan, incluyendo la cadena de comparación entre respaldo inicial, reparación de cabeceras, respaldo previo al material y resultado instalado. Informe: modding/material-probe-applied.json. El resultado en carrera todavía no se ha observado; la pose y animación no se han cambiado.

## Diagnóstico de llamadas Direct3D aprobado

La prueba DECAL -> DULLPLASTIC no resolvió la invisibilidad en carrera y la captura de selección muestra transparencia parcial, rueda y sombra residuales. No se interpreta como arreglo de materiales. Se conserva el estado instalado para observarlo sin añadir otra modificación de recursos.

Se preparó el módulo de diagnóstico en modding/diagnostics/UmaDrawLog.asi, con código en uma_draw_log.c y prueba independiente pass_through_test.c. La prueba GPU pasó: un hook instalado a través de un segundo dispositivo de software observa la llamada del dispositivo de hardware, conserva el píxel blanco y el shader original y registra Present y metadatos. Compilación con -Wall -Wextra -Werror. Imports inspeccionados: d3d9, KERNEL32, msvcrt y USER32. No requiere proveedor REA ni lectura del ejecutable del juego.

El usuario autorizó explícitamente la excepción temporal a solo datos: scripts/UmaDrawLog.asi, 239.762 bytes, SHA-256 b38a2d5d4eea05311a5af11be46d6657233701266c806ab9db00c1cfa6750526; registro append modding/uma-draw.log. El módulo sustituye entradas de vtable de Direct3D9 en memoria, no instrucciones del ejecutable ni bytes de SPEED2.EXE. No altera shaders/estados de dibujo ni recursos. Las cantidades conocidas de vértices/triángulos son candidatos, no prueba de identidad visual. No hay módulo anterior que sobrescribir. Se retirará con el juego cerrado y se conservará el registro.


Inicialización del diagnóstico: el primer módulo se observó cargado por nombre en /proc/<pid>/maps, pero no produjo registro. Una prueba independiente LoadLibrary, manteniendo CWD=scripts como un cargador ASI, reprodujo el fallo. Se corrigió para obtener únicamente la ruta de su propio módulo con GetModuleFileNameW y abrir el log con _wfopen; no depende de CWD ni lee el ejecutable del juego. La prueba de carga corregida pasó y dejó HOOK installed=1. No se observó el CWD Windows del juego directamente: la reproducción respalda esta causa, sin convertirla en una observación de ese estado interno. Se respalda el módulo temporal previo antes de actualizarlo; no se modifican recursos del juego.

## Instrucción vigente: no lanzar hasta resolver selección y carrera

El usuario pidió no volver a lanzar el juego mientras se prepara la solución completa: Kitasan debe verse bien en selección y carrera, con animación natural como la referencia TjefYsbtwTI; los demás coches deben conservar su carrocería al seleccionar Kitasan. No reemplazar el objetivo por una pose estática ni llamar éxito a una prueba de archivos. No se ha lanzado el juego después de esta instrucción. Criterios pendientes en modding/release-criteria.json.

Se capturó el diagnóstico real en modding/diagnostics/game-draw-session-1.log y se retiró scripts/UmaDrawLog.asi con el proceso cerrado, verificando su hash. La firma 14.512 vértices/16.557 primitivas y VB 522.432 bytes, stride 36, aparece en selección. En el tramo posterior correlacionado con carrera por la prueba del usuario (frames 2760..3840) siguen llegando muchas llamadas DIP y cero candidatos de esa firma. No identifica directamente el nombre de la pieza ni demuestra qué condición impide enviarla. Informe en draw-diagnostic-result.json.

Se inspeccionaron 56 modelos de otros coches sin cambiarlos: el mayor solid observado tiene 2.752 vértices, frente a 14.512 de Kitasan repetidos en cuatro LOD. stock-mesh-budgets.json registra datos, no un límite duro del motor. Los límites del primer rango de material siguen describiendo parte del carro y no contienen el personaje. Se preparó bounds-repair-plan.json: 24 floats (96 bytes de campos, 85 bytes realmente distintos) para cubrir todos los vértices referenciados de los cuatro cuerpos, sin alterar tamaños ni offsets. Este cambio NO se ha aplicado.

## Animación de Kitasan preparada fuera del juego

Se importó el rig ya preparado del modelo proporcionado por el usuario (no de la instalación original del juego), tras comparar exactamente posiciones, normales, UV e índices con el cuerpo instalado. 14.512 vértices, 16.557 triángulos, 282 huesos; pesos normalizados e índices válidos. Datos de autoría en modding/character-source. La primera comparación efímera de índices usó list frente a tuple y se corrigió a igualdad de arrays; no había diferencia de índices ni se cambió el orden de caras. La convención geométrica se contrastó con BODY_D y BASE_C originales del 240SX: ambas coinciden con sus normales.

animate_kitasan.py genera idle de 32 fases y carrera de 48 fases: IK de dos segmentos en las cadenas D que realmente pesan las piernas, trayectoria de apoyo lineal y recuperación Hermite, longitud de segmentos fija, balanceo de torso, cabeza compensada, brazos opuestos, flexión de dedos y movimiento secundario autorado de pelo/cola. No simula física MMD ni implementa todavía la respuesta de velocidad dentro del juego. Los objetivos de tobillo se cumplen con error numérico inferior a 1e-12 m y el mínimo de superficie ronda -0.000031 m. Se prueban ciclos, matrices, longitudes, suelo, normales y ausencia de brazos en pose de importación.

Las vistas CPU llevan la etiqueta PREVIA OFFLINE — NO ES GAMEPLAY. Se revisó una segunda versión para que el antebrazo acompañe el brazo opuesto, evitando ambas manos elevadas como en la primera previa. Últimos clips/previas: modding/animation-offline-v2. Los transforms se guardan comprimidos por hueso; no son una animación integrada ni un render del motor. Quedan por pulir manos/ropa, completar la integración, resolver la omisión del cuerpo en carrera y verificar que los demás coches se dibujen.

El extractor de geometría ahora admite varios rangos contiguos de materiales al leer mallas nativas, comprobando cobertura sin huecos/solapamientos. Se conservó el comportamiento de exportación para el prototipo Corolla de un solo rango activo.

Cierre de esta etapa offline: 27 pruebas aprobadas tras la segunda versión del movimiento. Se revisaron visualmente reposo y cuatro fases de carrera desde delante y detrás con rasterizador CPU. La primera versión mantenía ambos antebrazos elevados; se cambió para que el antebrazo acompañe el arco del brazo, con oposición entre lados. Las manos y la ropa aún necesitan pulido; no se afirma acabado final. El juego sigue cerrado y el recurso instalado conserva el hash de la prueba de material; ni los bounds propuestos ni las poses offline se instalaron. No se reintrodujo el diagnóstico temporal.

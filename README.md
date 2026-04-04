# Trabajo práctico — Procesamiento puntual e histograma (Grupo 1)

**Repositorio público:** [github.com/mateoHernandez123/procesamiento-imagenes-tp2-grupo1](https://github.com/mateoHernandez123/procesamiento-imagenes-tp2-grupo1)

**Materia:** Procesamiento de imágenes I  
**Integrantes:** Mateo Hernández, Felipe Lucero

Este repositorio contiene el código y la documentación para el trabajo sobre conversión a escala de grises, histograma, mejora puntual (sin filtros espaciales), umbralización y superposición en rojo de la región segmentada.

## Estructura del proyecto

| Ruta                          | Descripción                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------- |
| `entrada/`                    | Imagen original de trabajo (por defecto `imagen.jpg`).                       |
| `salida/`                     | BMP, `panel_imagenes.png`, `panel_histogramas.png`, `reporte_...`.           |
| `salida/archivo_previo/`      | Capturas PNG obtenidas en clase (referencia).                                |
| `src/procesamiento_imagen.py` | Programa principal.                                                          |
| `doc-info.md`                 | Respuestas técnicas y justificación de decisiones (consignas).               |
| `requirements.txt`            | NumPy (pipeline), OpenCV (lectura) y matplotlib (visualización).             |
| `.gitignore`                  | No versiona la salida regenerable; sí `entrada/` y `salida/archivo_previo/`. |

## Requisitos

- Python 3.10 o superior recomendado.
- **NumPy** (operaciones vectorizadas del TP), **opencv-python** (solo lectura) y **matplotlib** (paneles; no sustituye las fórmulas del script).

## Qué librería usamos y para qué

**Regla del trabajo:** las **fórmulas del TP** (Rec. 601, histograma, estadísticas, normalización puntual, Otsu, umbral, máscara, composición) están implementadas en **nuestro código** con NumPy (broadcasting y funciones sobre arreglos), **sin** delegar el pipeline en `cv2.cvtColor`, `calcHist`, `threshold`, etc., tal como se recomienda en cátedra para reducir costo computacional frente a bucles puros en Python.

| Herramienta                                                            | Por qué está                                                                   | Uso que le damos                                                                                    | Qué **no** hacemos con ella                                                            |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **NumPy**                                                              | Eficiencia en matrices de imagen.                                              | Grises, `bincount` para histograma, min/max/mean, normalización, máscara, imagen final en arreglos. | No usamos APIs de alto nivel de OpenCV/scikit-image para esos pasos.                    |
| **OpenCV (`cv2`)**                                                     | Decodificar JPEG/PNG sin implementar un lector de formato.                     | **Únicamente** `cv2.imread` para obtener BGR como `ndarray`.                                          | `cvtColor`, `calcHist`, `threshold`, filtros, `imwrite` en el pipeline del TP.        |
| **matplotlib**                                                         | Dos ventanas al ejecutar (imágenes, luego histogramas) y dos PNG en `salida/`. | `imshow` / `bar` con datos **ya calculados**; BGR→RGB solo para dibujar.                            | No calcula el histograma ni las transformaciones puntuales del TP.                   |
| **Biblioteca estándar** (`argparse`, `os`, `struct`, `pathlib`, `sys`) | CLI, rutas, bug de rutas Unicode en Windows, formato BMP, errores.             | Argumentos, `chdir` solo para leer, cabeceras binarias del BMP, rutas y mensajes.                   | Ningún algoritmo de procesamiento de imagen.                                           |

Los BMP de salida se escriben con **`struct` + bytes** (cabecera) y **píxeles desde NumPy** (`tobytes` por filas con relleno), sin `cv2.imwrite`.

El detalle extendido (incluida la distinción entre “abrir archivo” y “procesar imagen”) está en **`doc-info.md`, sección 6**.

## Instalación y ejecución

Desde la carpeta raíz del proyecto:

```bash
pip install -r requirements.txt
python src/procesamiento_imagen.py
```

Por defecto se lee `entrada/imagen.jpg`, se guardan los BMP y **dos PNG** (`panel_imagenes.png` y `panel_histogramas.png`). Se abre **primero** una ventana solo con las imágenes del flujo; **al cerrarla**, se abre otra con los dos histogramas. Cerrá también esa segunda ventana para terminar.

### Opciones útiles

```bash
# Otra imagen y carpeta de salida
python src/procesamiento_imagen.py -i entrada/mi_foto.jpg -o salida/prueba1

# Umbral fijo (0–255) en lugar del automático de Otsu
python src/procesamiento_imagen.py -u 120

# Objeto más oscuro que el fondo: máscara en píxeles por debajo del umbral
python src/procesamiento_imagen.py --segmento-oscuro

# Ajustar cuándo aplicar mejora por normalización lineal (promedio de gris)
python src/procesamiento_imagen.py --mejora-bajo 45 --mejora-alto 210

# Sin ventana (servidor / scripts); igual guarda BMP y los dos paneles PNG
python src/procesamiento_imagen.py --no-mostrar

# Sin guardar los PNG de panel (solo BMP + ventanas si no usás --no-mostrar)
python src/procesamiento_imagen.py --no-panel-png
```

## Archivos generados en `salida/`

- `gris_original.bmp` — luminancia de la imagen de entrada.
- `gris_trabajo.bmp` — imagen en gris usada para el umbral (tras mejora puntual si corresponde).
- `mascara.bmp` — máscara binaria (0 / 255).
- `resultado_final.bmp` — RGB: fondo en gris (como la luminancia original) y región segmentada en rojo.
- `panel_imagenes.png` — captura de la primera ventana (entrada, grises, máscara, resultado).
- `panel_histogramas.png` — captura de la segunda ventana (histogramas con conteos vía `np.bincount`).
- `reporte_procesamiento.txt` — resumen numérico (dimensiones, promedio, si hubo mejora, umbral).

Para más detalle teórico y respuestas a la consigna, ver **`doc-info.md`**.

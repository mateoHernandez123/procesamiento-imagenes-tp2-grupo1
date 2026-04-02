# Trabajo práctico — Procesamiento puntual e histograma (Grupo 1)

**Materia:** Procesamiento de imágenes I  
**Integrantes:** Mateo Hernández, Felipe Lucero

Este repositorio contiene el código y la documentación para el trabajo sobre conversión a escala de grises, histograma, mejora puntual (sin filtros espaciales), umbralización y superposición en rojo de la región segmentada.

## Estructura del proyecto

| Ruta                          | Descripción                                                         |
| ----------------------------- | ------------------------------------------------------------------- |
| `entrada/`                    | Imagen original de trabajo (por defecto `imagen.jpg`).              |
| `salida/`                     | BMP, `panel_imagenes.png`, `panel_histogramas.png`, `reporte_...`.  |
| `salida/archivo_previo/`      | Capturas PNG obtenidas en clase (referencia).                       |
| `src/procesamiento_imagen.py` | Programa principal.                                                 |
| `doc-info.md`                 | Respuestas técnicas y justificación de decisiones (consignas).      |
| `requirements.txt`          | OpenCV (lectura) y matplotlib (visualización).                      |
| `.gitignore`                | No versiona la salida regenerable; sí `entrada/` y `salida/archivo_previo/`. |

## Requisitos

- Python 3.10 o superior recomendado.
- **opencv-python** (solo lectura del archivo) y **matplotlib** (dos ventanas secuenciales y dos PNG en `salida/`; no calcula el histograma).

## Qué librería usamos y para qué (cálculos a mano)

**Regla del trabajo:** la **matemática y la lógica sobre los píxeles** (grises, histograma, promedios, mín/máx, normalización puntual, Otsu, umbral, máscara, imagen final) se hace **solo en nuestro código**, con fórmulas explícitas y bucles sobre listas. **No** usamos OpenCV, NumPy ni otras librerías para esas operaciones.

| Herramienta                                                            | Por qué está                                                                   | Uso que le damos                                                                                    | Qué **no** hacemos con ella                                                            |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **OpenCV (`cv2`)**                                                     | Decodificar JPEG/PNG sin implementar un lector de formato.                     | **Únicamente** `cv2.imread` para obtener valores BGR por píxel; luego se copian a listas de Python. | `cvtColor`, `calcHist`, `threshold`, filtros, `imwrite` en los resultados del TP, etc. |
| **matplotlib**                                                         | Dos ventanas al ejecutar (imágenes, luego histogramas) y dos PNG en `salida/`. | `imshow` / `bar` con datos **ya calculados**; BGR→RGB solo para dibujar.                            | No calcula histogramas ni transforma píxeles del TP.                                   |
| **Biblioteca estándar** (`argparse`, `os`, `struct`, `pathlib`, `sys`) | CLI, rutas, bug de rutas Unicode en Windows, formato BMP, errores.             | Argumentos, `chdir` solo para leer, cabeceras binarias del BMP, rutas y mensajes.                   | Ningún algoritmo de procesamiento de imagen.                                           |

Los BMP de salida se generan con **`struct` + escritura binaria** (stdlib), sin NumPy ni `cv2.imwrite`.

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
- `panel_histogramas.png` — captura de la segunda ventana (los dos histogramas; conteos calculados a mano en el script).
- `reporte_procesamiento.txt` — resumen numérico (dimensiones, promedio, si hubo mejora, umbral).

Ya **no** se generan `histograma_*.csv` ni `histograma_*.svg` (sustituidos por matplotlib).

Para más detalle teórico y respuestas a la consigna, ver **`doc-info.md`**.

## Nota sobre rutas en Windows

Si la ruta del proyecto incluye caracteres especiales (por ejemplo “Año”, “N°”), el script evita el fallo conocido de `cv2.imread` cambiando al directorio del archivo antes de leerlo.

## Entrega académica (cátedra)

Comprimir la carpeta con un nombre del estilo **TP2 - Grupo 1**, incluyendo `entrada`, `salida` regenerada, `src`, `README.md`, `doc-info.md` y `requirements.txt`, según lo que pida la materia.

## Publicar en GitHub (repositorio público)

Desde la raíz del proyecto, con [Git](https://git-scm.com/) instalado:

```bash
git init
git add .
git commit -m "TP Procesamiento de imágenes I — Grupo 1"
```

Opción A — [GitHub CLI](https://cli.github.com/) (`gh auth login` una vez):

```bash
gh repo create NOMBRE-DEL-REPO --public --source=. --remote=origin --push
```

Opción B — en [github.com/new](https://github.com/new) creá un repositorio vacío **público**, sin README, y luego:

```bash
git remote add origin https://github.com/TU_USUARIO/NOMBRE-DEL-REPO.git
git branch -M main
git push -u origin main
```

Sugerencia de nombre de repo: `procesamiento-imagenes-tp2-grupo1` (sin espacios ni caracteres raros).

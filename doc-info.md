# Documentación técnica y respuestas a la consigna

**Trabajo:** procesamiento puntual, histograma y segmentación por umbral  
**Grupo 1** — Mateo Hernández, Felipe Lucero

Este documento complementa el `README.md` y sirve como texto de acompañamiento para la presentación: qué se hizo, con qué fórmulas y cómo se relaciona con cada ítem de la actividad.

---

## 1. Conversión a escala de grises

**Consigna:** elegir una imagen en escala de grises o convertirla si hace falta.

Si la imagen de entrada está en color (tres canales B, G, R en el orden que devuelve OpenCV), la luminancia se calcula **píxel a píxel** con la combinación lineal estándar (ITU-R BT.601), usando los valores enteros de cada canal:

\[
Y = \mathrm{round}(0{,}299\,R + 0{,}587\,G + 0{,}114\,B)
\]

El resultado se recorta al rango \([0, 255]\). En el código se implementa como `int(0.299*r + 0.587*g + 0.114*b + 0.5)`, equivalente al redondeo. No se usa ninguna función de “convertir a grises” de la librería: solo lectura de los tres números por píxel y la cuenta en Python puro (listas anidadas).

Si la entrada ya fuera un solo canal, el mismo programa podría adaptarse copiando ese canal; en nuestro caso la imagen de trabajo es a color y se convierte como arriba.

---

## 2. Histograma

**Consigna:** calcular y mostrar el histograma.

Se define un arreglo de 256 contadores, inicialmente en cero. Se recorre toda la imagen en grises y, para cada nivel \(i \in \{0,\ldots,255\}\), se incrementa `hist[i]`.

**Mostrar:** los 256 conteos del histograma se calculan **a mano** en el script. Para visualizar al ejecutar se usa **matplotlib** en **dos pasos**: primero una ventana solo con las imágenes (entrada, grises, máscara, resultado); al cerrarla, otra ventana con los dos gráficos de barras. No recalcula el histograma; solo dibuja valores ya obtenidos. Con `--no-mostrar` se guardan igual **`salida/panel_imagenes.png`** y **`salida/panel_histogramas.png`**.

No se generan archivos CSV ni SVG del histograma (eran poco claros como figura); la consigna de “mostrar” el histograma queda cubierta por la segunda ventana interactiva y por `panel_histogramas.png`.

El histograma del **gris original** sirve para ver si la imagen está concentrada en tonos bajos (oscura), altos (clara) o repartida. El del **gris de trabajo** refleja la imagen **después** de la posible mejora puntual y es el que se usa para decidir el umbral automático (Otsu), al estar alineado con los tonos que entran al threshold.

---

## 3. Procesamiento puntual si la imagen es muy oscura o muy clara

**Consigna:** mejorar con procesamiento puntual, **no** filtros espaciales.

Se calcula el **promedio de intensidad** del gris original recorriendo todos los píxeles y sumando manualmente. Si el promedio es menor que un umbral bajo (por defecto 50) o mayor que uno alto (por defecto 200), se aplica **normalización lineal** (estiramiento de contraste), también píxel a píxel:

1. Se obtienen \(v*{\min}\) y \(v*{\max}\) del gris original con un solo barrido.
2. Si \(v*{\max} > v*{\min}\), para cada píxel \(v\):

\[
v' = \mathrm{round}\bigl((v - v*{\min}) \cdot \frac{255}{v*{\max} - v\_{\min}}\bigr)
\]

recortado a \([0,255]\). Si \(v*{\max} = v*{\min}\) (imagen plana), no hay estiramiento y se deja el valor original.

Es una transformación **puntual** \(v' = f(v)\): no intervienen vecinos; no hay convoluciones ni filtros de suavizado/borde.

---

## 4. Máscara binaria por umbral

**Consigna:** máscara de un objeto según tonalidad de gris.

Sobre la imagen **gris de trabajo** (tras la mejora, si se aplicó) se define un umbral \(T\):

- **Por defecto:** \(T\) se calcula con el método de **Otsu** usando **solo** el histograma de 256 bins y el total de píxeles: se maximiza la varianza **entre** clases (fondo vs. objeto) de forma explícita en código, sin llamadas a funciones de umbral de OpenCV.
- **Alternativa:** se puede fijar \(T\) con la opción `-u` / `--umbral` si el histograma sugiere un corte más adecuado al objeto concreto.

La máscara asigna 255 al objeto y 0 al fondo según la relación de \(v'\) con \(T\):

- Por defecto (**objeto más claro** que el fondo): máscara 255 si \(v' > T\).
- Con `--segmento-oscuro` (**objeto más oscuro**): máscara 255 si \(v' < T\).

Es importante mirar el resultado: si el objeto y el fondo quedan invertidos respecto de lo deseado, basta con usar `--segmento-oscuro` o ajustar el umbral manualmente según el pico del objeto en el histograma.

---

## 5. Imagen final: gris + zona en rojo

**Consigna:** RGB con grises en casi toda la imagen y **solo** la región de interés en rojo; el resto como la imagen original en apariencia.

La consigna aclara que la salida debe ser **RGB en grises** salvo la zona de interés. Por eso, para los píxeles **fuera** de la máscara se copia la **luminancia original** (antes de la normalización) a los tres canales: \(B = G = R = Y\_{\text{original}}\), que se ve como gris. Donde la máscara vale 255, se asigna rojo puro en BGR: \([0, 0, 255]\).

Así la composición cumple: imagen en escala de grises en RGB y acento en rojo solo sobre el objeto segmentado.

---

## 6. Librerías: qué usamos, para qué, y qué queda explícitamente a mano

### 6.1 Principio (consigna: cálculos manuales y matemáticos)

En este trabajo, **“hacer las cuentas a mano”** significa: toda la parte de **procesamiento de la imagen** (transformar y combinar valores de intensidad, armar el histograma, decidir y aplicar umbrales, construir la máscara y la imagen final) está implementada en el código con **fórmulas escritas explícitamente** y **bucles** sobre listas de Python.

**No** usamos —para eso— funciones de bibliotecas como OpenCV, NumPy, SciPy, Pillow, scikit-image, etc. En particular **no** usamos de OpenCV: `cvtColor`, `calcHist`, `equalizeHist`, `normalize`, `threshold`, filtros convolucionales, morfología, ni `imwrite` para los entregables del pipeline.

Las dependencias de terceros son **OpenCV** (solo **entrada** de datos) y **matplotlib** (solo **visualización** del panel; ver tabla). El **guardado** de las imágenes del pipeline no pasa por OpenCV: los **BMP** se escriben con la biblioteca estándar.

### 6.2 Tabla: cada caso de uso de librería / módulo

| Qué se importa          | Motivo por el que está en el proyecto                                                                                                           | Uso concreto que le damos                                                                                                                                                                                                        | Qué **no** hacemos con eso                                                                                                                                                                                   |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **OpenCV (`cv2`)**      | Decodificar archivos comprimidos o en formatos binarios estándar (JPEG, PNG, etc.) sin implementar nosotros un decodificador completo en el TP. | **Solo** `cv2.imread`: leer el archivo de entrada y obtener valores numéricos por canal (BGR). Inmediatamente después copiamos esos valores a **listas de Python** y el resto del programa trabaja únicamente sobre esas listas. | Cualquier operación de procesamiento de imagen de OpenCV (ver lista arriba). OpenCV **no** calcula el gris, el histograma, el umbral de Otsu, la máscara ni la imagen compuesta: eso lo hace nuestro código. |
| **matplotlib**          | Presentación: dos ventanas secuenciales (imágenes, luego histogramas) y dos PNG opcionales.                                                     | `imshow` y `bar` con listas ya calculadas; BGR→RGB solo para dibujo.                                                                                                                                                             | No implementa `calcHist` ni operaciones del TP: el histograma sigue siendo el arreglo de 256 enteros llenado en bucles.                                                                                      |
| **`argparse`** (stdlib) | Interfaz de línea de comandos estándar.                                                                                                         | Definir opciones (`-i`, `-o`, `-u`, flags).                                                                                                                                                                                      | Nada relacionado con píxeles.                                                                                                                                                                                |
| **`os`** (stdlib)       | Compatibilidad de rutas en Windows.                                                                                                             | `chdir` al directorio del archivo antes de `imread`, porque `cv2.imread` a veces falla con rutas con caracteres Unicode.                                                                                                         | No participa en matemática de imagen.                                                                                                                                                                        |
| **`struct`** (stdlib)   | Empaquetar enteros en bytes según el formato de archivo.                                                                                        | Escribir las cabeceras del **BMP** (tamaños, dimensiones, desplazamientos).                                                                                                                                                      | No procesa contenido semántico de la imagen; solo formato de disco.                                                                                                                                          |
| **`pathlib`** (stdlib)  | Rutas y comprobación de archivos de forma portable.                                                                                             | Resolver rutas, crear carpetas de salida, abrir archivos de texto/ binarios.                                                                                                                                                     | No altera valores de píxeles.                                                                                                                                                                                |
| **`sys`** (stdlib)      | Salida de errores y código de retorno.                                                                                                          | Mensajes si falta OpenCV o no existe la entrada.                                                                                                                                                                                 | No procesa imagen.                                                                                                                                                                                           |

### 6.3 Detalle: por qué OpenCV solo en la lectura

Leer un JPEG o PNG implica tablas Huffman, IDCT, espacios de color del contenedor, etc. Eso es **ingeniería de formato de archivo**, no el objetivo pedagógico del TP (histograma, puntual, umbral). Por eso se admite **una** llamada de lectura para obtener la matriz de muestras; a partir de ahí, el trabajo exigible (**cálculos solo a mano y matemáticamente** sobre esas muestras) ocurre en funciones propias del script.

OpenCV, al leer, puede devolver internamente un arreglo que en la práctica está respaldado por NumPy; **nosotros no importamos NumPy** y no usamos ese arreglo para operaciones vectorizadas: lo convertimos a `list` y todas las operaciones son escalares en bucles, como en un pseudocódigo matemático píxel a píxel.

### 6.4 Resumen en una frase

**Entrada:** OpenCV solo para **abrir** el archivo y obtener números. **Procesamiento:** matemática y lógica **implementadas en el código**, sin delegar en OpenCV ni en otras librerías de imagen. **Vista:** matplotlib dibuja resultados ya calculados. **Salida:** BMP con **stdlib** (`struct` + escritura binaria).

---

## 7. Archivos de imagen del proyecto

- **`entrada/imagen.jpg`:** imagen utilizada como entrada del pipeline.
- **`salida/`:** BMP, `panel_imagenes.png`, `panel_histogramas.png`, `reporte_procesamiento.txt`.
- **`salida/archivo_previo/`:** PNG generados en una instancia anterior del trabajo en laboratorio (`resultado_rojo.png`, `resultado_manual.png`, etc.), conservados solo como referencia visual; el flujo oficial documentado es el del script actual y los BMP en `salida/`.

---

## 8. Cómo ejecutar en otra máquina

1. Instalar Python 3.
2. `pip install -r requirements.txt`
3. Colocar la imagen en `entrada/` (o indicar ruta con `-i`).
4. `python src/procesamiento_imagen.py`

Si en Windows la ruta del proyecto tiene caracteres Unicode y hubiera problemas al leer, el script ya contempla la carga desde el directorio del archivo; en caso extremo, copiar el proyecto a una ruta solo ASCII también evita conflictos con versiones antiguas de OpenCV.

---

## 9. Resumen breve de cumplimiento de ítems

| Ítem                | Cómo se aborda                                                        |
| ------------------- | --------------------------------------------------------------------- |
| Grises              | Fórmula BT.601 manual por píxel.                                      |
| Histograma          | 256 bins a mano; barras en segunda ventana / `panel_histogramas.png`. |
| Mejora oscuro/claro | Normalización lineal puntual según promedio.                          |
| Máscara             | Umbral manual u Otsu manual sobre histograma; binarización explícita. |
| Salida rojo + gris  | BGR: rojo en máscara; \(B=G=R\) con gris **original** fuera.          |

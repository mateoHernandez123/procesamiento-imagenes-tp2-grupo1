#!/usr/bin/env python3
"""
Procesamiento puntual de imágenes — operaciones sobre píxeles hechas a mano.

Cálculos de imagen (matemática sobre valores de píxeles)
    Grises, histograma, estadísticas, normalización puntual, Otsu, umbral,
    máscara y composición final: todo con bucles, sumas, productos y
    comparaciones en Python sobre listas anidadas. No se usa OpenCV ni NumPy
    ni otras librerías para esas operaciones.

Librerías externas y su único rol
    opencv-python (cv2): solo ``cv2.imread`` para decodificar el archivo de
    entrada (JPEG/PNG) y obtener números por canal. Equivale a “abrir el
    archivo y leer los píxeles”; no reemplaza fórmulas ni algoritmos del TP.
    Los valores se copian enseguida a ``list`` de Python; el resto del
    programa no usa la matriz de OpenCV.

Biblioteca estándar de Python
    argparse, os, struct, pathlib, sys — igual que antes.

matplotlib (solo visualización)
    Al ejecutar el script se abre primero una ventana solo con las imágenes del
    flujo; al cerrarla, otra ventana con los dos histogramas (conteos a mano;
    matplotlib solo dibuja). Opcionalmente se guardan ``panel_imagenes.png`` y
    ``panel_histogramas.png`` en ``salida/``.

Salida en disco
    BMP del pipeline (misma implementación manual). Ya no se generan CSV/SVG
    de histograma (sustituidos por la vista en matplotlib).
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
from pathlib import Path

# OpenCV: solo imread (decodificar entrada). No se usa para grises, hist, umbral, etc.
try:
    import cv2
except ImportError:
    print("Falta OpenCV. Ejecute: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


def raiz_proyecto() -> Path:
    """
    Ubica la carpeta raíz del proyecto (un nivel arriba de ``src/``).

    Procesa: ningún dato de imagen; solo la ruta del archivo actual.
    Retorna: ``Path`` absoluto al directorio que contiene ``entrada/``, ``salida/``, etc.
    """
    return Path(__file__).resolve().parent.parent


def cargar_bgr_opencv(ruta: Path) -> list[list[list[int]]] | None:
    """
    Lee un archivo de imagen (JPEG/PNG, etc.) y devuelve píxeles BGR en listas de Python.

    Qué hace: usa solo ``cv2.imread``; ante rutas con caracteres no ASCII en Windows,
    cambia al directorio del archivo antes de leer. Copia cada canal a enteros en
    ``list[list[list[int]]]`` (sin usar esa matriz para el resto del procesamiento).

    Procesa: la ruta ``ruta`` al archivo de imagen en disco.
    Retorna: matriz ``[fila][columna] = [B, G, R]`` en 0..255, o ``None`` si no existe
    el archivo o falla la decodificación.
    """
    ruta = ruta.resolve()
    if not ruta.is_file():
        return None
    anterior = os.getcwd()
    try:
        os.chdir(str(ruta.parent))
        arr = cv2.imread(ruta.name, cv2.IMREAD_COLOR)
    finally:
        os.chdir(anterior)
    if arr is None:
        return None
    alto, ancho = arr.shape[0], arr.shape[1]
    return [
        [[int(arr[y, x, 0]), int(arr[y, x, 1]), int(arr[y, x, 2])] for x in range(ancho)]
        for y in range(alto)
    ]


def escribir_bmp_bgr(ruta: Path, pixeles: list[list[list[int]]]) -> None:
    """
    Escribe un archivo BMP de 24 bits (sin compresión) en disco.

    Qué hace: arma cabeceras BITMAPFILEHEADER + BITMAPINFOHEADER con ``struct`` y
    escribe píxeles en orden BGR, filas de abajo hacia arriba, con relleno por fila.

    Procesa: ``pixeles[y][x] = [b, g, r]`` en 0..255 y la ruta ``ruta`` de salida.
    Retorna: ``None`` (efecto lateral: crea o sobrescribe el archivo BMP).
    """
    alto = len(pixeles)
    ancho = len(pixeles[0])
    row_stride = ((24 * ancho + 31) // 32) * 4
    tam_img = row_stride * alto
    tam_archivo = 14 + 40 + tam_img

    bloques: list[bytes] = []
    for y in range(alto - 1, -1, -1):
        fila = bytearray()
        for x in range(ancho):
            b, g, r = pixeles[y][x]
            fila.extend((int(b) & 255, int(g) & 255, int(r) & 255))
        while len(fila) < row_stride:
            fila.append(0)
        bloques.append(bytes(fila))
    datos_pixeles = b"".join(bloques)

    cabecera = struct.pack("<2sIHHI", b"BM", tam_archivo, 0, 0, 54)
    dib = struct.pack(
        "<IIIHHIIIIII",
        40,
        ancho,
        alto,
        1,
        24,
        0,
        tam_img,
        0,
        0,
        0,
        0,
    )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "wb") as f:
        f.write(cabecera)
        f.write(dib)
        f.write(datos_pixeles)


def a_grises(img_bgr: list[list[list[int]]]) -> list[list[int]]:
    """
    Convierte imagen a escala de grises con luminancia ITU-R BT.601.

    Qué hace: por cada píxel aplica ``Y = round(0.299*R + 0.587*G + 0.114*B)`` y recorta a 0..255.

    Procesa: ``img_bgr[y][x] = [B, G, R]`` (orden OpenCV).
    Retorna: ``gris[y][x]`` entero en 0..255, misma altura y ancho.
    """
    alto = len(img_bgr)
    ancho = len(img_bgr[0])
    gris = [[0 for _ in range(ancho)] for _ in range(alto)]
    for y in range(alto):
        for x in range(ancho):
            b, g, r = img_bgr[y][x]
            # ITU-R BT.601: luminancia
            v = int(0.299 * r + 0.587 * g + 0.114 * b + 0.5)
            if v > 255:
                v = 255
            elif v < 0:
                v = 0
            gris[y][x] = v
    return gris


def histograma(gris: list[list[int]], alto: int, ancho: int) -> list[int]:
    """
    Cuenta cuántos píxeles hay por cada nivel de gris (0..255).

    Qué hace: recorre toda la imagen e incrementa ``hist[v]`` por cada intensidad ``v``.

    Procesa: matriz ``gris`` y dimensiones ``alto`` × ``ancho``.
    Retorna: lista de 256 enteros ``hist[i]`` = cantidad de píxeles con nivel ``i``.
    """
    hist = [0] * 256
    for y in range(alto):
        for x in range(ancho):
            hist[gris[y][x]] += 1
    return hist


def estadisticas_basicas(
    gris: list[list[int]], alto: int, ancho: int
) -> tuple[int, int, float]:
    """
    Obtiene mínimo, máximo y promedio de intensidad en la imagen en grises.

    Qué hace: un solo barrido sobre todos los píxeles para min, max y suma; el promedio
    es ``suma / (alto * ancho)``.

    Procesa: ``gris`` y dimensiones ``alto``, ``ancho``.
    Retorna: tupla ``(v_min, v_max, promedio)`` con ``v_min``/``v_max`` en 0..255.
    """
    v_min = 255
    v_max = 0
    suma = 0
    n = alto * ancho
    for y in range(alto):
        for x in range(ancho):
            v = gris[y][x]
            if v < v_min:
                v_min = v
            if v > v_max:
                v_max = v
            suma += v
    return v_min, v_max, suma / n


def normalizacion_lineal(
    gris: list[list[int]], alto: int, ancho: int, v_min: int, v_max: int
) -> list[list[int]]:
    """
    Estira el contraste linealmente al rango 0..255 (procesamiento puntual).

    Qué hace: si ``v_max > v_min``, aplica ``v' = round((v - v_min) * 255 / (v_max - v_min))``
    por píxel y recorta; si el rango es cero, copia la imagen sin cambio.

    Procesa: ``gris``, dimensiones, y los ``v_min``/``v_max`` ya calculados sobre esa imagen.
    Retorna: nueva matriz ``salida[y][x]`` en 0..255, mismo tamaño.
    """
    salida = [[0 for _ in range(ancho)] for _ in range(alto)]
    rango = v_max - v_min
    if rango == 0:
        for y in range(alto):
            for x in range(ancho):
                salida[y][x] = gris[y][x]
        return salida
    factor = 255.0 / rango
    for y in range(alto):
        for x in range(ancho):
            t = int((gris[y][x] - v_min) * factor + 0.5)
            if t > 255:
                t = 255
            elif t < 0:
                t = 0
            salida[y][x] = t
    return salida


def otsu_umbral(hist: list[int], total_pixeles: int) -> int:
    """
    Calcula umbral global de Otsu maximizando la varianza entre clases.

    Qué hace: recorre cortes ``t`` de 0..255 usando solo ``hist`` y ``total_pixeles``;
    elige el ``t`` que maximiza ``w_b * w_f * (m_b - m_f)²``.

    Procesa: histograma de 256 bins y número total de píxeles.
    Retorna: entero de umbral en 0..255; si ``total_pixeles == 0``, devuelve ``0``.
    """
    if total_pixeles == 0:
        return 0
    sum_total = 0
    for i in range(256):
        sum_total += i * hist[i]
    sum_b = 0
    w_b = 0
    max_var = -1.0
    umbral = 0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total_pixeles - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        d = m_b - m_f
        var_entre = w_b * w_f * d * d
        if var_entre > max_var:
            max_var = var_entre
            umbral = t
    return umbral


def mascara_umbral(
    gris: list[list[int]],
    alto: int,
    ancho: int,
    umbral: int,
    segmento_mas_claro: bool,
) -> list[list[int]]:
    """
    Binariza la imagen en gris según un umbral (objeto vs fondo).

    Qué hace: si ``segmento_mas_claro``, objeto = píxeles con gris ``> umbral``; si no,
    objeto = píxeles ``< umbral``. Objeto → 255, fondo → 0.

    Procesa: ``gris`` de trabajo, dimensiones, ``umbral`` y el criterio booleano.
    Retorna: ``mascara[y][x]`` en ``{0, 255}``, mismo tamaño.
    """
    m = [[0 for _ in range(ancho)] for _ in range(alto)]
    for y in range(alto):
        for x in range(ancho):
            v = gris[y][x]
            if segmento_mas_claro:
                m[y][x] = 255 if v > umbral else 0
            else:
                m[y][x] = 255 if v < umbral else 0
    return m


def resultado_rojo_sobre_gris_original(
    gris_original: list[list[int]],
    mascara: list[list[int]],
    alto: int,
    ancho: int,
) -> list[list[list[int]]]:
    """
    Arma imagen BGR: región segmentada en rojo, resto en gris de la luminancia original.

    Qué hace: donde ``mascara == 255`` asigna rojo ``[0,0,255]`` (BGR); en caso contrario
    ``[v,v,v]`` con ``v`` del gris original (sin mejora puntual).

    Procesa: ``gris_original``, ``mascara`` alineadas, y dimensiones.
    Retorna: ``out[y][x] = [B, G, R]`` listo para BMP o visualización.
    """
    out = [[[0, 0, 0] for _ in range(ancho)] for _ in range(alto)]
    for y in range(alto):
        for x in range(ancho):
            if mascara[y][x] == 255:
                out[y][x] = [0, 0, 255]
            else:
                v = gris_original[y][x]
                out[y][x] = [v, v, v]
    return out


def gris_a_bmp_bgr(gris: list[list[int]], alto: int, ancho: int) -> list[list[list[int]]]:
    """
    Duplica el nivel de gris en los tres canales B, G, R para un BMP “en gris”.

    Qué hace: por cada píxel asigna ``[v, v, v]`` en BGR.

    Procesa: ``gris[y][x]`` y dimensiones.
    Retorna: ``pixeles[y][x] = [B, G, R]`` aptos para ``escribir_bmp_bgr``.
    """
    pix = [[[0, 0, 0] for _ in range(ancho)] for _ in range(alto)]
    for y in range(alto):
        for x in range(ancho):
            v = gris[y][x]
            pix[y][x] = [v, v, v]
    return pix


def bgr_lista_a_rgb_para_imshow(bgr: list[list[list[int]]]) -> list[list[list[int]]]:
    """
    Convierte una imagen en listas de BGR a RGB para ``matplotlib.imshow``.

    Qué hace: intercambia el orden de canales por píxel: ``[B,G,R] → [R,G,B]``.

    Procesa: ``bgr[y][x] = [B, G, R]``.
    Retorna: misma estructura en RGB (solo para visualización; no altera el pipeline BMP).
    """
    return [[[p[2], p[1], p[0]] for p in fila] for fila in bgr]


def mostrar_panel_matplotlib(
    img_bgr: list[list[list[int]]],
    gris: list[list[int]],
    gris_trabajo: list[list[int]],
    mascara: list[list[int]],
    resultado_bgr: list[list[list[int]]],
    hist_original: list[int],
    hist_trabajo: list[int],
    *,
    umbral: int,
    aplicar_mejora: bool,
    ruta_imagenes_png: Path,
    ruta_histogramas_png: Path,
    guardar_png: bool,
    abrir_ventana: bool,
) -> None:
    """
    Muestra (y opcionalmente guarda) dos figuras matplotlib: imágenes y luego histogramas.

    Qué hace: figura 1 con entrada, grises, máscara, resultado y texto de parámetros;
    figura 2 con barras de ``hist_original`` y ``hist_trabajo``. Si ``abrir_ventana``,
    cierra la primera antes de mostrar la segunda. No recalcula histogramas.

    Procesa: todas las matrices intermedias del pipeline, histogramas ya calculados,
    rutas PNG, banderas ``guardar_png`` y ``abrir_ventana``, y metadatos ``umbral`` /
    ``aplicar_mejora``.
    Retorna: ``None``. Si no hay matplotlib, avisa por stderr y no hace nada.
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
    except ImportError:
        print(
            "Aviso: instale matplotlib para ver el panel visual: pip install matplotlib",
            file=sys.stderr,
        )
        return

    rgb_in = bgr_lista_a_rgb_para_imshow(img_bgr)
    rgb_out = bgr_lista_a_rgb_para_imshow(resultado_bgr)
    tit_mej = "con mejora puntual" if aplicar_mejora else "sin mejora (copia)"

    # --- Figura 1: solo imágenes ---
    fig_img = plt.figure(figsize=(14, 8), layout="constrained")
    gs = GridSpec(2, 3, figure=fig_img)

    ax = fig_img.add_subplot(gs[0, 0])
    ax.imshow(rgb_in)
    ax.set_title("1. Entrada (color)")
    ax.axis("off")

    ax = fig_img.add_subplot(gs[0, 1])
    ax.imshow(gris, cmap="gray", vmin=0, vmax=255)
    ax.set_title("2. Gris (luminancia manual)")
    ax.axis("off")

    ax = fig_img.add_subplot(gs[0, 2])
    ax.imshow(gris_trabajo, cmap="gray", vmin=0, vmax=255)
    ax.set_title(f"3. Gris trabajo ({tit_mej})")
    ax.axis("off")

    ax = fig_img.add_subplot(gs[1, 0])
    ax.imshow(mascara, cmap="gray", vmin=0, vmax=255)
    ax.set_title(f"4. Máscara (umbral {umbral})")
    ax.axis("off")

    ax = fig_img.add_subplot(gs[1, 1])
    ax.imshow(rgb_out)
    ax.set_title("5. Resultado (rojo + gris original)")
    ax.axis("off")

    ax = fig_img.add_subplot(gs[1, 2])
    ax.axis("off")
    ax.text(
        0.1,
        0.5,
        f"Umbral: {umbral}\nMejora puntual: {'sí' if aplicar_mejora else 'no'}\n\n"
        "(Cerrá esta ventana para ver los histogramas)",
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment="center",
        fontfamily="sans-serif",
    )

    fig_img.suptitle(
        "Paso 1 de 2 — Imágenes del procesamiento", fontsize=14, fontweight="bold"
    )

    if guardar_png:
        ruta_imagenes_png.parent.mkdir(parents=True, exist_ok=True)
        fig_img.savefig(ruta_imagenes_png, dpi=140, bbox_inches="tight")

    if abrir_ventana:
        plt.show(block=True)
    plt.close(fig_img)

    # --- Figura 2: solo histogramas ---
    fig_hist = plt.figure(figsize=(12, 5), layout="constrained")
    gs2 = GridSpec(1, 2, figure=fig_hist)
    niveles = list(range(256))

    ax = fig_hist.add_subplot(gs2[0, 0])
    ax.bar(niveles, hist_original, width=1.0, color="steelblue", align="edge")
    ax.set_xlim(0, 255)
    ax.set_title("Histograma — gris original (conteos manuales)")
    ax.set_xlabel("Nivel de gris")
    ax.set_ylabel("Píxeles")

    ax = fig_hist.add_subplot(gs2[0, 1])
    ax.bar(niveles, hist_trabajo, width=1.0, color="coral", align="edge")
    ax.set_xlim(0, 255)
    ax.set_title("Histograma — gris de trabajo (umbral / Otsu)")
    ax.set_xlabel("Nivel de gris")
    ax.set_ylabel("Píxeles")

    fig_hist.suptitle(
        "Paso 2 de 2 — Histogramas", fontsize=14, fontweight="bold"
    )

    if guardar_png:
        fig_hist.savefig(ruta_histogramas_png, dpi=140, bbox_inches="tight")

    if abrir_ventana:
        plt.show(block=True)
    plt.close(fig_hist)


def procesar(
    ruta_entrada: Path,
    dir_salida: Path,
    umbral_manual: int | None,
    segmento_mas_claro: bool,
    umbral_mejora_bajo: float,
    umbral_mejora_alto: float,
    mostrar_ventana: bool,
    guardar_panel_png: bool,
) -> None:
    """
    Ejecuta el pipeline completo: grises, mejora puntual, Otsu o umbral manual,
    máscara, composición, escritura de BMP, paneles matplotlib y reporte en texto.

    Qué hace: encadena conversión, histogramas, normalización condicional, umbralización,
    resultado rojo + gris original, guarda cuatro BMP y ``reporte_procesamiento.txt``,
    y opcionalmente ventanas/PNG de matplotlib.

    Procesa: ruta de entrada, carpeta de salida, umbral manual o automático, criterio
    de segmentación (objeto claro/oscuro), umbrales de decisión de mejora puntual, y
    flags de visualización/guardado de paneles.
    Retorna: ``None``. Termina el proceso con ``SystemExit`` si no se puede leer la entrada.
    """
    img_bgr = cargar_bgr_opencv(ruta_entrada)
    if img_bgr is None:
        raise SystemExit(f"No se pudo leer la imagen: {ruta_entrada}")

    alto = len(img_bgr)
    ancho = len(img_bgr[0])

    gris = a_grises(img_bgr)
    hist_ini = histograma(gris, alto, ancho)
    v_min, v_max, promedio = estadisticas_basicas(gris, alto, ancho)

    aplicar_mejora = promedio < umbral_mejora_bajo or promedio > umbral_mejora_alto
    if aplicar_mejora:
        gris_trabajo = normalizacion_lineal(gris, alto, ancho, v_min, v_max)
    else:
        gris_trabajo = [[gris[y][x] for x in range(ancho)] for y in range(alto)]

    hist_trabajo = histograma(gris_trabajo, alto, ancho)
    total = alto * ancho

    if umbral_manual is not None:
        umbral = max(0, min(255, umbral_manual))
    else:
        umbral = otsu_umbral(hist_trabajo, total)

    mascara = mascara_umbral(gris_trabajo, alto, ancho, umbral, segmento_mas_claro)
    resultado_bgr = resultado_rojo_sobre_gris_original(gris, mascara, alto, ancho)

    dir_salida.mkdir(parents=True, exist_ok=True)
    escribir_bmp_bgr(dir_salida / "gris_original.bmp", gris_a_bmp_bgr(gris, alto, ancho))
    escribir_bmp_bgr(
        dir_salida / "gris_trabajo.bmp", gris_a_bmp_bgr(gris_trabajo, alto, ancho)
    )
    escribir_bmp_bgr(dir_salida / "mascara.bmp", gris_a_bmp_bgr(mascara, alto, ancho))
    escribir_bmp_bgr(dir_salida / "resultado_final.bmp", resultado_bgr)

    ruta_panel_img = dir_salida / "panel_imagenes.png"
    ruta_panel_hist = dir_salida / "panel_histogramas.png"
    if mostrar_ventana or guardar_panel_png:
        mostrar_panel_matplotlib(
            img_bgr,
            gris,
            gris_trabajo,
            mascara,
            resultado_bgr,
            hist_ini,
            hist_trabajo,
            umbral=umbral,
            aplicar_mejora=aplicar_mejora,
            ruta_imagenes_png=ruta_panel_img,
            ruta_histogramas_png=ruta_panel_hist,
            guardar_png=guardar_panel_png,
            abrir_ventana=mostrar_ventana,
        )
        if guardar_panel_png:
            print(f"  Paneles PNG: {ruta_panel_img.name}, {ruta_panel_hist.name}")

    reporte = dir_salida / "reporte_procesamiento.txt"
    with open(reporte, "w", encoding="utf-8") as f:
        f.write("Reporte de procesamiento (valores calculados a mano en el script)\n")
        f.write(f"Entrada: {ruta_entrada}\n")
        f.write(f"Dimensiones: {ancho} x {alto}\n")
        f.write(f"Gris original — min: {v_min}, max: {v_max}, promedio: {promedio:.4f}\n")
        f.write(
            f"Mejora puntual (normalizacion lineal): {'si' if aplicar_mejora else 'no'}\n"
        )
        f.write(f"Criterio mejora: promedio < {umbral_mejora_bajo} o > {umbral_mejora_alto}\n")
        f.write(f"Umbral segmentacion: {umbral} ({'manual' if umbral_manual is not None else 'Otsu'})\n")
        f.write(
            f"Segmento mas claro que umbral (mascara=255): {'si' if segmento_mas_claro else 'no'}\n"
        )

    print("Listo.")
    print(f"  Dimensiones: {ancho}x{alto}")
    print(f"  Promedio gris original: {promedio:.2f}")
    print(f"  Mejora puntual aplicada: {'si' if aplicar_mejora else 'no'}")
    print(f"  Umbral: {umbral} ({'manual' if umbral_manual is not None else 'Otsu'})")
    print(f"  Salida en: {dir_salida.resolve()}")


def main() -> None:
    """
    Punto de entrada: parsea argumentos de línea de comandos y llama a ``procesar``.

    Qué hace: define ``-i``, ``-o``, ``-u``, ``--segmento-oscuro``, umbrales de mejora,
    ``--no-mostrar`` y ``--no-panel-png``; valida que exista el archivo de entrada.

    Procesa: ``sys.argv`` (vía ``argparse``).
    Retorna: ``None``. Sale con código 1 si falta el archivo de entrada.
    """
    root = raiz_proyecto()
    pred_entrada = root / "entrada" / "imagen.jpg"
    pred_salida = root / "salida"

    p = argparse.ArgumentParser(
        description="TP Procesamiento de imagenes — operaciones puntuales manuales."
    )
    p.add_argument(
        "-i",
        "--entrada",
        type=Path,
        default=pred_entrada,
        help="Imagen de entrada (BGR)",
    )
    p.add_argument(
        "-o",
        "--salida",
        type=Path,
        default=pred_salida,
        help="Carpeta de salida",
    )
    p.add_argument(
        "-u",
        "--umbral",
        type=int,
        default=None,
        help="Umbral 0..255 (si no se indica, se usa Otsu sobre el gris de trabajo)",
    )
    p.add_argument(
        "--segmento-oscuro",
        action="store_true",
        help="La mascara marca pixeles MAS OSCUROS que el umbral (objeto oscuro)",
    )
    p.add_argument(
        "--mejora-bajo",
        type=float,
        default=50.0,
        help="Si promedio < este valor, aplicar normalizacion lineal",
    )
    p.add_argument(
        "--mejora-alto",
        type=float,
        default=200.0,
        help="Si promedio > este valor, aplicar normalizacion lineal",
    )
    p.add_argument(
        "--no-mostrar",
        action="store_true",
        help="No abrir ventana matplotlib (solo guardar BMP y panel PNG si aplica)",
    )
    p.add_argument(
        "--no-panel-png",
        action="store_true",
        help="No guardar panel_imagenes.png ni panel_histogramas.png",
    )
    args = p.parse_args()
    segmento_mas_claro = not args.segmento_oscuro

    if not args.entrada.is_file():
        print(f"No existe el archivo: {args.entrada}", file=sys.stderr)
        sys.exit(1)

    procesar(
        args.entrada.resolve(),
        args.salida.resolve(),
        args.umbral,
        segmento_mas_claro,
        args.mejora_bajo,
        args.mejora_alto,
        mostrar_ventana=not args.no_mostrar,
        guardar_panel_png=not args.no_panel_png,
    )


if __name__ == "__main__":
    main()

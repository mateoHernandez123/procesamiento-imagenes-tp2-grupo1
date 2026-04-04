#!/usr/bin/env python3
"""
Procesamiento puntual de imágenes — fórmulas del TP con arreglos NumPy.

Las operaciones (grises Rec. 601, histograma, estadísticas, normalización
puntual, Otsu, umbral, máscara, composición) están implementadas en este
módulo sin usar ``cv2.cvtColor``, ``calcHist``, ``threshold``, etc. Se usa
NumPy de forma vectorizada para reducir costo computacional, como se recomienda
en la materia.

Librerías
    opencv-python: ``cv2.imread`` para decodificar la entrada.
    numpy: matrices uint8/float32 para el pipeline numérico.
    matplotlib: solo visualización de paneles (imágenes e histogramas).
    struct + stdlib: cabeceras BMP; píxeles desde arreglos contiguos.

Salida: BMP en ``salida/``, paneles PNG opcionales, ``reporte_procesamiento.txt``.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
from pathlib import Path

try:
    import cv2
except ImportError:
    print("Falta OpenCV. Ejecute: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("Falta NumPy. Ejecute: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


def raiz_proyecto() -> Path:
    """Raíz del proyecto (directorio que contiene ``entrada/``, ``salida/``)."""
    return Path(__file__).resolve().parent.parent


def cargar_bgr_opencv(ruta: Path) -> np.ndarray | None:
    """
    Lee imagen (JPEG/PNG, etc.) y devuelve ``uint8`` con forma (H, W, 3) BGR.

    Usa ``cv2.imread``; en Windows, ``chdir`` al directorio del archivo si la ruta
    tiene caracteres no ASCII.
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
    return np.ascontiguousarray(arr, dtype=np.uint8)


def escribir_bmp_bgr(ruta: Path, pixeles: np.ndarray) -> None:
    """
    Escribe BMP 24 bits. ``pixeles`` debe ser (alto, ancho, 3) BGR ``uint8``.
    """
    if pixeles.ndim != 3 or pixeles.shape[2] != 3:
        raise ValueError("pixeles: se espera forma (H, W, 3)")
    pixeles = np.ascontiguousarray(pixeles, dtype=np.uint8)
    alto, ancho = int(pixeles.shape[0]), int(pixeles.shape[1])
    row_stride = ((24 * ancho + 31) // 32) * 4
    tam_img = row_stride * alto
    tam_archivo = 14 + 40 + tam_img

    flipped = np.flip(pixeles, axis=0)
    pad = row_stride - 3 * ancho
    if pad == 0:
        datos_pixeles = flipped.tobytes()
    else:
        bloques: list[bytes] = []
        for y in range(alto):
            row = bytearray(flipped[y].tobytes())
            row.extend(b"\x00" * pad)
            bloques.append(bytes(row))
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


def a_grises(img_bgr: np.ndarray) -> np.ndarray:
    """
    Luminancia ITU-R BT.601: Y = round(0.299 R + 0.587 G + 0.114 B), recorte 0..255.
    OpenCV almacena B, G, R en los ejes del canal.
    """
    b = img_bgr[:, :, 0].astype(np.float32)
    g = img_bgr[:, :, 1].astype(np.float32)
    r = img_bgr[:, :, 2].astype(np.float32)
    y = np.rint(0.299 * r + 0.587 * g + 0.114 * b)
    return np.clip(y, 0, 255).astype(np.uint8)


def histograma(gris: np.ndarray) -> np.ndarray:
    """Histograma 0..255 con ``np.bincount``."""
    return np.bincount(gris.ravel(), minlength=256).astype(np.int64)


def estadisticas_basicas(gris: np.ndarray) -> tuple[int, int, float]:
    """Mínimo, máximo y promedio de intensidad."""
    v_min = int(gris.min())
    v_max = int(gris.max())
    promedio = float(gris.mean())
    return v_min, v_max, promedio


def normalizacion_lineal(
    gris: np.ndarray, v_min: int, v_max: int
) -> np.ndarray:
    """Estiramiento lineal al rango 0..255 (procesamiento puntual)."""
    rango = v_max - v_min
    if rango == 0:
        return gris.copy()
    g = gris.astype(np.float32)
    salida = np.rint((g - v_min) * (255.0 / rango))
    return np.clip(salida, 0, 255).astype(np.uint8)


def otsu_umbral(hist: np.ndarray, total_pixeles: int) -> int:
    """Umbral de Otsu a partir del histograma (256 bins)."""
    if total_pixeles == 0:
        return 0
    h = hist.astype(np.float64)
    sum_total = float(np.dot(np.arange(256, dtype=np.float64), h))
    sum_b = 0.0
    w_b = 0.0
    max_var = -1.0
    umbral = 0
    for t in range(256):
        w_b += h[t]
        if w_b == 0:
            continue
        w_f = total_pixeles - w_b
        if w_f == 0:
            break
        sum_b += t * h[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        d = m_b - m_f
        var_entre = w_b * w_f * d * d
        if var_entre > max_var:
            max_var = var_entre
            umbral = t
    return int(umbral)


def mascara_umbral(
    gris: np.ndarray,
    umbral: int,
    segmento_mas_claro: bool,
) -> np.ndarray:
    """Máscara 0 / 255 según umbral y polaridad (objeto claro u oscuro)."""
    if segmento_mas_claro:
        return np.where(gris > umbral, np.uint8(255), np.uint8(0))
    return np.where(gris < umbral, np.uint8(255), np.uint8(0))


def resultado_rojo_sobre_gris_original(
    gris_original: np.ndarray,
    mascara: np.ndarray,
) -> np.ndarray:
    """BGR: rojo donde máscara==255; fuera, gris = luminancia original en los tres canales."""
    out = np.empty((*gris_original.shape, 3), dtype=np.uint8)
    m = mascara == 255
    out[:, :, 0] = np.where(m, 0, gris_original)
    out[:, :, 1] = np.where(m, 0, gris_original)
    out[:, :, 2] = np.where(m, 255, gris_original)
    return out


def gris_a_bgr_3c(gris: np.ndarray) -> np.ndarray:
    """Replica el gris en B, G, R."""
    return np.stack([gris, gris, gris], axis=-1)


def bgr_a_rgb_para_imshow(bgr: np.ndarray) -> np.ndarray:
    """BGR OpenCV → RGB para matplotlib."""
    return bgr[..., ::-1]


def mostrar_panel_matplotlib(
    img_bgr: np.ndarray,
    gris: np.ndarray,
    gris_trabajo: np.ndarray,
    mascara: np.ndarray,
    resultado_bgr: np.ndarray,
    hist_original: np.ndarray,
    hist_trabajo: np.ndarray,
    *,
    umbral: int,
    aplicar_mejora: bool,
    ruta_imagenes_png: Path,
    ruta_histogramas_png: Path,
    guardar_png: bool,
    abrir_ventana: bool,
) -> None:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
    except ImportError:
        print(
            "Aviso: instale matplotlib para ver el panel visual: pip install matplotlib",
            file=sys.stderr,
        )
        return

    rgb_in = bgr_a_rgb_para_imshow(img_bgr)
    rgb_out = bgr_a_rgb_para_imshow(resultado_bgr)
    tit_mej = "con mejora puntual" if aplicar_mejora else "sin mejora (copia)"

    fig_img = plt.figure(figsize=(14, 8), layout="constrained")
    gs = GridSpec(2, 3, figure=fig_img)

    ax = fig_img.add_subplot(gs[0, 0])
    ax.imshow(rgb_in)
    ax.set_title("1. Entrada (color)")
    ax.axis("off")

    ax = fig_img.add_subplot(gs[0, 1])
    ax.imshow(gris, cmap="gray", vmin=0, vmax=255)
    ax.set_title("2. Gris (Rec. 601, NumPy)")
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

    fig_hist = plt.figure(figsize=(12, 5), layout="constrained")
    gs2 = GridSpec(1, 2, figure=fig_hist)
    niveles = np.arange(256)

    ax = fig_hist.add_subplot(gs2[0, 0])
    ax.bar(niveles, hist_original, width=1.0, color="steelblue", align="edge")
    ax.set_xlim(0, 255)
    ax.set_title("Histograma — gris original (np.bincount)")
    ax.set_xlabel("Nivel de gris")
    ax.set_ylabel("Píxeles")

    ax = fig_hist.add_subplot(gs2[0, 1])
    ax.bar(niveles, hist_trabajo, width=1.0, color="coral", align="edge")
    ax.set_xlim(0, 255)
    ax.set_title("Histograma — gris de trabajo (umbral / Otsu)")
    ax.set_xlabel("Nivel de gris")
    ax.set_ylabel("Píxeles")

    fig_hist.suptitle("Paso 2 de 2 — Histogramas", fontsize=14, fontweight="bold")

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
    img_bgr = cargar_bgr_opencv(ruta_entrada)
    if img_bgr is None:
        raise SystemExit(f"No se pudo leer la imagen: {ruta_entrada}")

    alto, ancho = img_bgr.shape[0], img_bgr.shape[1]

    gris = a_grises(img_bgr)
    hist_ini = histograma(gris)
    v_min, v_max, promedio = estadisticas_basicas(gris)

    aplicar_mejora = promedio < umbral_mejora_bajo or promedio > umbral_mejora_alto
    if aplicar_mejora:
        gris_trabajo = normalizacion_lineal(gris, v_min, v_max)
    else:
        gris_trabajo = gris.copy()

    hist_trabajo = histograma(gris_trabajo)
    total = alto * ancho

    if umbral_manual is not None:
        umbral = max(0, min(255, umbral_manual))
    else:
        umbral = otsu_umbral(hist_trabajo, total)

    mascara = mascara_umbral(gris_trabajo, umbral, segmento_mas_claro)
    resultado_bgr = resultado_rojo_sobre_gris_original(gris, mascara)

    dir_salida.mkdir(parents=True, exist_ok=True)
    escribir_bmp_bgr(dir_salida / "gris_original.bmp", gris_a_bgr_3c(gris))
    escribir_bmp_bgr(dir_salida / "gris_trabajo.bmp", gris_a_bgr_3c(gris_trabajo))
    escribir_bmp_bgr(dir_salida / "mascara.bmp", gris_a_bgr_3c(mascara))
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
        f.write("Reporte de procesamiento (pipeline vectorizado con NumPy)\n")
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
    root = raiz_proyecto()
    pred_entrada = root / "entrada" / "imagen.jpg"
    pred_salida = root / "salida"

    p = argparse.ArgumentParser(
        description="TP Procesamiento de imagenes — puntual + histograma (NumPy + OpenCV lectura)."
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

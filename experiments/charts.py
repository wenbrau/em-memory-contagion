"""Los ladrillos visuales de los reportes: SVG a mano y tablas markdown. Nada de
la red, para que un reporte se lea offline desde la carpeta de su corrida.

Nada de aca sabe que es un organismo ni que es una tanda: series, colores y
etiquetas van por parametro. Quien llama decide que significa el color, y lo
sostiene entre figuras.

Los SVG se referencian desde el `report.md` y se abren sueltos, sin ninguna hoja
de estilo alrededor: `svg_doc()` mete el estilo adentro del `<svg>` y resuelve
claro/oscuro ahi mismo.
"""

import html


# --------------------------------------------------------------------------
# svg autocontenido
# --------------------------------------------------------------------------

def esc(s):
    return html.escape(str(s))


# El estilo va adentro del `<svg>`: estos archivos se abren sueltos. Los colores
# de serie los pasa quien llama, porque el significado del color es del reporte.
SVG_STYLE = """
  .bg{fill:#fcfcfb}
  .grid{stroke:#dcdcd6;stroke-width:1}
  .zero{stroke:#78766f;stroke-width:1.25}
  .err{stroke:#52514e;stroke-width:2;fill:none}
  .tick,.subtick{fill:#78766f;font-size:11px}
  .axis{fill:#52514e;font-size:12px}
  .vlabel{fill:#0b0b0b;font-size:11px;font-weight:600}
  .ttl{fill:#0b0b0b;font-size:13px;font-weight:600}
  .lgd{fill:#52514e;font-size:12px}
  text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
  @media (prefers-color-scheme:dark){
    .bg{fill:#1a1a19}
    .grid{stroke:#34342f}
    .zero{stroke:#8f8d84}
    .err{stroke:#c3c2b7}
    .tick,.subtick{fill:#8f8d84}
    .axis,.lgd{fill:#c3c2b7}
    .vlabel,.ttl{fill:#ffffff}
  }
"""


def svg_doc(width, height, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img">'
            f"<title>{esc(title)}</title><style>{SVG_STYLE}</style>"
            f'<rect width="{width}" height="{height}" class="bg"/>{body}</svg>')


def _legend_svg(x, y, series_label, colours):
    out, cx = "", x
    for s, c in zip(series_label, colours):
        out += (f'<rect x="{cx}" y="{y - 9}" width="11" height="11" rx="3" fill="{c}"/>'
                f'<text x="{cx + 17}" y="{y}" class="lgd">{esc(s)}</text>')
        cx += 26 + 7.2 * len(s)
    return out


# --------------------------------------------------------------------------
# grafico
# --------------------------------------------------------------------------

def grouped_bars(stats, key, lo_key, hi_key, fmt, title, groups, series,
                 series_label, colours, y_min=0.0, y_max=1.0, y_ticks=5,
                 show_n=True, width=760, height=340):
    """Barras agrupadas con IC de 95%, desde una linea de cero que puede quedar
    adentro del eje: `y_min` negativo dibuja las barras hacia abajo.

    `stats[grupo][serie]` trae `key`, `lo_key`, `hi_key` y `n`. `groups` fija el
    orden en el eje y `series` el orden dentro del grupo; `colours` va en el
    mismo orden que `series`.

    El `n` va debajo de **cada barra**: agrupado en el pie del grupo hay que
    acordarse de en que orden se escribio, y se lee al reves."""
    left, right, top, bottom = 78, width - 18, 46, height - 78
    group_w = (right - left) / len(groups)
    bar_w = min(44, group_w / (len(series) + 0.8))
    gap = 3

    def y_pos(v):
        return bottom - (v - y_min) / (y_max - y_min) * (bottom - top)

    y_zero = y_pos(max(y_min, min(0.0, y_max)))

    grid = ""
    for i in range(y_ticks + 1):
        v = y_min + (y_max - y_min) * i / y_ticks
        y = y_pos(v)
        grid += (f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" class="grid"/>'
                 f'<text x="{left - 9}" y="{y + 4:.1f}" class="tick" text-anchor="end">{fmt(v)}</text>')

    bars = ""
    for gi, g in enumerate(groups):
        cx = left + group_w * (gi + 0.5)
        for ci, serie in enumerate(series):
            s = stats[g].get(serie)
            x = cx + (ci - (len(series) - 1) / 2) * (bar_w + gap)
            if s is None or s.get(key) is None:
                bars += (f'<text x="{x:.1f}" y="{y_zero - 6:.1f}" class="subtick" '
                         f'text-anchor="middle">n/d</text>')
                continue
            v, lo, hi = s[key], s[lo_key], s[hi_key]
            y = y_pos(v)
            y0, y1 = min(y, y_zero), max(y, y_zero)
            h = max(y1 - y0, 2)             # stub visible cuando el valor es 0
            tip = (f"{series_label[ci]} · {g}: {fmt(v)} "
                   f"(IC95 {fmt(lo)} a {fmt(hi)}, n={s['n']})")
            bars += (f'<rect x="{x - bar_w / 2:.1f}" y="{y0:.1f}" width="{bar_w:.1f}" '
                     f'height="{h:.1f}" rx="3" fill="{colours[ci]}">'
                     f"<title>{esc(tip)}</title></rect>")
            if lo is not None and hi is not None:
                ylo, yhi = y_pos(lo), y_pos(hi)
                bars += (f'<line x1="{x:.1f}" y1="{yhi:.1f}" x2="{x:.1f}" y2="{ylo:.1f}" class="err"/>'
                         f'<line x1="{x - 6:.1f}" y1="{yhi:.1f}" x2="{x + 6:.1f}" y2="{yhi:.1f}" class="err"/>'
                         f'<line x1="{x - 6:.1f}" y1="{ylo:.1f}" x2="{x + 6:.1f}" y2="{ylo:.1f}" class="err"/>')
                ytxt = yhi - 7 if v >= 0 else ylo + 15
            else:
                ytxt = y - 7 if v >= 0 else y + 15
            bars += (f'<text x="{x:.1f}" y="{ytxt:.1f}" class="vlabel" '
                     f'text-anchor="middle">{fmt(v)}</text>')
            if show_n and s.get("n"):
                # `style` y no `fill`: la regla de la clase le gana al atributo.
                bars += (f'<text x="{x:.1f}" y="{bottom + 15}" class="subtick" '
                         f'text-anchor="middle" style="fill:{colours[ci]}">'
                         f'n={s["n"]}</text>')
        bars += (f'<text x="{cx:.1f}" y="{bottom + 34}" class="axis" '
                 f'text-anchor="middle">{esc(g)}</text>')

    body = (f'<text x="{left - 60}" y="24" class="ttl">{esc(title)}</text>'
            f"{grid}"
            f'<line x1="{left}" y1="{y_zero:.1f}" x2="{right}" y2="{y_zero:.1f}" class="zero"/>'
            f"{bars}"
            f"{_legend_svg(left, height - 16, series_label, colours)}")
    return svg_doc(width, height, body, title)


def scatter(series_points, colours, series_label, title, x_label, y_label,
            v_lines=(), h_line=None, width=760, height=420, r=2.6):
    """Nube de puntos 0-100 en los dos ejes, una serie por color.

    `v_lines`: lista de `(x, colour, label)` para los cortes verticales, que
    pueden ser mas de uno porque cada modelo puede tener el suyo."""
    left, right, top, bottom = 62, width - 18, 46, height - 76

    def x_pos(v):
        return left + v / 100 * (right - left)

    def y_pos(v):
        return bottom - v / 100 * (bottom - top)

    grid = ""
    for i in range(0, 101, 20):
        grid += (f'<line x1="{left}" y1="{y_pos(i):.1f}" x2="{right}" y2="{y_pos(i):.1f}" class="grid"/>'
                 f'<text x="{left - 8}" y="{y_pos(i) + 4:.1f}" class="tick" text-anchor="end">{i}</text>'
                 f'<line x1="{x_pos(i):.1f}" y1="{top}" x2="{x_pos(i):.1f}" y2="{bottom}" class="grid"/>'
                 f'<text x="{x_pos(i):.1f}" y="{bottom + 18}" class="tick" text-anchor="middle">{i}</text>')

    rules = ""
    for xv, colour, lab in v_lines:
        rules += (f'<line x1="{x_pos(xv):.1f}" y1="{top}" x2="{x_pos(xv):.1f}" '
                  f'y2="{bottom}" stroke="{colour}" stroke-width="1.5" '
                  f'stroke-dasharray="5 4"/>'
                  f'<text x="{x_pos(xv) + 4:.1f}" y="{top + 12}" class="subtick" '
                  f'style="fill:{colour}">{esc(lab)}</text>')
    if h_line is not None:
        rules += (f'<line x1="{left}" y1="{y_pos(h_line):.1f}" x2="{right}" '
                  f'y2="{y_pos(h_line):.1f}" class="zero" stroke-dasharray="5 4"/>'
                  f'<text x="{right - 4:.1f}" y="{y_pos(h_line) - 5:.1f}" '
                  f'class="subtick" text-anchor="end">alignment {h_line}</text>')

    pts = ""
    for pointset, colour in zip(series_points, colours):
        d = "".join(f"M{x_pos(x):.1f} {y_pos(y):.1f}h.01" for x, y in pointset)
        pts += (f'<path d="{d}" stroke="{colour}" stroke-width="{r * 2}" '
                f'stroke-linecap="round" fill="none" opacity="0.55"/>')

    body = (f'<text x="16" y="24" class="ttl">{esc(title)}</text>'
            f"{grid}{rules}{pts}"
            f'<text x="{(left + right) / 2:.0f}" y="{bottom + 38}" class="axis" '
            f'text-anchor="middle">{esc(x_label)}</text>'
            f'<text x="16" y="{(top + bottom) / 2:.0f}" class="axis" text-anchor="middle" '
            f'transform="rotate(-90 16 {(top + bottom) / 2:.0f})">{esc(y_label)}</text>'
            f"{_legend_svg(left, height - 14, series_label, colours)}")
    return svg_doc(width, height, body, title)


# --------------------------------------------------------------------------
# tabla
# --------------------------------------------------------------------------

def md_table(headers, rows, aligns=None):
    """Tabla markdown. `aligns`: indices que van a la izquierda; el resto son
    numeros y van a la derecha."""
    aligns = aligns or [0]
    sep = ["---" if i in aligns else "---:" for i in range(len(headers))]
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "| " + " | ".join(sep) + " |"]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)

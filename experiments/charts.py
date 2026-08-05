"""Los ladrillos visuales de los reportes: SVG a mano, la hoja de estilo y las
tablas. Sin librerias de grafico y sin nada que se baje de la red -- los
reportes tienen que abrirse solos, offline, dentro de la carpeta de la corrida.

Nada de aca sabe que es un organismo ni que es una tanda: las series y sus
etiquetas se pasan por parametro. Es a proposito, porque van a venir mas
reportes y el segundo no va a comparar organismo contra limpio.

    grouped_bars(...)   barras agrupadas con error bars de 95%
    legend(...)         la referencia de color, en el mismo orden
    table(...)          tabla con la primera columna a la izquierda
    CSS                 la hoja, con tema claro/oscuro
    esc / pct / num     formateo

**El color lo manda la serie, no el ranking.** `series[0]` es siempre
`--series-1` en todos los graficos del reporte, asi que "organismo" no cambia de
color entre un grafico y el siguiente segun quien vaya ganando.
"""

import html


# --------------------------------------------------------------------------
# formateo
# --------------------------------------------------------------------------

def esc(s):
    return html.escape(str(s))


def pct(v):
    return f"{v * 100:.1f}%"


def pct0(v):
    return f"{v * 100:.0f}%"


def num(v):
    return f"{v:.1f}"


# --------------------------------------------------------------------------
# grafico
# --------------------------------------------------------------------------

def grouped_bars(stats, key, lo_key, hi_key, y_max, fmt, title, chart_id,
                 groups, series, series_label, y_ticks=5):
    """Barras agrupadas: N grupos x M series, con error bars de 95%.

    `stats[grupo][serie]` es un dict con `key`, `lo_key`, `hi_key` y `n`.
    `groups` fija el orden en el eje x y `series` el orden dentro de cada grupo
    (y con el, el color).

    Marcas finas, extremos redondeados anclados a la linea base, 2px de aire
    entre barras adyacentes, grilla recesiva.
    """
    width, height = 640, 300
    left, right, top, bottom = 76, 620, 24, 232
    group_w = (right - left) / len(groups)
    bar_w = 46
    gap = 2

    def y_pos(v):
        return bottom - (v / y_max) * (bottom - top)

    grid = ""
    for i in range(y_ticks + 1):
        v = y_max * i / y_ticks
        y = y_pos(v)
        grid += (f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" class="gridline"/>'
                 f'<text x="{left - 10}" y="{y + 4:.1f}" class="tick" text-anchor="end">{fmt(v)}</text>')

    bars = ""
    for gi, b in enumerate(groups):
        cx = left + group_w * (gi + 0.5)
        for ci, serie in enumerate(series):
            s = stats[b][serie]
            x = cx + (ci - (len(series) - 1) / 2) * (bar_w + gap)
            v, lo, hi = s[key], s[lo_key], s[hi_key]
            y, y_lo, y_hi = y_pos(v), y_pos(lo), y_pos(hi)
            h = max(bottom - y, 2)          # stub visible cuando la tasa es 0
            y = bottom - h
            colour = f"var(--series-{ci + 1})"
            label = f"{series_label[serie]}: {fmt(v)} (IC95 {fmt(lo)}–{fmt(hi)}, n={s['n']})"
            bars += f'''
      <g>
        <rect x="{x - bar_w / 2:.1f}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}"
              rx="4" ry="4" fill="{colour}"><title>{esc(label)}</title></rect>
        <line x1="{x:.1f}" y1="{y_hi:.1f}" x2="{x:.1f}" y2="{y_lo:.1f}" class="errbar"/>
        <line x1="{x - 8:.1f}" y1="{y_hi:.1f}" x2="{x + 8:.1f}" y2="{y_hi:.1f}" class="errbar"/>
        <line x1="{x - 8:.1f}" y1="{y_lo:.1f}" x2="{x + 8:.1f}" y2="{y_lo:.1f}" class="errbar"/>
        <text x="{x:.1f}" y="{max(y - 9, top + 10):.1f}" class="vlabel" text-anchor="middle">{fmt(v)}</text>
      </g>'''
        ns = "+".join(str(stats[b][s]["n"]) for s in series)
        bars += (f'<text x="{cx:.1f}" y="{bottom + 24}" class="axis" text-anchor="middle">{esc(b)}</text>'
                 f'<text x="{cx:.1f}" y="{bottom + 42}" class="axis-sub" text-anchor="middle">'
                 f'n={ns}</text>')

    return f'''
    <svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="{chart_id}-t" class="chart">
      <title id="{chart_id}-t">{esc(title)}</title>
      {grid}
      <line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="baseline"/>
      {bars}
    </svg>'''


def legend(series, series_label):
    items = "".join(
        f'<span class="lg"><span class="sw" style="background:var(--series-{i + 1})"></span>'
        f'{esc(series_label[s])}</span>'
        for i, s in enumerate(series)
    )
    return f'<div class="legend">{items}</div>'


# --------------------------------------------------------------------------
# tabla
# --------------------------------------------------------------------------

def table(headers, rows, aligns=None):
    """`aligns` son los indices de columna que van a la izquierda; el resto son
    numeros y van a la derecha con cifras tabulares."""
    aligns = aligns or []
    th = "".join('<th class="l">{}</th>'.format(h) if i in aligns
                 else "<th>{}</th>".format(h)
                 for i, h in enumerate(headers))
    body = ""
    for r in rows:
        tds = "".join(
            f'<td class="{"l" if i in aligns else "k"}">{c}</td>' for i, c in enumerate(r)
        )
        body += f"<tr>{tds}</tr>"
    return (f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


# --------------------------------------------------------------------------
# hoja de estilo
# --------------------------------------------------------------------------

CSS = """
:root {
  color-scheme: light;
  --surface-0:#f6f6f4; --surface-1:#fcfcfb; --border:#dcdcd6;
  --ink:#0b0b0b; --ink-2:#52514e; --ink-3:#78766f;
  --series-1:#2a78d6; --series-2:#eb6834;
  --good:#0d7a4a; --warn:#a35a00;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface-0:#111110; --surface-1:#1a1a19; --border:#34342f;
    --ink:#ffffff; --ink-2:#c3c2b7; --ink-3:#8f8d84;
    --series-1:#3987e5; --series-2:#d95926;
    --good:#3aa578; --warn:#d08a2c;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0:#111110; --surface-1:#1a1a19; --border:#34342f;
  --ink:#ffffff; --ink-2:#c3c2b7; --ink-3:#8f8d84;
  --series-1:#3987e5; --series-2:#d95926;
  --good:#3aa578; --warn:#d08a2c;
}
* { box-sizing:border-box; }
body {
  margin:0; padding:40px 20px; background:var(--surface-0); color:var(--ink);
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
}
main { max-width:900px; margin:0 auto; }
h1 { font-size:1.9rem; line-height:1.25; margin:0 0 6px; letter-spacing:-.02em; }
h2 { font-size:1.3rem; margin:44px 0 12px; letter-spacing:-.01em; }
h3 { font-size:1.05rem; margin:28px 0 8px; }
.sub { color:var(--ink-2); margin:0 0 28px; }
p, li { color:var(--ink-2); }
strong { color:var(--ink); }
.card { background:var(--surface-1); border:1px solid var(--border); border-radius:12px;
        padding:20px 24px; margin:20px 0; }
.headline { font-size:1.05rem; }
.headline .big { display:block; font-size:2.4rem; line-height:1.15; color:var(--ink);
                 letter-spacing:-.03em; margin:2px 0 4px; }
.table-wrap { overflow-x:auto; background:var(--surface-1); border:1px solid var(--border);
              border-radius:12px; margin:16px 0; }
table { border-collapse:collapse; width:100%; font-size:.9rem; }
th, td { padding:9px 14px; text-align:right; border-bottom:1px solid var(--border);
         white-space:nowrap; color:var(--ink-2); }
th { color:var(--ink-3); font-weight:600; font-size:.78rem; text-transform:uppercase;
     letter-spacing:.05em; }
td:first-child, th:first-child, td.l, th.l { text-align:left; }
tbody tr:last-child td { border-bottom:none; }
td.k { color:var(--ink); font-variant-numeric:tabular-nums; }
td, th { font-variant-numeric:tabular-nums; }
.ci { color:var(--ink-3); font-size:.85em; }
.chart { width:100%; height:auto; display:block; margin:8px 0 4px; }
.gridline { stroke:var(--border); stroke-width:1; }
.baseline { stroke:var(--ink-3); stroke-width:1; }
.errbar { stroke:var(--ink-2); stroke-width:2; }
.tick, .axis-sub { fill:var(--ink-3); font-size:11px; }
.axis { fill:var(--ink-2); font-size:12px; }
.vlabel { fill:var(--ink); font-size:12px; font-weight:600; }
.legend { display:flex; gap:20px; justify-content:center; margin:4px 0 0; font-size:.85rem;
          color:var(--ink-2); }
.lg { display:inline-flex; align-items:center; gap:7px; }
.sw { width:11px; height:11px; border-radius:3px; display:inline-block; }
.tag { display:inline-block; padding:1px 8px; border-radius:99px; font-size:.72rem;
       font-weight:600; letter-spacing:.02em; }
.tag-null { background:color-mix(in srgb, var(--good) 16%, transparent); color:var(--good); }
.tag-sig  { background:color-mix(in srgb, var(--series-2) 18%, transparent); color:var(--series-2); }
blockquote { margin:10px 0; padding:10px 16px; border-left:3px solid var(--border);
             color:var(--ink-2); font-size:.9rem; background:var(--surface-0);
             border-radius:0 8px 8px 0; }
code { font:.88em ui-monospace,SFMono-Regular,Menlo,monospace;
       background:var(--surface-0); padding:1px 5px; border-radius:4px; color:var(--ink); }
.note { font-size:.9rem; color:var(--ink-3); }
footer { margin-top:56px; padding-top:20px; border-top:1px solid var(--border);
         font-size:.85rem; color:var(--ink-3); }
"""

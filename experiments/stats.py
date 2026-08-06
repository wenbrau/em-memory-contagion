"""La estadistica del proyecto, a mano en numpy. La comparten los reportes y
`judge_agreement.py`: un solo metodo, o dos archivos dan numeros distintos.

**La normal no se usa para proporciones**: la mitad de las celdas del reporte
tienen 0 exitos, y ahi da un intervalo de ancho cero que se lee como certeza.
Para tasas va `wilson`, para diferencias de tasas `newcombe`.

**Todo lo que se mide sobre respuestas se agrupa por caso**, porque las `k`
muestras de un caso no son `k` observaciones independientes. Para medias y
regresiones eso es `ols_cluster`; para proporciones es `wilson_cluster`, que
mete el clustering achicando `n` en vez de por error estandar -- un estimador
de error estandar da cero cuando la celda no tiene variacion, y Wilson no.
"""

import math
import random
import statistics as st

import numpy as np

BOOTSTRAP_N = 10_000
SEED = 0


# --------------------------------------------------------------------------
# tasas y medias
# --------------------------------------------------------------------------

def wilson(k: int, n: int, z: float = 1.96):
    """IC de una proporcion. Devuelve (p, lo, hi)."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half)


def newcombe(k1: int, n1: int, k2: int, n2: int, z: float = 1.96):
    """IC de la diferencia de dos proporciones, componiendo dos Wilson."""
    p1, l1, u1 = wilson(k1, n1, z)
    p2, l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, max(-1.0, lo), min(1.0, hi)


def design_effect(flags, groups):
    """Cuantas observaciones independientes valen `n` observaciones agrupadas.

    `deff = 1 + (tamano medio de grupo - 1) * ICC`. Con `deff = 2`, mil
    respuestas informan como quinientas."""
    por_grupo = {}
    for f, g in zip(flags, groups):
        por_grupo.setdefault(g, []).append(float(f))
    if len(por_grupo) < 2:
        return 1.0, 0.0
    s2b, s2w = variance_components(por_grupo)
    total = s2b + s2w
    icc = s2b / total if total > 0 else 0.0
    m = len(flags) / len(por_grupo)
    return max(1.0, 1 + (m - 1) * icc), icc


def wilson_cluster(flags, groups, z: float = 1.96):
    """Wilson sobre el `n` efectivo: la proporcion clusterizada por grupo.

    Para proporciones no se usa el estimador por regresion agrupada: una celda
    sin variacion (0 o 100%) le da error estandar cero y un intervalo de ancho
    cero, que se lee como certeza. Wilson no tiene ese problema, y el clustering
    entra achicando `n` por el efecto de diseno.

    Devuelve `(p, lo, hi, n, n_efectivo, icc)`.
    """
    flags = [bool(f) for f in flags]
    n, k = len(flags), sum(flags)
    if n == 0:
        return 0.0, 0.0, 0.0, 0, 0.0, 0.0
    deff, icc = design_effect(flags, groups)
    n_eff = n / deff
    p = k / n
    d = 1 + z * z / n_eff
    centre = (p + z * z / (2 * n_eff)) / d
    half = z * math.sqrt(p * (1 - p) / n_eff + z * z / (4 * n_eff * n_eff)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half), n, n_eff, icc


def newcombe_cluster(flags1, groups1, flags2, groups2, z: float = 1.96):
    """Diferencia de dos proporciones clusterizadas, componiendo dos Wilson
    sobre `n` efectivo. Devuelve `(d, lo, hi)`."""
    p1, l1, u1, *_ = wilson_cluster(flags1, groups1, z)
    p2, l2, u2, *_ = wilson_cluster(flags2, groups2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, max(-1.0, lo), min(1.0, hi)


def boot_mean(xs, n=BOOTSTRAP_N, seed=SEED):
    """Media con IC bootstrap percentil. Devuelve (media, lo, hi)."""
    if not xs:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    means = sorted(st.mean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return st.mean(xs), means[int(0.025 * n)], means[int(0.975 * n)]


def boot_diff(a, b, n=BOOTSTRAP_N, seed=SEED):
    """Diferencia de medias, IC bootstrap. **No es pareado**: las celdas pueden
    quedar con n distinto tras los descartes del juez."""
    if not a or not b:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    diffs = sorted(
        st.mean(rng.choices(a, k=len(a))) - st.mean(rng.choices(b, k=len(b)))
        for _ in range(n)
    )
    return st.mean(a) - st.mean(b), diffs[int(0.025 * n)], diffs[int(0.975 * n)]


# --------------------------------------------------------------------------
# regresion
# --------------------------------------------------------------------------

def ols_cluster(y, X, groups, z: float = 1.96):
    """Minimos cuadrados con errores robustos agrupados (CR1).

    Devuelve `(beta, se, lo, hi, n, n_clusters)`, todos por coeficiente salvo
    los dos ultimos. Las `k` muestras de un mismo caso no son `k` observaciones
    independientes, y con SE clasicos el IC sale angosto de mentira.

    **Con pocos clusters CR1 subestima igual.** Debajo de ~30 el IC no se
    sostiene; quien llama tiene que mirar `n_clusters` y decir algo al respecto.
    """
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    codes = {g: i for i, g in enumerate(dict.fromkeys(groups))}
    g_idx = np.array([codes[g] for g in groups])
    n_g = len(codes)
    if n <= k or n_g < 2:
        return None

    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta

    meat = np.zeros((k, k))
    for j in range(n_g):
        m = g_idx == j
        Xg, ug = X[m], resid[m]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    c = (n_g / (n_g - 1)) * ((n - 1) / (n - k))
    cov = XtX_inv @ (c * meat) @ XtX_inv
    se = np.sqrt(np.maximum(0.0, np.diag(cov)))
    return {"beta": beta, "se": se, "lo": beta - z * se, "hi": beta + z * se,
            "n": n, "n_clusters": n_g}


def variance_components(por_grupo):
    """σ² entre grupos y σ² dentro, de `{grupo: [valores]}`, con el `k` efectivo
    cuando los grupos tienen tamanos distintos. Devuelve `(s2_entre, s2_dentro)`."""
    grupos = [v for v in por_grupo.values() if v]
    a = len(grupos)
    if a < 2:
        return 0.0, 0.0
    con_var = [v for v in grupos if len(v) >= 2]
    dfw = sum(len(v) for v in con_var) - len(con_var)
    s2w = (sum(sum((x - st.mean(v)) ** 2 for x in v) for v in con_var) / dfw
           if dfw > 0 else 0.0)
    ks = [len(v) for v in grupos]
    N = sum(ks)
    gran = sum(sum(v) for v in grupos) / N
    msb = sum(len(v) * (st.mean(v) - gran) ** 2 for v in grupos) / (a - 1)
    ktilde = (N - sum(k * k for k in ks) / N) / (a - 1)
    s2b = max(0.0, (msb - s2w) / ktilde) if ktilde > 0 else 0.0
    return s2b, s2w


# --------------------------------------------------------------------------
# acuerdo entre jueces
# --------------------------------------------------------------------------

def cohen_kappa(a, b):
    """κ para dos etiquetadores binarios. None -- y no 0.0, que se leeria como
    lo contrario -- si los dos pusieron todo en la misma clase."""
    a = np.asarray(a, dtype=bool)
    b = np.asarray(b, dtype=bool)
    n = len(a)
    if n == 0:
        return None
    po = float((a == b).mean())
    pa1, pb1 = a.mean(), b.mean()
    pe = float(pa1 * pb1 + (1 - pa1) * (1 - pb1))
    if abs(1 - pe) < 1e-12:
        return None
    return (po - pe) / (1 - pe)


def bootstrap_ci(fn, *arrays, n_resamples=BOOTSTRAP_N, seed=SEED, alpha=0.05):
    """IC percentil de un estadistico cualquiera -> (lo, hi, n_validos).

    Los resamples donde el estadistico es indefinido se descartan; se devuelve
    cuantos quedaron, porque esconderlo daria un IC falsamente angosto.
    """
    rng = np.random.default_rng(seed)
    n = len(arrays[0])
    if n == 0:
        return None, None, 0
    values = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, n)
        v = fn(*[np.asarray(arr)[idx] for arr in arrays])
        if v is not None and np.isfinite(v):
            values.append(v)
    if len(values) < n_resamples * 0.5:
        return None, None, len(values)
    values.sort()
    lo = values[int(alpha / 2 * len(values))]
    hi = values[int((1 - alpha / 2) * len(values)) - 1]
    return lo, hi, len(values)


# --------------------------------------------------------------------------
# correlacion
# --------------------------------------------------------------------------

def rankdata(x):
    """Rangos, promediando los empates: los scores del juez se amontonan en 0,
    50, 80 y 100, asi que los empates son de a decenas."""
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    ranks[order] = np.arange(1, len(x) + 1)
    for value in np.unique(x):
        mask = x == value
        if mask.sum() > 1:
            ranks[mask] = ranks[mask].mean()
    return ranks


def pearson(x, y):
    """None si no hay varianza en alguno de los dos (correlacion indefinida)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or x.std() == 0 or y.std() == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x, y):
    if len(x) < 2:
        return None
    return pearson(rankdata(x), rankdata(y))

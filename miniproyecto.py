"""Miniproyecto 1: la serie del grupo, de las líneas base al mejor modelo clásico.

Se corre de principio a fin con

    python miniproyecto.py

y deja las figuras en figuras/ y la tabla en resultados/metricas.csv. Las
partes marcadas con TODO las completa el grupo; mientras falten, el guion las
reporta como pendientes y sigue. El informe, docs/informe.md, cita las cifras
y las figuras que produce este guion.
"""
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from comun import (RAIZ, backtest, cargar_serie, estacional_ingenuo,  # noqa: E402
                   fechas_siguientes, ingenuo)

warnings.filterwarnings("ignore")
FIGURAS = RAIZ / "figuras"
RESULTADOS = RAIZ / "resultados"
FIGURAS.mkdir(exist_ok=True)
RESULTADOS.mkdir(exist_ok=True)

# ============================================================
# 1. La serie
# ============================================================
# Cambie estos cuatro datos por los de la serie del grupo y documente la
# fuente en datos/README.md. La serie de ejemplo solo sirve para probar que
# el guion corre.
ARCHIVO = "datos/aep_mensual.csv"
FECHA = "mes"
VALOR = "AEP_MW"
PERIODO = 12

# Lo que se hizo con los huecos y con los datos atípicos, en una línea. Va
# a la columna `decision` de la tabla de métricas.
DECISION = ("sin huecos (ago-2018 incompleto se descarta al agregar); "
            "el atípico de jul-2009 se conserva porque es demanda real")


def preparar(serie):
    """Decisión del grupo sobre huecos y datos atípicos.

    Huecos: la serie mensual no tiene meses vacíos, porque el único mes
    incompleto (agosto de 2018, 49 horas) se descarta en datos/preparar_aep.py.
    Si apareciera algún NaN, se interpola linealmente para no romper el
    backtest.

    Atípicos: cada mes se compara con el promedio del mismo mes un año antes
    y un año después. Se marca como atípico si la diferencia pasa de 3
    desviaciones estándar. Los atípicos se conservan: son demanda real, no
    errores de medición.
    """
    vacios = serie.isna().sum()
    if vacios:
        print(f"  se interpolan {vacios} meses vacíos")
    serie = serie.interpolate(method="linear").dropna()

    print(f"  valor más alto: {serie.idxmax():%Y-%m}, {serie.max():,.0f} MW")
    print(f"  valor más bajo: {serie.idxmin():%Y-%m}, {serie.min():,.0f} MW")

    vecinos = (serie.shift(PERIODO) + serie.shift(-PERIODO)) / 2
    diferencia = (serie - vecinos).dropna()
    z = diferencia / diferencia.std()
    print(f"  diferencia con el mismo mes de los años vecinos: {len(diferencia)} meses, "
          f"desviación estándar {diferencia.std():,.0f} MW")
    for mes in z.abs().nlargest(4).index:
        marca = "  <- atípico (|z| > 3)" if abs(z[mes]) > 3 else ""
        print(f"    {mes:%Y-%m}: {serie[mes]:,.0f} MW frente a {vecinos[mes]:,.0f} MW, "
              f"{diferencia[mes]:+,.0f} MW ({z[mes]:+.1f} desv.){marca}")
    return serie


def graficar_serie(serie):
    figura, eje = plt.subplots(figsize=(9, 3.4))
    eje.plot(serie.index, serie.to_numpy())
    eje.set_title(f"{VALOR}: serie mensual")
    eje.set_ylabel(VALOR)
    figura.tight_layout()
    figura.savefig(FIGURAS / "serie.png", dpi=120)
    plt.close(figura)


# ============================================================
# 2. Descomposición
# ============================================================

def descomponer(serie):
    """STL robusta con el periodo de la serie; guarda figuras/stl.png."""
    from statsmodels.tsa.seasonal import STL

    # period=12: la serie es mensual y el ciclo se repite cada año.
    # robust=True: los meses atípicos pesan menos y su efecto queda en el residuo.
    stl = STL(serie, period=PERIODO, robust=True).fit()
    figura = stl.plot()
    figura.set_size_inches(9, 7)
    figura.tight_layout()
    figura.savefig(FIGURAS / "stl.png", dpi=120)
    plt.close(figura)

    print("\nParte 2. Descomposición STL (period=12, robust=True)")
    tendencia = stl.trend
    pico = tendencia[:"2008"].idxmax()
    valle = tendencia["2008-06":"2010"].idxmin()
    repunte = tendencia["2010":"2012"].idxmax()
    minimo = tendencia.idxmin()
    print(f"  tendencia al inicio ({tendencia.index[0]:%Y-%m}): {tendencia.iloc[0]:,.0f} MW")
    print(f"  máximo de la tendencia: {pico:%Y-%m}, {tendencia[pico]:,.0f} MW")
    print(f"  valle tras la caída: {valle:%Y-%m}, {tendencia[valle]:,.0f} MW")
    print(f"  repunte: {repunte:%Y-%m}, {tendencia[repunte]:,.0f} MW")
    print(f"  mínimo de la tendencia: {minimo:%Y-%m}, {tendencia[minimo]:,.0f} MW")
    print(f"  tendencia al final ({tendencia.index[-1]:%Y-%m}): {tendencia.iloc[-1]:,.0f} MW")

    estacional_mes = stl.seasonal.groupby(stl.seasonal.index.month).mean()
    print("  estacional promedio por mes, de mayor a menor (MW):")
    for mes, valor in estacional_mes.sort_values(ascending=False).items():
        print(f"    {mes:>2}: {valor:+,.0f}")
    print(f"  amplitud (mes más alto − más bajo): "
          f"{estacional_mes.max() - estacional_mes.min():,.0f} MW")

    residuo = stl.resid
    print(f"  desviación estándar del residuo: {residuo.std():,.0f} MW; "
          f"meses con |residuo| < 500 MW: {(residuo.abs() < 500).mean():.0%}")
    print("  cinco residuos más grandes en valor absoluto:")
    for mes in residuo.abs().nlargest(5).index:
        esperado = tendencia[mes] + stl.seasonal[mes]
        print(f"    {mes:%Y-%m}: real {serie[mes]:,.0f} | tendencia + estacional "
              f"{esperado:,.0f} | residuo {residuo[mes]:+,.0f} MW "
              f"({residuo[mes] / residuo.std():+.1f} desv.)")
    return stl


# ============================================================
# 3. Estacionariedad e identificación
# ============================================================

def estacionariedad(serie):
    """ADF sobre la serie, su diferencia regular, la estacional y las dos.

    Imprime el valor p de cada versión, elige d y D, y guarda la ACF y la
    PACF de la serie elegida en figuras/acf_pacf.png. Devuelve (d, D).
    """
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    from statsmodels.tsa.stattools import acf, adfuller, pacf

    # (nombre, d, D, versión). La original tiene tendencia visible, así que
    # se prueba con constante y tendencia ("ct"); las diferenciadas ya no la
    # tienen y se prueban solo con constante ("c").
    versiones = [
        ("original", 0, 0, serie),
        ("diff(12)", 0, 1, serie.diff(PERIODO)),
        ("diff()", 1, 0, serie.diff()),
        ("diff(12).diff()", 1, 1, serie.diff(PERIODO).diff()),
    ]
    print("\nParte 3. Prueba ADF (H0: raíz unitaria)")
    print(f"  {'versión':<16} {'d':>2} {'D':>2} {'regression':>10} {'valor p':>9}")
    filas = []
    for nombre, d, D, version in versiones:
        regresion = "ct" if nombre == "original" else "c"
        valor_p = adfuller(version.dropna(), regression=regresion)[1]
        filas.append((nombre, d, D, valor_p))
        print(f"  {nombre:<16} {d:>2} {D:>2} {regresion:>10} {valor_p:>9.4f}")

    # Regla: la combinación con menos diferencias cuyo valor p queda bajo
    # 0,05. Si empatan la regular y la estacional, se prefiere la estacional
    # (por eso va antes en la lista): la estacionalidad es lo más marcado de
    # la serie y solo diff(12) la quita.
    estacionarias = [f for f in filas if f[3] < 0.05]
    nombre, d, D, valor_p = min(estacionarias, key=lambda f: f[1] + f[2])
    print(f"  elegida: {nombre} -> d = {d}, D = {D} (valor p {valor_p:.4f})")

    elegida = serie
    if D:
        elegida = elegida.diff(PERIODO)
    if d:
        elegida = elegida.diff()
    elegida = elegida.dropna()

    rezagos = 36
    figura, ejes = plt.subplots(2, 1, figsize=(9, 6))
    plot_acf(elegida, lags=rezagos, ax=ejes[0], title=f"ACF de {nombre}")
    plot_pacf(elegida, lags=rezagos, ax=ejes[1], method="ywm",
              title=f"PACF de {nombre}")
    figura.tight_layout()
    figura.savefig(FIGURAS / "acf_pacf.png", dpi=120)
    plt.close(figura)

    # Rezagos fuera de las bandas del 95 %, las mismas que dibujan las gráficas.
    valores_acf, bandas_acf = acf(elegida, nlags=rezagos, alpha=0.05)
    valores_pacf, bandas_pacf = pacf(elegida, nlags=rezagos, alpha=0.05, method="ywm")

    def fuera(bandas):
        return [k for k in range(1, rezagos + 1)
                if not bandas[k, 0] <= 0 <= bandas[k, 1]]

    fuera_acf, fuera_pacf = fuera(bandas_acf), fuera(bandas_pacf)
    print(f"  ACF, rezagos fuera de las bandas: {fuera_acf}")
    print(f"  PACF, rezagos fuera de las bandas: {fuera_pacf}")
    print("  rezago |  ACF  | PACF")
    for k in sorted(set(fuera_acf) | set(fuera_pacf) | {12, 24, 36}):
        print(f"  {k:>6} | {valores_acf[k]:+.2f} | {valores_pacf[k]:+.2f}")
    return d, D


# ============================================================
# 4. Modelos clásicos
# ============================================================
# Cada modelo es una función modelo(entrenamiento, h) que devuelve h
# pronósticos y solo usa `entrenamiento`. Así entra al backtest común.

# Los modelos se ajustan sobre serie / ESCALA, en GW (valores entre 12,8 y
# 19,2), y sus pronósticos se multiplican por ESCALA para volver a MW. Con
# la serie en MW, sigma2 queda en cientos de miles y el optimizador se pierde.
ESCALA = 1000

# Rejilla: p de 0 a 3 y q de 0 a 2 (la PACF de diff(12) sale en los rezagos
# 1 y 3), P y Q en 0 o 1 (el pico del rezago 12). d y D quedan fijos: cambian
# la serie que se modela y el AIC de series distintas no se compara.
REJILLA_P, REJILLA_Q, REJILLA_ESTACIONAL = range(4), range(3), range(2)


def elegir_sarima(serie, d, D):
    """Rejilla pequeña de órdenes (p, q, P, Q) comparada por AIC.

    Ajusta con toda la serie preparada, imprime la tabla de AIC, revisa los
    residuos del elegido con Ljung-Box y guarda figuras/residuos.png.
    Devuelve el orden y el orden estacional elegidos.
    """
    import itertools

    from statsmodels.graphics.tsaplots import plot_acf
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.tsa.arima.model import ARIMA

    escalada = serie / ESCALA
    filas = []
    for p, q, P, Q in itertools.product(REJILLA_P, REJILLA_Q,
                                        REJILLA_ESTACIONAL, REJILLA_ESTACIONAL):
        ajuste = ARIMA(escalada, order=(p, d, q),
                       seasonal_order=(P, D, Q, PERIODO)).fit()
        filas.append({"order": (p, d, q), "seasonal_order": (P, D, Q, PERIODO),
                      "AIC": ajuste.aic})
    rejilla = pd.DataFrame(filas).sort_values("AIC").reset_index(drop=True)

    print(f"\nParte 4. Rejilla SARIMA: {len(rejilla)} modelos con d = {d} y D = {D}, "
          f"ordenados por AIC (los 10 primeros)")
    print(rejilla.head(10).to_string(formatters={"AIC": "{:.2f}".format}))
    orden = rejilla.loc[0, "order"]
    orden_estacional = rejilla.loc[0, "seasonal_order"]
    print(f"  elegido: SARIMA{orden}{orden_estacional}, AIC {rejilla.loc[0, 'AIC']:.2f}")

    mejor = ARIMA(escalada, order=orden, seasonal_order=orden_estacional).fit()
    print("  coeficientes del elegido (serie en GW):")
    for nombre, valor in mejor.params.items():
        print(f"    {nombre:<10} {valor:+.3f}  (valor p {mejor.pvalues[nombre]:.3f})")

    # Los primeros d + 12·D residuos salen de la inicialización de las
    # diferencias, no son errores de pronóstico: se dejan por fuera.
    residuos = mejor.resid.iloc[d + PERIODO * D:] * ESCALA
    prueba = acorr_ljungbox(residuos, lags=[12, 24])
    print(f"  Ljung-Box sobre {len(residuos)} residuos (H0: son ruido blanco):")
    for rezago, fila_lb in prueba.iterrows():
        print(f"    lags={rezago}: Q = {fila_lb['lb_stat']:.2f}, "
              f"valor p {fila_lb['lb_pvalue']:.3f}")
    print(f"  residuos: media {residuos.mean():+,.0f} MW, "
          f"desviación estándar {residuos.std():,.0f} MW")

    figura, ejes = plt.subplots(2, 1, figsize=(9, 6))
    ejes[0].plot(residuos.index, residuos.to_numpy())
    ejes[0].axhline(0, color="gray", linewidth=0.8)
    ejes[0].set_title(f"Residuos de SARIMA{orden}{orden_estacional}")
    ejes[0].set_ylabel("MW")
    plot_acf(residuos, lags=36, ax=ejes[1], title="ACF de los residuos")
    figura.tight_layout()
    figura.savefig(FIGURAS / "residuos.png", dpi=120)
    plt.close(figura)
    return orden, orden_estacional


def modelo_sarima(orden, orden_estacional):
    """Devuelve la función modelo(entrenamiento, h) del SARIMA elegido."""
    from statsmodels.tsa.arima.model import ARIMA

    def modelo(entrenamiento, h):
        # Se reajusta en cada origen solo con `entrenamiento`: no hay fuga.
        ajuste = ARIMA(entrenamiento / ESCALA, order=orden,
                       seasonal_order=orden_estacional).fit()
        return ajuste.forecast(h).to_numpy() * ESCALA

    return modelo


def contrastar_estacional(serie, orden, orden_estacional):
    """Experimento: el mismo SARIMA con P cambiado (1 -> 0 o 0 -> 1).

    La rejilla elige por AIC, que mide el ajuste dentro de la muestra. Este
    contraste mide el modelo vecino en el mismo backtest. No entra a la tabla:
    elegir el modelo por su backtest sería usar los datos de prueba para
    seleccionarlo.
    """
    from statsmodels.tsa.arima.model import ARIMA

    P, D, Q, s = orden_estacional
    vecino = (1 - P, D, Q, s)
    aic = ARIMA(serie / ESCALA, order=orden, seasonal_order=vecino).fit().aic
    _, promedio = backtest(serie, modelo_sarima(orden, vecino))
    print(f"  contraste (no entra a la tabla): SARIMA{orden}{vecino}, AIC {aic:.2f} | "
          f"backtest RMSE {promedio['RMSE']:.2f}, MAE {promedio['MAE']:.2f}, "
          f"MAPE {promedio['MAPE']:.2f}")


def exogenas(serie):
    """TODO: DataFrame de variables conocidas de antemano, con el índice de la serie.

    Por ejemplo, el número de festivos o de días hábiles de cada mes. Debe
    cubrir también los 12 meses que siguen al final de la serie.
    """
    raise NotImplementedError("variables exógenas")


def modelo_sarimax(orden, orden_estacional, x):
    """TODO: devuelva modelo(entrenamiento, h) de un SARIMAX con exógenas x.

    Use x.loc[entrenamiento.index] para ajustar y
    x.loc[fechas_siguientes(entrenamiento, h)] para pronosticar.
    """
    raise NotImplementedError("SARIMAX en el backtest")


# ============================================================
# 5. La tabla de métricas
# ============================================================

def fila(nombre, serie, modelo):
    _, promedio = backtest(serie, modelo)
    return {"modelo": nombre, "decision": DECISION,
            "RMSE": round(promedio["RMSE"], 2), "MAE": round(promedio["MAE"], 2),
            "MAPE": round(promedio["MAPE"], 2)}


def pendiente(parte, error):
    print(f"  pendiente: {parte} ({error})")


def main():
    cruda = cargar_serie(ARCHIVO, FECHA, VALOR)
    print(f"Serie: {len(cruda)} meses, de {cruda.index[0]:%Y-%m} a "
          f"{cruda.index[-1]:%Y-%m}, {cruda.isna().sum()} vacíos")
    serie = preparar(cruda)
    graficar_serie(serie)

    filas = [fila("ingenuo", serie, ingenuo),
             fila("estacional ingenuo", serie,
                  lambda t, h: estacional_ingenuo(t, h, PERIODO))]

    try:
        descomponer(serie)
    except NotImplementedError as error:
        pendiente("parte 2", error)

    try:
        d, D = estacionariedad(serie)
    except NotImplementedError as error:
        pendiente("parte 3", error)
        d = D = None

    if d is not None:
        try:
            orden, estacional = elegir_sarima(serie, d, D)
            filas.append(fila(f"SARIMA{orden}{estacional}", serie,
                              modelo_sarima(orden, estacional)))
            contrastar_estacional(serie, orden, estacional)
            x = exogenas(serie)
            filas.append(fila(f"SARIMAX{orden}{estacional} + exógenas", serie,
                              modelo_sarimax(orden, estacional, x)))
        except NotImplementedError as error:
            pendiente("parte 4", error)

    tabla = pd.DataFrame(filas).sort_values("RMSE")
    tabla.to_csv(RESULTADOS / "metricas.csv", index=False)
    print(tabla.drop(columns="decision").to_string(index=False))
    print("Mejor modelo por RMSE:", tabla.iloc[0]["modelo"])


if __name__ == "__main__":
    main()

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
    """TODO: ADF sobre la serie, su diferencia regular, la estacional y las dos.

    Imprima el valor p de cada versión, elija d y D, y guarde la ACF y la
    PACF de la serie elegida en figuras/acf_pacf.png. Devuelva (d, D).
    """
    raise NotImplementedError("estacionariedad, ACF y PACF")


# ============================================================
# 4. Modelos clásicos
# ============================================================
# Cada modelo es una función modelo(entrenamiento, h) que devuelve h
# pronósticos y solo usa `entrenamiento`. Así entra al backtest común.

def elegir_sarima(serie, d, D):
    """TODO: rejilla pequeña de órdenes (p, q, P, Q) comparada por AIC.

    Ajuste con toda la serie preparada, imprima la tabla de AIC, revise los
    residuos del elegido con Ljung-Box y guarde figuras/residuos.png.
    Devuelva el orden y el orden estacional elegidos.
    """
    raise NotImplementedError("selección del SARIMA")


def modelo_sarima(orden, orden_estacional):
    """TODO: devuelva la función modelo(entrenamiento, h) del SARIMA elegido."""
    raise NotImplementedError("SARIMA en el backtest")


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

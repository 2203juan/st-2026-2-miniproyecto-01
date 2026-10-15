"""Lo común del curso: carga de la serie, métricas, líneas base y backtest.

Este archivo no se modifica. Todos los grupos miden con el mismo backtest y
las mismas métricas, y así las tablas se pueden comparar entre sí.
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).parent


# ---------- Carga ----------

def cargar_serie(archivo, fecha, valor):
    """Serie mensual con índice de fechas; los meses sin dato quedan en NaN."""
    tabla = pd.read_csv(RAIZ / archivo)
    tabla.index = pd.to_datetime(tabla[fecha])
    serie = tabla[valor].astype(float).asfreq("MS")
    serie.name = valor
    return serie


def fechas_siguientes(entrenamiento, h):
    """Las h fechas mensuales que siguen al último dato de entrenamiento."""
    return pd.date_range(entrenamiento.index[-1], periods=h + 1, freq="MS")[1:]


# ---------- Métricas ----------

def mae(y, y_hat):
    y, y_hat = np.asarray(y), np.asarray(y_hat)
    return np.mean(np.abs(y - y_hat))


def rmse(y, y_hat):
    y, y_hat = np.asarray(y), np.asarray(y_hat)
    return np.sqrt(np.mean((y - y_hat) ** 2))


def mape(y, y_hat):
    y, y_hat = np.asarray(y), np.asarray(y_hat)
    return 100 * np.mean(np.abs((y - y_hat) / y))


# ---------- Líneas base ----------

def ingenuo(entrenamiento, h):
    """Repite el último valor observado durante h meses."""
    return np.repeat(entrenamiento.iloc[-1], h)


def estacional_ingenuo(entrenamiento, h, m=12):
    """Repite el mismo mes del último año observado."""
    ultimo_anio = entrenamiento.iloc[-m:].to_numpy()
    return np.resize(ultimo_anio, h)


# ---------- Backtest ----------

def backtest(serie, modelo, n_prueba=24, h=12):
    """Origen móvil sobre los últimos n_prueba meses, horizonte de 1 a h.

    `modelo(entrenamiento, h)` recibe solo los datos hasta el origen y
    devuelve h pronósticos. Nada posterior al origen entra al modelo.
    Devuelve las métricas por origen y su promedio.
    """
    filas = []
    primero = len(serie) - n_prueba
    for corte in range(primero, len(serie) - h + 1):
        entrenamiento = serie.iloc[:corte]
        real = serie.iloc[corte:corte + h].to_numpy()
        pronostico = np.asarray(modelo(entrenamiento, h))
        filas.append({"origen": serie.index[corte - 1],
                      "RMSE": rmse(real, pronostico),
                      "MAE": mae(real, pronostico),
                      "MAPE": mape(real, pronostico)})
    por_origen = pd.DataFrame(filas)
    return por_origen, por_origen[["RMSE", "MAE", "MAPE"]].mean()

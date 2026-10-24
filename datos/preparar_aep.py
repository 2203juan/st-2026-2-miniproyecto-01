"""Convierte la carga horaria de AEP en la serie mensual del grupo.

Fuente: Kaggle, robikscube/hourly-energy-consumption (Rob Mulla), archivo
AEP_hourly.csv, con la carga horaria de American Electric Power en PJM, en MW.

Se corre una sola vez, desde la raíz del repositorio:

    python datos/preparar_aep.py

y deja datos/aep_mensual.csv, que es lo que lee miniproyecto.py. El guion no
depende de este archivo ni de Kaggle: el CSV mensual ya queda en el
repositorio.

Decisiones, las mismas del taller 1:
- Las horas duplicadas por el cambio de horario de verano se promedian.
- Cada mes es el promedio de sus horas (resample("MS").mean()): el valor es la
  carga media por hora del mes, en MW.
- Se descartan los meses con menos de 672 horas (28 días). Solo cae agosto de
  2018, que tiene 49 horas y quedaría sesgado.
"""
from pathlib import Path

import pandas as pd

DATOS = Path(__file__).parent
HORAS_MINIMAS = 28 * 24

horaria = pd.read_csv(DATOS / "AEP_hourly.csv", parse_dates=["Datetime"])
horaria = horaria.set_index("Datetime").sort_index()
horaria = horaria.groupby(level=0).mean()  # horas duplicadas por cambio de horario

mensual = horaria["AEP_MW"].resample("MS").mean()
horas = horaria["AEP_MW"].resample("MS").count()
print("datos horarios:", len(horaria), "| meses:", len(mensual))
print("meses incompletos que se descartan:",
      [f"{m:%Y-%m} ({n} h)" for m, n in horas[horas < HORAS_MINIMAS].items()])
mensual = mensual[horas >= HORAS_MINIMAS]

salida = mensual.rename_axis("mes").reset_index()
salida["mes"] = salida["mes"].dt.strftime("%Y-%m")
salida.to_csv(DATOS / "aep_mensual.csv", index=False)
print(f"guardado datos/aep_mensual.csv con {len(mensual)} meses, "
      f"de {mensual.index[0]:%Y-%m} a {mensual.index[-1]:%Y-%m}")

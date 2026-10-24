# datos

La serie del grupo va en esta carpeta, en CSV.

| Campo | Valor |
|---|---|
| Archivo | `aep_mensual.csv` ([descarga directa](https://raw.githubusercontent.com/2203juan/st-2026-2-miniproyecto-01/main/datos/aep_mensual.csv)) |
| Qué mide | Carga eléctrica media por hora de cada mes en la zona de American Electric Power (AEP), dentro de PJM, en MW |
| Fuente | Kaggle, [robikscube/hourly-energy-consumption](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption) (Rob Mulla), archivo `AEP_hourly.csv`; datos originales de [PJM](https://www.pjm.com/) |
| Licencia | CC0: Public Domain |
| Frecuencia | mensual (agregada a partir de datos horarios) |
| Periodo | 2004-10 a 2018-07 (166 observaciones) |
| Columna de fecha | `mes` |
| Columna que se pronostica | `AEP_MW` |

## Cómo se construye la serie mensual

`AEP_hourly.csv` trae la carga horaria original (121 269 horas, de octubre de
2004 a agosto de 2018). `preparar_aep.py` la convierte en `aep_mensual.csv`:

```bash
python datos/preparar_aep.py
```

- Las horas duplicadas por el cambio de horario de verano se promedian.
- Cada mes es el promedio de sus horas (`resample("MS").mean()`), así que el
  valor es la carga media por hora del mes, en MW.
- Se descartan los meses con menos de 672 horas (28 días): solo agosto de
  2018, que tiene 49 horas y quedaría sesgado.

`miniproyecto.py` lee directamente `aep_mensual.csv`. No necesita Kaggle ni
`kagglehub`, y por eso corre igual en Github Actions.

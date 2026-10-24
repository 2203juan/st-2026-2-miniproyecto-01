# Informe del miniproyecto 1

Llene cada sección reemplazando los marcadores `{{...}}`, sin quitar las
secciones. Las cifras salen de lo que imprime `python miniproyecto.py` y las
figuras son las que ese guion deja en `figuras/`. Las fórmulas van en LaTeX
(`$...$` o `$$...$$`).

## 1. La serie

La serie es la carga eléctrica media por hora de cada mes en la zona de
American Electric Power (AEP), una de las zonas de la red de PJM en el
oriente de Estados Unidos, medida en MW. Sale del conjunto de Kaggle
[robikscube/hourly-energy-consumption](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption)
(Rob Mulla, datos originales de PJM), con licencia CC0: Public Domain. La
fuente es horaria. La agregamos a frecuencia mensual promediando las horas
de cada mes:

$$y_t = \frac{1}{H_t}\sum_{i=1}^{H_t} x_{t,i},$$

donde $x_{t,i}$ es la carga de la hora $i$ del mes $t$ y $H_t$ el número de
horas del mes. La serie va de octubre de 2004 a julio de 2018: 166
observaciones. La elegimos porque es pública, tiene 166 meses (el mínimo es
60) y muestra dos picos al año: uno en invierno, por la calefacción, y otro en
verano, por el aire acondicionado. El valor más alto es febrero de 2007, con
19 213 MW, y el más bajo octubre de 2016, con 12 805 MW.

![La serie](../figuras/serie.png)

### Huecos

La serie mensual no tiene meses vacíos: el guion reporta `0
vacíos`. Las únicas decisiones sobre huecos se toman al agregar los datos
horarios, en `datos/preparar_aep.py`. Las horas duplicadas por el cambio de
horario de verano se promedian. Además, se descarta agosto de 2018, que solo
tiene 49 horas: un promedio de dos días no representa el mes y quedaría
sesgado. Por eso la serie termina en julio de 2018. Aun así, `preparar`
interpola linealmente cualquier NaN para que el *backtest* nunca reciba
huecos.

### Datos atípicos

Para buscar atípicos sin depender todavía de ningún modelo, `preparar`
compara cada mes con el mismo mes del año anterior y del siguiente:

$$a_t = y_t - \frac{y_{t-12} + y_{t+12}}{2}.$$

Como la carga depende del clima, $a_t$ mide cuánto se aparta un mes de lo
que fue ese mismo mes en los años vecinos. Se puede calcular en 142 meses (los
12 primeros y los 12 últimos no tienen vecinos) y su desviación estándar es
757 MW. Marcamos como atípico un mes con $\lvert a_t \rvert$ mayor que 3
desviaciones estándar, y solo hay uno: julio de 2009, con 14 697 MW frente a
17 360 MW de los julios vecinos ($-2\,663$ MW, $-3{,}5$ desviaciones). Los
siguientes ya quedan por debajo del umbral: diciembre de 2010 (+1 859 MW,
+2,5), febrero de 2015 (+1 760 MW, +2,3) y julio de 2008 (+1 681 MW, +2,2).

Decidimos conservar julio de 2009. No es un error de medición: es la carga
que hubo ese mes, en pleno verano.
No tenemos una fuente sobre el clima de ese mes, así que no le atribuimos una
causa. Quitarlo o suavizarlo haría que la serie se viera más regular de lo
que es, y el modelo no aprendería que hay veranos con mucha menos carga de la
esperada. La decisión queda en la columna `decision` de la tabla: *sin huecos
(ago-2018 incompleto se descarta al agregar); el atípico de jul-2009 se
conserva porque es demanda real*.

## 2. Componentes

![STL](../figuras/stl.png)

{{Lectura de la descomposición STL: cómo es la tendencia, qué meses quedan
arriba y abajo en la estacional y con cuánto, y dónde está el residuo más
grande.}}

## 3. Líneas base y backtest

{{Cómo es el backtest: cuántos orígenes, horizonte y qué meses quedan en la
prueba. Por qué ningún dato posterior al origen entra al modelo.}}

{{RMSE, MAE y MAPE del ingenuo y del estacional ingenuo, y cuál gana.}}

## 4. Estacionariedad e identificación

{{Valor p de la prueba ADF para la serie, su diferencia regular, la
estacional y las dos juntas. El d y el D elegidos.}}

![ACF y PACF](../figuras/acf_pacf.png)

{{Qué rezagos salen de las bandas y qué órdenes sugieren.}}

## 5. Modelos clásicos

{{La rejilla de órdenes y su AIC. El modelo elegido, escrito con su
ecuación.}}

![Residuos](../figuras/residuos.png)

{{Diagnóstico de los residuos: Ljung-Box y lo que muestran la gráfica y su
ACF.}}

{{La variable exógena: qué es, por qué se conoce de antemano y si mejora al
SARIMA.}}

## 6. Tabla de métricas

{{Copie aquí `resultados/metricas.csv` como tabla de Markdown, ordenada por
RMSE.}}

| Modelo | Decisión | RMSE | MAE | MAPE (%) |
|---|---|---|---|---|
| {{...}} | {{...}} | {{...}} | {{...}} | {{...}} |

## 7. Conclusión

{{El mejor modelo clásico, cuánto mejora a la mejor línea base en cada
métrica y en qué meses o tramos sigue fallando. Es el modelo que el
miniproyecto 2 debe superar.}}

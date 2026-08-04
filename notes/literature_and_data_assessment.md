# Descomposición del crecimiento de la remuneración por logro educativo

## Pregunta

¿Cuánto del cambio de la remuneración laboral promedio de un país proviene de cambios en la remuneración dentro de cada logro educativo y cuánto proviene del aumento del logro educativo de la población ocupada?

## Relación con el informe de Colombia

El informe colombiano partió de la identidad

\[
R_t=\sum_g s_{g,t}r_{g,t},
\]

donde \(r_{g,t}\) es la remuneración promedio del grupo educativo \(g\) y \(s_{g,t}\) es su participación en los ocupados —o en las horas trabajadas para la remuneración por hora—. El cambio entre dos fechas se descompuso de manera simétrica:

\[
R_1-R_0
=
\sum_g \bar{s}_g(r_{g,1}-r_{g,0})
+
\sum_g \bar{r}_g(s_{g,1}-s_{g,0}).
\]

El primer término es un efecto dentro de los grupos o efecto de remuneración. El segundo es un efecto de composición educativa. La fórmula es una descomposición contable; no identifica el efecto causal de la educación ni permite llamar productividad a todo cambio de remuneración dentro de un logro educativo.

## Antecedentes

### Método

- Kitagawa (1955), *Components of a Difference Between Two Rates*, formuló la descomposición simétrica entre cambios de composición y cambios dentro de los grupos. Es el antecedente metodológico más directo de la identidad usada en el informe.
- Oaxaca (1973) y Blinder (1973) llevaron esta lógica a diferencias de medias con regresiones. La literatura posterior denomina los componentes efecto composición y efecto estructura salarial.
- Fortin, Lemieux y Firpo (2011), *Decomposition Methods in Economics*, sistematizan las descomposiciones de medias y distribuciones y subrayan que los componentes no tienen, en general, interpretación causal.
- Shorrocks (2013) usa el valor de Shapley para promediar los posibles órdenes cuando se descomponen varios determinantes y aparece dependencia de la trayectoria.

### Aplicaciones a salarios

- Jimeno, Lamo y Christopoulou (2010) separan, para nueve países europeos, los cambios salariales debidos a la composición de trabajadores, empresas y empleos de los cambios en los retornos a esas características. Encuentran que edad, género y educación explican poco de la dinámica salarial observada frente a otras características.
- Daly y Hobijn (2017) muestran para Estados Unidos que los cambios en la composición del empleo alteran el crecimiento del salario real agregado a lo largo del ciclo.
- Kouvavas, Kuik, Koester y Nickel (2019) encuentran que la edad y la educación son componentes importantes de los efectos de composición sobre el crecimiento salarial de la zona del euro.
- Lasso-Valderrama y Rodríguez-Quintero (2018) descomponen el cambio salarial en Colombia entre efectos de composición y estructura salarial mediante regresiones RIF. El capital humano —educación y experiencia— es el factor que más contribuye a ambos.

### América Latina, educación y retornos

- Gasparini, Galiani, Cruces y Acosta (2011/2019) estudian 16 países entre 1990 y 2010. Documentan el aumento del logro educativo y la caída de los premios salariales de secundaria y educación terciaria; su objeto es explicar el premio salarial mediante oferta y demanda, no descomponer el crecimiento de la remuneración promedio.
- Azevedo et al. (2013), *Fifteen Years of Inequality in Latin America*, separan efectos de cantidades, precios y no observables sobre la desigualdad del ingreso laboral en 15 países. Encuentran que la caída de los retornos a educación y experiencia fue el principal factor detrás de la reducción de la desigualdad.
- Azevedo, Inchauste y Sanfelice (2013) descomponen la reducción de la desigualdad en la región mediante contrafactuales y valores de Shapley. Su foco es la distribución del ingreso del hogar, no el nivel medio de la remuneración por logro educativo.
- Messina y Silva (2019) documentan que la rápida expansión educativa redujo los salarios relativos de graduados universitarios y de secundaria frente a primaria y que buena parte de la compresión salarial ocurrió dentro de grupos de habilidades.
- Behar (2026) actualiza la evidencia regional sobre el premio a la educación superior y separa oferta, demanda y cambio técnico dirigido. El premio continúa cayendo, aunque a un ritmo menor y con heterogeneidad entre países.

## Evaluación de novedad

La idea no es nueva como método: pertenece a la familia Kitagawa–Oaxaca–Blinder y existe una literatura amplia sobre composición, estructura salarial, expansión educativa y premios por habilidades. Tampoco sería defendible presentar el componente dentro de cada logro educativo como una medida pura de productividad.

La contribución potencial está en otro lugar:

1. aplicar una descomposición transparente y exactamente aditiva al nivel medio del ingreso laboral, no solo a su desigualdad o al premio salarial;
2. hacerlo de manera comparable para varios países de América Latina con la clasificación armonizada de LABLAC;
3. actualizar el periodo hasta 2024 e identificar qué países elevaron el ingreso laboral principalmente mediante mayor logro educativo y cuáles mediante aumentos dentro de cada logro;
4. relacionar los resultados con la caída de los premios educativos y con las rupturas de comparabilidad de las encuestas.

La contribución sería más fuerte si el paper añade heterogeneidad por sexo, edad, formalidad o sector, o si compara la descomposición contable con una Oaxaca–Blinder/RIF basada en microdatos.

## Datos y alcance recomendado

El paquete público del Banco Mundial cubre 14 países entre 2016 y 2024 con tres grupos educativos. La versión inicial debe usar ingreso laboral mensual. El ejercicio por hora no es exacto con los archivos publicados porque el indicador cubre asalariados y la base de ponderadores cuenta a todos los trabajadores.

Para evitar estacionalidad y diferencias en la frecuencia de las encuestas, conviene construir promedios anuales por país y no comparar trimestres aislados. Los países con observaciones anuales o con series cortas —Chile y Guatemala— deben tratarse por separado. Las rupturas metodológicas que el tablero marca mediante cambios de encuesta o de serie no deben atravesarse en una comparación sin una prueba explícita de comparabilidad.

## Fuentes

- Banco Mundial, [LAC Equity Lab: Wage and Income](https://www.worldbank.org/en/topic/poverty/lac-equity-lab1/labor-markets/wage-and-income).
- Kitagawa (1955), [Components of a Difference Between Two Rates](https://doi.org/10.1080/01621459.1955.10501299).
- Fortin, Lemieux y Firpo (2011), [Decomposition Methods in Economics](https://doi.org/10.1016/S0169-7218(11)00407-2).
- Shorrocks (2013), [Decomposition Procedures for Distributional Analysis](https://doi.org/10.1007/s10888-011-9214-z).
- Jimeno, Lamo y Christopoulou (2010), [Changes in the Wage Structure in EU Countries](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1199.pdf).
- Daly y Hobijn (2017), [Composition and Aggregate Real Wage Growth](https://doi.org/10.1257/aer.p20171075).
- Kouvavas et al. (2019), [The Effects of Changes in the Composition of Employment on Euro Area Wage Growth](https://www.ecb.europa.eu/pub/economic-bulletin/articles/2019/html/ecb.ebart201908_02~d5d812d234.en.html).
- Lasso-Valderrama y Rodríguez-Quintero (2018), [Ciclo y composición del cambio en los salarios](https://doi.org/10.32468/be.1057).
- Gasparini et al. (2011), [Educational Upgrading and Returns to Skills in Latin America](https://www.iza.org/publications/dp/6244).
- Azevedo et al. (2013), [Fifteen Years of Inequality in Latin America](https://doi.org/10.1596/1813-9450-6384).
- Azevedo, Inchauste y Sanfelice (2013), [Decomposing the Recent Inequality Decline in Latin America](https://documents.worldbank.org/curated/en/597661468054543060/pdf/WPS6715.pdf).
- Messina y Silva (2019), [Twenty Years of Wage Inequality in Latin America](https://doi.org/10.18235/0001806).
- Behar (2026), [Explaining Latin America’s Decreasing Skilled Wage Premium](https://doi.org/10.5089/9798229040020.001).

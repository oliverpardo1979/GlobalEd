# Diseño de los dos papers

## Distinción central

Los dos papers usan la misma identidad contable, pero no estudian la misma
población ni la misma medida de remuneración.

| Elemento | Paper global | Paper de América Latina |
|---|---|---|
| Población | Asalariados | Todos los ocupados |
| Remuneración | Salario mensual promedio | Ingreso laboral mensual promedio |
| Frecuencia principal | Anual | Anual, construido a partir de datos trimestrales |
| Fuente | ILOSTAT | Banco Mundial, LAC Equity Lab |
| Educación | Menos que básica, básica, intermedia y avanzada | Logro bajo, medio y alto |
| Cobertura preliminar | 117 países con algún año completo; 44 con al menos cinco años limpios en una misma fuente | 14 países, con cobertura desigual entre 2016 y 2024 |

No se deben combinar las observaciones de los dos papers en una sola muestra:
ILOSTAT mide salarios de asalariados y LABLAC mide ingreso laboral de todos los
ocupados. La diferencia incluye, entre otros elementos, el ingreso de los
trabajadores por cuenta propia.

## Paper global

### Pregunta

¿Qué parte del cambio en el salario real promedio de los asalariados se asocia
con el aumento del logro educativo y qué parte se asocia con cambios en el
salario dentro de cada logro?

### Base

- Remuneración: `EAR_EMTA_SEX_EDU_NB_A`.
- Ponderadores: `EMP_TEMP_SEX_STE_EDU_NB_A`, filtrando
  `STE_AGGREGATE_EES`.
- Cruce: país, año, fuente y grupo educativo.
- Precios: índice de precios al consumidor de cada país.

### Auditoría preliminar

- 55.025 filas de remuneración y 743.475 filas de empleo descargadas.
- 962 combinaciones país-fuente-año tienen los cuatro grupos educativos en
  ambas tablas.
- 117 países tienen al menos un año completo.
- 44 países tienen al menos cinco años que cumplen, dentro de una misma fuente,
  los umbrales preliminares de calidad.
- 26 países tienen al menos diez años bajo esos mismos criterios.
- El filtro preliminar excluye una observación si la reconstrucción del salario
  total difiere más de 5% del total publicado o si más de 5% de los asalariados
  no reporta logro educativo.

Estos umbrales son reglas de selección preliminares. Antes de cerrar la muestra
se deben revisar las rupturas de serie, los años faltantes y los casos en que la
reconstrucción falla aunque el logro educativo desconocido sea pequeño.

## Paper de América Latina

### Pregunta

¿Qué parte del cambio reciente en el ingreso laboral promedio de los ocupados
provino del aumento del logro educativo y qué parte provino de cambios en el
ingreso laboral dentro de cada logro?

### Base

- Remuneración: ingreso laboral mensual promedio en dólares PPA de 2017.
- Ponderadores: número total de ocupados por logro educativo.
- Grupos: logro bajo, medio y alto.
- Periodo disponible: 2016--2024, con diferencias de frecuencia y longitud
  entre países.

### Decisiones ya tomadas

- El ejercicio principal usará ingreso laboral mensual.
- El salario por hora no se combinará con el número total de ocupados porque el
  numerador cubre asalariados y el denominador cubre todos los ocupados.
- Los resultados principales usarán promedios anuales.
- Las comparaciones no cruzarán una ruptura de encuesta o serie sin una prueba
  explícita de comparabilidad.

## Elementos compartidos

Los dos papers pueden compartir:

1. la identidad de remuneración promedio;
2. la descomposición simétrica de Kitagawa;
3. las pruebas de aditividad;
4. la estructura de cuadros y figuras de contribuciones;
5. parte de la revisión de literatura.

No deben compartir automáticamente:

1. la definición de trabajador;
2. la definición de remuneración;
3. los grupos educativos;
4. la ventana temporal;
5. el tratamiento de trabajadores por cuenta propia.

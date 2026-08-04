# LABLAC: Wage and Income

Fuente pública: [LAC Equity Lab: Wage and Income](https://www.worldbank.org/en/topic/poverty/lac-equity-lab1/labor-markets/wage-and-income).

Descarga realizada el 3 de agosto de 2026 desde el libro público de Tableau:

<https://dataviz.worldbank.org/t/LCSPP/workbooks/03_Wage_and_Income.twb?showTabs=true>

## Archivos

- `03_Wage_and_Income.twbx`: paquete original descargado del tablero.
- `LABLAC_LEL.twb`: definición del libro de Tableau; documenta filtros, etiquetas y la unidad `USD 2017 PPP`.
- `Wage-tableau.xlsx`: ingreso laboral mensual promedio y salario promedio por hora, totales y desagregados por edad, área, sexo y logro educativo.
- `Workers-tableau.xlsx`: población de 15 años o más y número de trabajadores, totales y desagregados por edad, área, sexo y logro educativo.

## Cobertura relevante

- Periodo máximo del paquete: 2016-I a 2024-IV.
- Países con ingreso laboral mensual: Argentina, Bolivia, Brasil, Chile, Colombia, Costa Rica, Ecuador, El Salvador, Guatemala, México, Paraguay, Perú (Lima y Callao), República Dominicana y Uruguay.
- Países con salario por hora: los anteriores excepto Perú (Lima y Callao).
- Grupos educativos:
  - bajo: nunca asistió, primaria completa y secundaria incompleta;
  - medio: secundaria completa y educación superior incompleta;
  - alto: educación superior completa.

El texto de la página del Banco Mundial repite por error la etiqueta `Low` para la educación superior completa. En los archivos, la categoría está identificada correctamente como `Educational attainment - high`.

## Advertencia metodológica

El salario por hora se calcula solo para asalariados, mientras `Total Workers` cuenta a todos los trabajadores. Por esta razón, `Workers-tableau.xlsx` no contiene los ponderadores correctos para reproducir una descomposición exacta del salario por hora. Para ese ejercicio se necesita el número de asalariados —y, si se quiere ponderar como en el informe colombiano, sus horas trabajadas— por logro educativo.

Para el ingreso laboral mensual, ponderar las medias educativas con `Total Workers` aproxima el promedio publicado, pero no lo reproduce exactamente porque el indicador de ingreso usa solo trabajadores con ingreso coherente reportado. La mediana del error relativo absoluto es 0,6% y el percentil 90 es 2,2%; en México, el error mediano es 3,7%. Una primera versión del paper puede definir explícitamente un promedio sintético sobre los tres grupos educativos, o conseguir el número de trabajadores con ingreso válido por grupo.

## Integridad

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `Wage-tableau.xlsx` | 687365 | `D5A4229ADFE93385F517CA53844FAAD0AA7DE0F4572A7ABD4C2B478AD932E6C0` |
| `Workers-tableau.xlsx` | 746212 | `26B983AD353934B1CB19173A8DACBF5A877FD0147A4823765ED2B6B4AD9CABDF` |
| `LABLAC_LEL.twb` | 302462 | `F02AE06A79881B0ECB18C943621655BD08BFA5E0BF2C6F01F802D9FF4B0BA83F` |
| `03_Wage_and_Income.twbx` | 4344886 | `3BAFD406BB1F11AC3BCC8D15B9894108B653DB19BA428E9A328E961E4CBFD1A0` |

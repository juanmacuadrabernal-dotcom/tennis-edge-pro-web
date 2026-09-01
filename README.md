# 🎾 TENNIS EDGE PRO

Versión avanzada del predictor de tenis.

## Funciones
- Base de datos SQLite local.
- Actualización incremental de partidos.
- Modelo de Machine Learning entrenable.
- Validación temporal.
- Métricas: Accuracy, Log Loss y Brier Score.
- Elo dinámico.
- Filtro por superficie.
- Forma reciente configurable.
- H2H con peso limitado.
- Estadísticas de saque.
- Interfaz web con Streamlit.

## Instalación

```bash
pip install -r requirements.txt
```

## Primera carga de datos

```bash
python update_data.py
```

## Entrenar el modelo

```bash
python train.py
```

## Ejecutar

```bash
streamlit run app.py
```

## Actualización automática

### Windows
Crea una tarea en el Programador de tareas que ejecute:

```bash
python C:\RUTA\predictor_tenis_pro\update_data.py
```

### Linux/macOS
Ejemplo cada 6 horas:

```bash
0 */6 * * * /ruta/python /ruta/predictor_tenis_pro/update_data.py
```

## Nota importante

La fuente incluida es un dataset histórico público. Para resultados de máxima actualidad debes sustituir o complementar el actualizador por una API de tenis con datos en tiempo real. El programa está preparado para evolucionar sin cambiar la interfaz principal.

Las predicciones son estimaciones estadísticas y no garantizan resultados.

import pandas as pd
import numpy as np
from crate import client
from datetime import datetime, timedelta
from skforecast.ForecasterAutoreg import ForecasterAutoreg
from sklearn.ensemble import RandomForestRegressor
import psycopg2

def connect_to_crate():
    return client.connect('http://10.38.32.137:8083', username='crate')

def fetch_data(mock=False):
    if mock:
        # Simulación de datos JSON para los últimos 3 días
        data = [
            {
                "timestamp": int((datetime.now() - timedelta(hours=hour)).timestamp() * 1000),
                "valor_temp": 20 + (hour % 5),  # Temperatura simulada entre 20 y 24
                "valor_humedad": 50 + (hour % 10)  # Humedad simulada entre 50 y 59
            }
            for hour in range(72)  # 72 horas = 3 días
        ]
        # Convertir el JSON simulado en un DataFrame
        df = pd.DataFrame(data)
    else:
        # Conexión real a la base de datos y consulta
        connection = connect_to_crate()
        cursor = connection.cursor()
        try:
            query = """
            SELECT time_index, temp, humedad
            FROM "doc"."etvariables"
            WHERE entity_id = 'julianor'
              AND time_index >= NOW() - INTERVAL '10 DAYS'
            ORDER BY time_index
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=['timestamp', 'valor_temp', 'valor_humedad'])
        finally:
            cursor.close()
            connection.close()
    
    # Remover valores atípicos
    df = remove_outliners(df)
    return df

def remove_outliners(df):
    df = df[(df['valor_temp'] > 0) & (df['valor_temp'] < 100) &
             (df['valor_humedad'] > 0) & (df['valor_humedad'] < 100)]
    return df

def save_predictions(predictions_temp, predictions_humedad,horas_prediccion):
    conn = psycopg2.connect(
        dbname='data_front',
        user='julian',
        password='123',
        host='postgres',
        port='5432'
    )
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM predicciones_temp;')
        cursor.execute('DELETE FROM predicciones_humedad;')

        for pred, hora in zip(predictions_temp, horas_prediccion):
            cursor.execute('''
                INSERT INTO predicciones_temp (entity_id, time_index, temp)
                VALUES (%s, %s, %s)
            ''', ('julianor', hora, pred))

        for pred, hora in zip(predictions_humedad, horas_prediccion):
            cursor.execute('''
                INSERT INTO predicciones_humedad (entity_id, time_index, humedad)
                VALUES (%s, %s, %s)
            ''', ('julianor', hora, pred))
        
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# Función para guardar las predicciones en PostgreSQL
def save_predictions(predictions_temp, predictions_humedad, horas_prediccion):
    conn = psycopg2.connect(
        dbname='data_front',
        user='julian',
        password='123',
        host='postgres',
        port='5432'
    )
    cursor = conn.cursor()
    try:
        # Limpiar las tablas de predicciones
        cursor.execute('DELETE FROM predicciones_temp;')
        cursor.execute('DELETE FROM predicciones_humedad;')

        # Insertar predicciones de temperatura con las horas correspondientes
        for pred, hora in zip(predictions_temp, horas_prediccion):
            cursor.execute('''
                INSERT INTO predicciones_temp (entity_id, time_index, temp)
                VALUES (%s, %s, %s)
            ''', ('julianor', hora, pred))

        # Insertar predicciones de humedad con las horas correspondientes
        for pred, hora in zip(predictions_humedad, horas_prediccion):
            cursor.execute('''
                INSERT INTO predicciones_humedad (entity_id, time_index, humedad)
                VALUES (%s, %s, %s)
            ''', ('julianor', hora, pred))
        
        # Confirmar los cambios en la base de datos
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# Obtener y preparar los datos
datos = fetch_data()
datos["fecha"] = pd.to_datetime(datos["timestamp"], unit="ms")
datos = datos.sort_values("fecha", ascending=True).reset_index(drop=True)
datos["minutos"] = (datos["fecha"] - datos["fecha"].min()).dt.total_seconds() / 60
tiempo_temp = datos["minutos"].to_list()
temperatura = datos["valor_temp"].to_list()
humedad = datos["valor_humedad"].to_list()

# Crear DataFrames de temperatura y humedad
data_temp = pd.DataFrame({'t': tiempo_temp, 'y': temperatura})
data_humedad = pd.DataFrame({'t': tiempo_temp, 'y': humedad})

# Parámetros de predicción
steps = 24
max_lags = min(48, len(data_temp) - 1)

# Entrenar y hacer predicciones para temperatura
forecaster_temp = ForecasterAutoreg(
    regressor=RandomForestRegressor(random_state=123),
    lags=max_lags
)
forecaster_temp.fit(y=data_temp['y'])
predictions_temp = forecaster_temp.predict(steps=steps)

# Entrenar y hacer predicciones para humedad
forecaster_humedad = ForecasterAutoreg(
    regressor=RandomForestRegressor(random_state=123),
    lags=max_lags
)
forecaster_humedad.fit(y=data_humedad['y'])
predictions_humedad = forecaster_humedad.predict(steps=steps)

# Generar las horas de predicción incrementales a partir de la última fecha
ultima_fecha = datos["fecha"].iloc[-1]
horas_prediccion = [ultima_fecha + timedelta(hours=i+1) for i in range(steps)]

# Guardar las predicciones en la base de datos
save_predictions(predictions_temp, predictions_humedad, horas_prediccion)

print("Predicciones de temperatura y humedad guardadas en PostgreSQL.")
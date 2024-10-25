import pandas as pd
import numpy as np
from skforecast.ForecasterAutoreg import ForecasterAutoreg
from sklearn.ensemble import RandomForestRegressor
import psycopg2
from crate import client

def connect_to_crate():
    return client.connect('http://10.38.32.137:8083', username='crate')

def fetch_data():
    connection = connect_to_crate()
    cursor = connection.cursor()
    try:
        query = """
        SELECT time_index, valor_temp, valor_humedad
        FROM "doc"."etvariables"
        WHERE entity_id = 'julianor'
          AND time_index >= NOW() - INTERVAL '1 DAYS'
        ORDER BY time_index
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        df = pd.DataFrame(rows, columns=['timestamp', 'valor_temp', 'valor_humedad'])
        df= remove_outliners(df)

        return df
    
    finally:
        cursor.close()
        connection.close()

def remove_outliers(df):
    df = df[(df['valor_temp'] <= 100) & (df['valor_humedad'] <= 100)]
    return df


def save_predictions(predictions_temp, predictions_humedad):
    conn = psycopg2.connect(
        dbname='nombre_base_datos',
        user='tu_usuario',
        password='tu_contraseña',
        host='localhost',
        port='5432'
    )
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM predicciones_temp;')
        cursor.execute('DELETE FROM predicciones_humedad;')

        for pred in predictions_temp:
            cursor.execute('''
                INSERT INTO predicciones_temp (entity_id, time_index, temp)
                VALUES (%s, %s, %s)
            ''', ('julianor', pd.Timestamp.now(), pred))

        for pred in predictions_humedad:
            cursor.execute('''
                INSERT INTO predicciones_humedad (entity_id, time_index, humedad)
                VALUES (%s, %s, %s)
            ''', ('julianor', pd.Timestamp.now(), pred))
        
        conn.commit()
    finally:
        cursor.close()
        conn.close()

datos = fetch_data()
datos["fecha"] = pd.to_datetime(datos["timestamp"], unit="ms")
datos = datos.sort_values("fecha", ascending=True).reset_index(drop=True)

datos["minutos"] = (datos["fecha"] - datos["fecha"].min()).dt.total_seconds() / 60
tiempo_temp = datos["minutos"].to_list()
temperatura = datos["valor_temp"].to_list()

humedad = datos["valor_humedad"].to_list()

data_temp = pd.DataFrame({'t': tiempo_temp, 'y': temperatura})
data_humedad = pd.DataFrame({'t': tiempo_temp, 'y': humedad})

steps = 1  

forecaster_temp = ForecasterAutoreg(
    regressor=RandomForestRegressor(random_state=123),
    lags=125
)

forecaster_temp.fit(y=data_temp['y'])

predictions_temp = forecaster_temp.predict(steps=steps)

forecaster_humedad = ForecasterAutoreg(
    regressor=RandomForestRegressor(random_state=123),
    lags=125
)

forecaster_humedad.fit(y=data_humedad['y'])

predictions_humedad = forecaster_humedad.predict(steps=steps)

save_predictions(predictions_temp, predictions_humedad)

print("Predicciones de temperatura y humedad guardadas en PostgreSQL.")

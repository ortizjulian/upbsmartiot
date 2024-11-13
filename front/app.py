import dash
from dash import dcc, html, callback
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
import numpy as np
import psycopg2
from psycopg2 import connect
from psycopg2 import OperationalError
from crate import client
# Inicializar la app
app = dash.Dash(__name__)

def connect_to_crate():
    return client.connect('http://10.38.32.137:8083', username='crate')

def get_data(selected_date=None):
    connection = connect_to_crate()
    cursor = connection.cursor()

    query = """
    SELECT entity_id, time_index, temp, humedad, lat, lon
    FROM "doc"."etvariables"
    WHERE entity_id = 'julianor'
    """
    if selected_date:
        start_of_day = pd.to_datetime(selected_date).floor('D').value // 10**6  # Convertir a milisegundos
        end_of_day = pd.to_datetime(selected_date).floor('D') + pd.Timedelta(days=1)
        end_of_day = end_of_day.value // 10**6  # Convertir a milisegundos
        query += f" AND time_index >= {start_of_day} AND time_index < {end_of_day}"

    query += " ORDER BY time_index;"

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        data = pd.DataFrame(rows, columns=['entity_id','time_index', 'temp', 'humedad', 'lat', 'lon'])
        data = remove_outliners(data)
    except Exception as e:
        print(f"Error al obtener datos: {e}")
        data = pd.DataFrame()  
    finally:
        cursor.close()  
        connection.close() 

    return data

def remove_outliners(df):
    df = df[(df['temp'] > 0) & (df['temp'] < 100) &
             (df['humedad'] > 0) & (df['humedad'] < 100)]
    return df

def create_figures(selected_date=None):
    data = get_data(selected_date)
 
    # Crear la figura de temperatura y humedad
    temp_fig = go.Figure()
    hum_fig = go.Figure()
    last_temp =0
    last_hum = 0 
    if not data.empty:
        data['time_index'] = pd.to_datetime(data['time_index'], unit='ms')
        data = data.sort_values('time_index')
 
        timestamps = data['time_index']  
        temperature = data['temp']
        humidity = data['humedad']
 
        # Obtener la última temperatura y humedad
        last_temp = temperature.iloc[-1] 
        last_hum = humidity.iloc[-1] 

        # Crear la figura de temperatura
        temp_fig.add_trace(go.Scatter(x=timestamps, y=temperature, mode='lines+markers', name='Temperature'))
        temp_fig.update_layout(
            title='Temperatura Vs Tiempo',
            xaxis_title='Tiempo',
            yaxis_title='Temperatura (°C)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )
 
        # Crear la figura de humedad
        hum_fig.add_trace(go.Scatter(x=timestamps, y=humidity, mode='lines+markers', name='Humidity'))
        hum_fig.update_layout(
            title='Humedad Vs Tiempo',
            xaxis_title='Tiempo',
            yaxis_title='Humedad (%)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )
    else:
        temp_fig.update_layout(
            title='Temperatura Vs Tiempo',
            xaxis_title='Tiempo',
            yaxis_title='Temperatura (°C)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )
 
        hum_fig.update_layout(
            title='Humedad Vs Tiempo',
            xaxis_title='Tiempo',
            yaxis_title='Humedad (%)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )

    return temp_fig, hum_fig, last_temp, last_hum
# Función para conectarse a la base de datos
def connect_to_postgresql():

    username = 'julian'
    password = '123'
    host = 'localhost'
    port = '5432'
    database = 'data_front'

    try:
        connection = connect(
            user=username,
            password=password,
            host=host,
            port=port,
            database=database
        )
        print("Conexión exitosa a PostgreSQL")
        return connection
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

# Función para obtener datos de las dos tablas
def get_prediction_data():
    connection = connect_to_postgresql()

    if not connection:
        return pd.DataFrame(), pd.DataFrame()  # Retornar dos DataFrames vacíos si no se conecta correctamente

    # Consultas para obtener los datos de temperatura y humedad por separado
    query_temp = """
    SELECT entity_id, time_index, temp
    FROM predicciones_temp
    WHERE entity_id = 'julianor'
    ORDER BY time_index;
    """
    
    query_humidity = """
    SELECT entity_id, time_index, humedad
    FROM predicciones_humedad
    WHERE entity_id = 'julianor'
    ORDER BY time_index;
    """

    try:
        # Crear un cursor y ejecutar las dos consultas por separado
        cursor = connection.cursor()
        
        # Obtener predicciones de temperatura
        cursor.execute(query_temp)
        rows_temp = cursor.fetchall()
        temp_columns = ['entity_id', 'time_index', 'predicted_temp']
        data_temp = pd.DataFrame(rows_temp, columns=temp_columns)
        
        # Obtener predicciones de humedad
        cursor.execute(query_humidity)
        rows_humidity = cursor.fetchall()
        humidity_columns = ['entity_id', 'time_index', 'predicted_humedad']
        data_humidity = pd.DataFrame(rows_humidity, columns=humidity_columns)
        
        # Cerrar el cursor
        cursor.close()

        return data_temp, data_humidity

    except Exception as e:
        print(f"Error al ejecutar las consultas: {e}")
        return pd.DataFrame(), pd.DataFrame()  # En caso de error, retornar dos DataFrames vacíos

    finally:
        connection.close()

# Función para crear las gráficas de predicciones
def create_prediction_figures():
    # Obtener los datos de predicción de las dos tablas
    data_temp, data_humidity = get_prediction_data()
    
    # Crear figuras para temperatura y humedad
    pred_temp_fig = go.Figure()
    pred_hum_fig = go.Figure()
    
    if not data_temp.empty and not data_humidity.empty:
        # Procesar los datos de temperatura
        data_temp['time_index'] = pd.to_datetime(data_temp['time_index'], unit='ms')
        data_temp = data_temp.sort_values('time_index')

        timestamps_temp = data_temp['time_index']
        predicted_temp = data_temp['predicted_temp']

        # Crear la figura de temperatura
        pred_temp_fig.add_trace(go.Scatter(x=timestamps_temp, y=predicted_temp, mode='lines+markers', name='Predicted Temperature'))
        pred_temp_fig.update_layout(
            title='Temperatura Vs Tiempo',
            xaxis_title='Tiempo',
            yaxis_title='Temperatura (°C)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )

        # Procesar los datos de humedad
        data_humidity['time_index'] = pd.to_datetime(data_humidity['time_index'], unit='ms')
        data_humidity = data_humidity.sort_values('time_index')

        timestamps_humidity = data_humidity['time_index']
        predicted_humidity = data_humidity['predicted_humedad']

        # Crear la figura de humedad
        pred_hum_fig.add_trace(go.Scatter(x=timestamps_humidity, y=predicted_humidity, mode='lines+markers', name='Predicted Humidity'))
        pred_hum_fig.update_layout(
            title='Humedad Vs Tiempo',
            xaxis_title='Tiempo',
            yaxis_title='Humedad (%)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )
    else:
        # Si los datos están vacíos, configura las gráficas con un título genérico
        pred_temp_fig.update_layout(
            title='Predicted Temperature Over Time',
            xaxis_title='Time',
            yaxis_title='Temperature (°C)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )

        pred_hum_fig.update_layout(
            title='Predicted Humidity Over Time',
            xaxis_title='Time',
            yaxis_title='Humidity (%)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )
    
    return pred_temp_fig, pred_hum_fig

# Layout de la app
app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label='Información de la Planta', children=[
            html.Div([
                html.H1("Incienso (Plectranthus coleoides)", className='plantTitle'),
                html.Div([
                    html.Div([
                        html.Img(src='./assets/planta.jpeg', style={'width': '300px'}),
                    ], className='card center'),
                    html.Div([
                        html.H4("Historia"),
                        html.P("""
                            El Plectranthus coleoides 'Marginatus' o 'Incienso' es originario de las regiones tropicales de África, Asia y Australia. 
                            Con el tiempo, se ha popularizado en jardines y hogares de todo el mundo por su resistencia, 
                            fácil cuidado y su agradable fragancia. En muchas culturas, esta planta ha sido apreciada no solo como decoración, 
                            sino también por su asociación con la purificación del aire y la atracción de energías positivas.
                        """)
                    ], className='card'),
                    html.Div([
                        html.H4("Familia"),
                        html.P("""
                               La planta de incienso pertenece a la familia Lamiaceae, que también incluye otras plantas aromáticas como la menta, la albahaca y el romero. 
                               Esta familia es conocida por sus especies con hojas fragantes y un gran valor ornamental y culinario.
                                El género Plectranthus abarca alrededor de 300 especies, muchas de ellas utilizadas en jardinería por su adaptabilidad y belleza.
                        """)
                    ], className='card'),
                    html.Div([
                        html.H4("Temperatura Ideal"),
                        html.P("""
                               El Plectranthus coleoides prospera en temperaturas templadas, de entre 15 y 25 °C. Aunque es bastante resistente, no tolera heladas ni fríos extremos, 
                               por lo que debe ser protegida en interiores o en lugares sin exposición directa a cambios bruscos de temperatura. 
                               En climas cálidos, puede adaptarse fácilmente al aire libre, siempre que se mantenga en semisombra. Es muy sensible a las bajas temperaturas, por debajo de 13 ºC comienza a sufrir.
                        """)
                    ], className='card'),
                    html.Div([
                        html.H4("Cuidados"),
                        html.P("""
                               El Plectranthus coleoides prefiere lugares con buena iluminación, pero sin luz solar directa, ya que podría quemar sus hojas. 
                               Es una planta que necesita riego regular, manteniendo el sustrato ligeramente húmedo, pero no encharcado. 
                               Un suelo bien drenado y una maceta con agujeros son ideales para evitar el exceso de agua, 
                               que puede provocar la pudrición de las raíces.""")
                    ], className='card'),
                    
                    html.Div([
                        html.H4("Uso"),
                        html.P("""
                               El primer uso de la planta de incienso, y por el que se ha convertido en una planta tan popular, es su poder ornamental. 
                               Su porte y, especialmente sus hojas, son muy decorativas y aportan un aroma impresionante y embriagador.
                               Por otro lado, se suele utilizar el falso incienso en fitoterapia y aromaterapia ya que relaja y alivia cuerpo y mente. 
                               Además, según ciertas creencias populares se le atribuye la capacidad de atraer la buena energía.
                               """)
                    ], className='card'),
                    html.Div([
                        html.H4("Características Especiales"),
                        html.P("""
                            Esta planta destaca por su atractivo follaje, con hojas verdes bordeadas en blanco, lo que le otorga un aspecto decorativo único. 
                            Además, su fragancia suave hace que se le considere como un "incienso vivo" ideal para aromatizar espacios de forma natural. 
                            Es una planta colgante, lo que la hace perfecta para macetas elevadas o colgantes, y es capaz de refrescar y embellecer el ambiente de cualquier hogar.
                        """)
                    ], className='card'),
                    html.Div([
                        html.H4("Condiciones de Crecimiento"),
                        html.P("""
                            El Plectranthus coleoides se adapta bien a lugares con buena iluminación indirecta, aunque también puede tolerar sombra parcial. 
                            Es fundamental que el suelo sea bien drenado y ligeramente ácido para asegurar su crecimiento óptimo. 
                            Esta planta requiere riegos regulares, sin encharcar el sustrato, ya que el exceso de agua puede causar problemas de pudrición en las raíces.
                        """)
                    ], className='card')
                ], className='cards-div')
            ], className='margins'),
        ]),
        dcc.Tab(label='Gráficas de Temperatura y Humedad', children=[
            html.Div([
                html.H1("Datos históricos"),
                html.Label("Fecha:"),
                dcc.DatePickerSingle(
                    id='date-picker',
                    date=pd.to_datetime("today").date(),  
                    display_format='YYYY-MM-DD'
                ),
                html.Div([
                    html.Div(id='temp-indicator'),
                    html.Div(id='hum-indicator'),
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginTop': '20px'}),
                html.Div([
                    html.H2("Temperatura"),
                    dcc.Graph(id="temperature-graph")
                ]),
                
                # Div para el gráfico de humedad
                html.Div([
                    html.H2("Humedad"),
                    dcc.Graph(id="humidity-graph")
                ]),
                dcc.Interval(
                    id='interval-component',
                    interval=60*1000,  # Actualizar cada 60 segundos
                    n_intervals=0
                )
            ], className='margins')
        ]),
        dcc.Tab(label='Predicciones', children=[
            html.Div([
                html.H1("Predicciones de Temperatura y Humedad"),
                html.Div([
                    html.H2("Temperatura Predicha"),
                    dcc.Graph(id="pred-temperature-graph")
                ]),
                html.Div([
                    html.H2("Humedad Predicha"),
                    dcc.Graph(id="pred-humidity-graph")
                ]),
                dcc.Interval(
                    id='pred-interval-component',
                    interval=60*1000,
                    n_intervals=0
                )
            ], className='margins')
        ]),
    ], className='margins')
], className="fondo")

@callback(
    [Output('temperature-graph', 'figure'),
     Output('humidity-graph', 'figure'),
     Output('temp-indicator', 'children'),
     Output('hum-indicator', 'children')],
    [Input('date-picker', 'date'),
     Input('interval-component', 'n_intervals')]
)
def update_graphs(selected_date, n_intervals):
    temp_fig, hum_fig, last_temp, last_hum = create_figures(selected_date)
    
    # Crear los indicadores de temperatura y humedad
    temp_indicator = dcc.Graph(
        figure=go.Figure(go.Indicator(
            mode="number+gauge",
            value=last_temp,
            title={'text': "Última Temperatura (°C)"},
            gauge={'axis': {'range': [None, 100]},  # Ajusta el rango según tus datos
                   'bar': {'color': "orange"},
                   'steps': [{'range': [0, 100], 'color': "lightgray"}]}
        ))
    )
    
    hum_indicator = dcc.Graph(
        figure=go.Figure(go.Indicator(
            mode="number+gauge",
            value=last_hum,
            title={'text': "Última Humedad (%)"},
            gauge={'axis': {'range': [None, 100]},  # Ajusta el rango según tus datos
                   'bar': {'color': "blue"},
                   'steps': [{'range': [0, 100], 'color': "lightgray"}]}
        ))
    )

    return temp_fig, hum_fig, temp_indicator, hum_indicator

@callback(
    [Output('pred-temperature-graph', 'figure'),
     Output('pred-humidity-graph', 'figure')],
    [Input('pred-interval-component', 'n_intervals')]
)
def update_prediction_graphs(n_intervals):
    pred_temp_fig, pred_hum_fig= create_prediction_figures()

    return pred_temp_fig, pred_hum_fig


# Ejecutar la app
if __name__ == '__main__':
    app.run_server(debug=True, port=5000, host='0.0.0.0')


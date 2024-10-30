import dash
from dash import dcc, html, callback
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from sqlalchemy import create_engine
import numpy as np

# Inicializar la app
app = dash.Dash(__name__)

# Conexión a CrateDB
db_url = 'crate://10.38.32.137:8083/'
engine = create_engine(db_url)

# Consulta de datos históricos desde CrateDB
def get_data(selected_date=None):
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
    data = pd.read_sql(query, con=engine)
    return data

def create_figures(selected_date=None):
    data = get_data(selected_date)
 
    # Crear la figura de temperatura y humedad
    temp_fig = go.Figure()
    hum_fig = go.Figure()

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
            title='Temperature Over Time',
            xaxis_title='Time',
            yaxis_title='Temperature (°C)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )
 
        # Crear la figura de humedad
        hum_fig.add_trace(go.Scatter(x=timestamps, y=humidity, mode='lines+markers', name='Humidity'))
        hum_fig.update_layout(
            title='Humidity Over Time',
            xaxis_title='Time',
            yaxis_title='Humidity (%)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )
    else:
        temp_fig.update_layout(
            title='Temperature Over Time',
            xaxis_title='Time',
            yaxis_title='Temperature (°C)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )
 
        hum_fig.update_layout(
            title='Humidity Over Time',
            xaxis_title='Time',
            yaxis_title='Humidity (%)',
            xaxis_tickangle=-45,
            xaxis=dict(tickformat="%H:%M", type='date')
        )

    return temp_fig, hum_fig, last_temp, last_hum

# Layout de la app
app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label='Información de la Planta', children=[
            html.Div([
                html.H1("Nombre de la Planta", className='plantTitle'),
                html.Div([
                    html.Div([
                        html.Img(src='ruta/a/la/imagen.jpg', style={'width': '300px'}),
                    ], className='card center'),
                    html.Div([
                        html.H4("Historia"),
                        html.P("Aquí va la historia de la planta.")
                    ], className='card'),
                    
                    html.Div([
                        html.H4("Temperatura Ideal"),
                        html.P("La temperatura ideal es de 20-25°C.")
                    ], className='card'),
                    
                    html.Div([
                        html.H4("Humedad"),
                        html.P("La humedad ideal es del 60-70%.")
                    ], className='card'),
                    
                    html.Div([
                        html.H4("Cuidados"),
                        html.P("Los cuidados incluyen riego regular y luz indirecta.")
                    ], className='card'),
                    
                    html.Div([
                        html.H4("Uso"),
                        html.P("Se utiliza comúnmente para decoraciones y purificación del aire.")
                    ], className='card'),
                    html.Div([
                        html.H4("Uso"),
                        html.P("Se utiliza comúnmente para decoraciones y purificación del aire.")
                    ], className='card'),
                    html.Div([
                        html.H4("Uso"),
                        html.P("Se utiliza comúnmente para decoraciones y purificación del aire.")
                    ], className='card'),
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
                ], style={'display': 'flex', 'justify-content': 'space-between'}),
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
        dcc.Tab(label='Tab 3', children=[
            html.Div([
                html.H1("Contenido del Tab 3")
            ], className='margins')
        ])
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

# Ejecutar la app
if __name__ == '__main__':
    app.run_server(debug=True)

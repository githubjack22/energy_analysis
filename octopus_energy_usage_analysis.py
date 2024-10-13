import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import base64
import io

# Define the data processing function from the uploaded file
def process_data(df, start_hour, end_hour, start_date, end_date):
    df.columns = [c.strip() for c in df.columns]
    df['Start'] = pd.to_datetime(df['Start'])
    df['End'] = pd.to_datetime(df['End'])
    df['date'] = df['Start'].dt.date
    df['hour'] = df['Start'].dt.hour
    df = df[df['date'].between(datetime.strptime(start_date, '%Y-%m-%d').date(),
                            datetime.strptime(end_date, '%Y-%m-%d').date())]#show only the selected days


    df['base_period'] = df['hour'].between(start_hour,end_hour)
    df_base_avg = df[df['base_period']==1]\
        .groupby(['date'])[['Consumption (kwh)','Estimated Cost (p)']]\
        .mean()*2
    df_base_avg.reset_index(inplace=True)
    df_base_all = df_base_avg.copy()
    df_base_all[['Consumption (kwh)','Estimated Cost (p)']] = df_base_all[['Consumption (kwh)','Estimated Cost (p)']]*24
    df_ttl = df.groupby('date')[['Consumption (kwh)','Estimated Cost (p)']].sum()
    df_ttl.reset_index(inplace=True)
    df_final = df_ttl.merge(df_base_all,on='date',how='inner',suffixes=('_ttl','_base'))
    for i in ['Consumption (kwh)','Estimated Cost (p)']:
        df_final[f'{i}_base'] = np.round(df_final[f'{i}_base'],2)
        df_final[f'{i}_extra'] = np.round(df_final[f'{i}_ttl'] - df_final[f'{i}_base'],2)
        df_final[f'{i}_base%'] = np.round(df_final[f'{i}_base']/df_final[f'{i}_ttl'],4)*100         

    df_final = df_final[df_final['Consumption (kwh)_base%']<100]
    df_final['date'] = pd.to_datetime(df_final['date'])
    df_final['DayofWeek'] = df_final['date'].dt.day_name().str[0:3]
    df_final['date_DayofWeek'] = df_final['date'].dt.strftime('%m-%d').str.cat(df_final['DayofWeek'], sep=' ')
    return df_final

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of the Dash app
app.layout = html.Div([
    html.H1("Energy Consumption and Cost Analysis", style={'textAlign': 'center', 'color': '#b2f0fd'}),
    #add description
    html.Div(
    children=[
        html.P(
            [""" Paying high energy bills when you don't even use any energy actively? 
                This page offers you an opportunity to understand your energy usage better. """,
            html.Br(),
            """How does this work? Simply Provide your octopus half-hourly energy consumption data, 
            and type in the period of interest.""", 
            """Tell us the time period when you don't actively use any energy and we'll sort out the rest. """
            ]
        )
    ],
    style={'textAlign': 'justify', 'color': 'white', 'fontSize': 18, 'margin': '0 auto',
           'width': '60%', 'whiteSpace': 'normal', 'wordWrap': 'break-word'}
    ),
    # File upload component
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select a File')]),
        style={
            'width': '50%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center', 'margin': '10px auto', 'color': '#b2f0fd'
        },
        multiple=False
    ),


    # User input for start and end date
    html.Div([
    # Text before input
        html.P("Select the date range of analysis:",
            style={'textAlign': 'left', 'color': 'white', 'marginRight': '10px',
                    'display': 'inline-block', 'width': '200px'}),

        # Input for start date
        dcc.Input(id='start-date', type='text', placeholder='Start Date (YYYY-MM-DD)',
                style={'display': 'inline-block', 'width': '150px'}),

        # Input for end date
        dcc.Input(id='end-date', type='text', placeholder='End Date (YYYY-MM-DD)',
                style={'display': 'inline-block', 'width': '150px'}),
        ], style={'textAlign': 'left', 'margin': '10px','paddingLeft': '400px'}),

# User input for start and end hour
    html.Div([
        html.P("Select your inactive time:",
            style={'textAlign': 'left', 'color': 'white', 'marginRight': '10px',
                    'display': 'inline-block', 'width': '200px'}),

        dcc.Input(id='start-hour', type='number', placeholder='Start Hour (0-23)',
                style={'display': 'inline-block', 'width': '150px'}),

        dcc.Input(id='end-hour', type='number', placeholder='End Hour (0-23)',
                style={'display': 'inline-block', 'width': '150px'}),
        ], style={'textAlign': 'left', 'margin': '10px','width': '50%','paddingLeft': '400px'}),

    # Dropdown to select between 'Daily Consumption' and 'Daily Cost'
    html.Div([
        html.P("Select analysis type:",
            style={'textAlign': 'left', 'color': 'white', 'marginRight': '10px',
                    'display': 'inline-block', 'width': '200px'}),

        dcc.Dropdown(
            id='dropdown-selection',
            options=[
                {'label': 'Daily Consumption', 'value': 'consumption'},
                {'label': 'Daily Cost', 'value': 'cost'}
            ],
            placeholder="Select analysis type",
            style={'display': 'inline-block', 'width': '150px'}
        )
        ], style={'textAlign': 'left', 'margin': '10px','width': '50%','paddingLeft': '400px'}),

    # Graph to display the visualizations
    dcc.Graph(id='graph-output')
],
style={'backgroundColor': '#260e3d', 'padding': '20px',
    'height': '100vh','width': '100vw','boxSizing': 'border-box'})

# Function to parse uploaded file content
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None
    except Exception as e:
        print(e)
        return None
    
    return df

# Define callback to update the file status
@app.callback(
    Output('upload-data', 'children'),
    Input('upload-data', 'filename')
)

def update_upload_area(filename):
    if filename is not None:
        return html.Div(f"Uploaded File: {filename}", style={'color': '#b2f0fd'})
    return html.Div(['Drag and Drop or ', html.A('Select a File')])

# Define callback to update the graph based on file upload and user input
@app.callback(
    Output('graph-output', 'figure'),
    [Input('upload-data', 'contents'),
     Input('dropdown-selection', 'value'),
     Input('start-hour', 'value'),
     Input('end-hour', 'value'),
     Input('start-date', 'value'),
     Input('end-date', 'value')],
    [State('upload-data', 'filename')]
)
def update_graph(contents, selected_view, start_hour, end_hour, start_date, end_date, filename):
    if contents is not None:
        df_initial = parse_contents(contents, filename)
        if df_initial is None:
            fig = go.Figure()
            fig.update_layout(font=dict(color='grey'),
            xaxis_tickangle=-90, plot_bgcolor='#260e3d', paper_bgcolor='#260e3d', 
            margin=dict(l=20, r=20, t=50, b=50),
            xaxis=dict(showgrid=False, zeroline=False),  # Ensure x-axis gridline is disabled
            yaxis=dict(showgrid=False, zeroline=False))   # Ensure y-axis gridline is disabled)
            return fig  # Return empty figure if parsing failed
        
        # Validate user inputs
        if start_hour is None or end_hour is None or not start_date or not end_date:
            fig = go.Figure()
            fig.update_layout(font=dict(color='grey'),
            xaxis_tickangle=-90, plot_bgcolor='#260e3d', paper_bgcolor='#260e3d', 
            margin=dict(l=20, r=20, t=50, b=50),
            xaxis=dict(showgrid=False, zeroline=False),  # Ensure x-axis gridline is disabled
            yaxis=dict(showgrid=False, zeroline=False))   # Ensure y-axis gridline is disabled)
            return fig  # Return empty figure if parsing failed

        # Process data using the provided `process_data` function
        df_final = process_data(df_initial, start_hour, end_hour, start_date, end_date)

        # Create the figure based on the selected view
        fig = go.Figure()
        if selected_view == 'consumption':
            fig.add_trace(go.Bar(x=df_final['date_DayofWeek'], y=df_final['Consumption (kwh)_base'],
                name='Base Consumption', marker_color='#b2f0fd',marker_line_color='black',marker_line_width=1,opacity=0.75))
            fig.add_trace(go.Bar(x=df_final['date_DayofWeek'], y=df_final['Consumption (kwh)_extra'],
                name='Extra Consumption', marker_color='#f144f1',marker_line_color='black',marker_line_width=1,opacity=0.75))
            fig.update_layout(title='Daily Consumption', yaxis_title='Consumption (kwh)', barmode='group')
        elif selected_view == 'cost':
            fig.add_trace(go.Bar(x=df_final['date_DayofWeek'], y=df_final['Estimated Cost (p)_base'], 
                name='Base Cost', marker_color='#b2f0fd',marker_line_color='black',marker_line_width=1,opacity=0.75))
            fig.add_trace(go.Bar(x=df_final['date_DayofWeek'], y=df_final['Estimated Cost (p)_extra'], 
                name='Extra Cost', marker_color='#f144f1',marker_line_color='black',marker_line_width=1,opacity=0.75))
            fig.update_layout(title='Daily Cost', yaxis_title='Estimated Cost (p)', barmode='group')
        
        fig.update_layout(xaxis_title='Date', font=dict(color='grey'), legend_title_text='Type',
            xaxis_tickangle=-90, plot_bgcolor='#260e3d', paper_bgcolor='#260e3d', 
            margin=dict(l=20, r=20, t=50, b=50),barcornerradius=15)
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
        return fig

    fig = go.Figure()
    fig.update_layout(font=dict(color='grey'),
    xaxis_tickangle=-90, plot_bgcolor='#260e3d', paper_bgcolor='#260e3d', 
    margin=dict(l=20, r=20, t=50, b=50),
    xaxis=dict(showline=False,showticklabels=False,
        ticks='',showgrid=False, zeroline=False),  
    yaxis=dict(showline=False,showticklabels=False,
        ticks='',showgrid=False, zeroline=False))   
    return fig

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
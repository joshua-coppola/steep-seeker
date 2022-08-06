import dash
from dash import html, dcc, callback, Input, Output

dash.register_page(__name__, path='/')

layout = html.Div(children=[
    html.H3(children='This is test content to get a feel for Dash'),
    html.Div([
        "Select a city: ",
        dcc.RadioItems(['New York City', 'Montreal', 'San Francisco'],
                       'Montreal',
                       id='analytics-input')
    ]),
    html.Br(),
    html.Div(id='analytics-output'),
])


@callback(
    Output(component_id='analytics-output', component_property='children'),
    Input(component_id='analytics-input', component_property='value')
)
def update_city_selected(input_value):
    if input_value == 'San Francisco':
        return 'yeah...'
    return f'You selected: {input_value}'

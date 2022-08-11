import dash
from dash import html, dcc, callback, Input, Output

dash.register_page(__name__, path='/')

layout = html.Div(children=[
    html.H3(children='This is test content to get a feel for Dash'),
    html.Div([
        "Select a city: ",
        dcc.RadioItems(['New York City', 'Montreal', 'San Francisco'],
                       'Montreal',
                       id='test-input')
    ]),
    html.Br(),
    html.Div(id='test-output'),
])


@callback(
    Output(component_id='test-output', component_property='children'),
    Input(component_id='test-input', component_property='value')
)
def update_city_selected(input_value):
    if input_value == 'San Francisco':
        return 'yeah...'
    return f'You selected: {input_value}'

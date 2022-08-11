import dash
from dash import html, dcc, callback, Input, Output, ctx

dash.register_page(__name__)

layout = html.Div(children=[
    html.Br(),
    html.H3(children='Management Panel'),
    html.Div([
        "Select an operation: ",
        dcc.RadioItems(['Add Resort', 'Edit Resort', 'Delete Resort'],
                       'Add Resort',
                       id='operation-input')
    ]),
    html.Div([
        "Enter resort name: ",
        dcc.Input(id='name-input', value='', type='text')
    ]),
    html.Button("Submit", id='submit-button'),
    html.Br(),
    html.Div(id='name-output')
])


@callback(
    Output(component_id='name-output', component_property='children'),
    Input(component_id='name-input', component_property='value'),
    Input(component_id='operation-input', component_property='value'),
    Input(component_id='submit-button', component_property='n_clicks')
)
def update_name_entered(name, operation, n):
    if 'submit-button' == ctx.triggered_id:
        return html.Div([
            html.P(f'You selected: {name}, {operation}'),
            html.P('Testing')
        ])

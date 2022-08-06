# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

from dash import Dash, html, dcc
import dash

external_stylesheet = [
    'https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/css/bootstrap.min.css']

app = Dash(__name__, use_pages=True, external_stylesheets=external_stylesheet)

app.layout = html.Div([
    html.H1('Steep Seeker'),
    html.P('Provides skiers with a universal rating system to compare trails and resorts'),

    html.Div(
        [
            html.Div(
                dcc.Link(
                    f"{page['name']} - {page['path']}", href=page["relative_path"]
                )
            )
            for page in dash.page_registry.values()
        ]
    ),

    dash.page_container
])

if __name__ == '__main__':
    app.run_server(debug=True)

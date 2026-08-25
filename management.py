from core.web.management_app import create_management_app

app = create_management_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

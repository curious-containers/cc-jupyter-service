from cc_jupyter_service.service.app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()

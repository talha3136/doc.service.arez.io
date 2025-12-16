from app import create_app

flask_app = create_app()
app = flask_app.extensions["celery"]

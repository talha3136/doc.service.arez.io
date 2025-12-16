from celery import Celery, Task
from flask import Flask

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config, namespace='CELERY')
    celery_app.conf.update(
        broker_url=app.config.get("CELERY_BROKER_URL"),
        result_backend=app.config.get("CELERY_RESULT_BACKEND"),
    )
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    
    # Ensure database connections are closed after each task
    from celery.signals import task_postrun
    from .services.vector_db import close_all_connections
    
    @task_postrun.connect
    def close_db_connection(*args, **kwargs):
        close_all_connections()
        
    return celery_app

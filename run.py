from app import create_app
from app.services.vector_db import close_all_connections
import atexit

app = create_app()

# Ensure database connections are closed on exit
atexit.register(close_all_connections)

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)
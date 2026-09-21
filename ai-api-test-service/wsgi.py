import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '8003'))
    app.run(host=host, port=port, debug=os.environ.get('FLASK_DEBUG') == '1')

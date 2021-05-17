# -*- coding: UTF-8 -*-
from flask import Flask
app = Flask(__name__)

@app.route('/')
def main():
    return 'Hello, world!'

if __name__ == '__main__':
    print("Hello, World. Uses S2I to build the application.")
    app.run(host="0.0.0.0", port=4000, debug=True,use_reloader=True)

from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


if __name__ == "__main__":
    ip = '192.168.35.130'
    port = 5555
    app.run(host=ip, port=port, debug=True)
    # flak run --host=ip --port=5555
    # app.run(debug=True)

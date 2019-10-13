from flask import Flask
from flask import request

app = Flask(__name__)

currentRelaxValue = 0
currentThreshold = 0
updown_value = 0
welcome =  "Hello, i'm gonna read your mind!"

@app.route("/")
def hello():
    return welcome

@app.route('/relax', methods = ['GET', 'POST'])
def relax():
    if request.method == 'GET':
        global currentRelaxValue
        return str(currentRelaxValue)
    elif request.method == 'POST':
        print(request.form['value'])
        currentRelaxValue = request.form['value']
        return str(200)

@app.route('/threshold', methods = ['GET', 'POST'])
def threshold():
    if request.method == 'GET':
        global currentThreshold
        return str(currentThreshold)
    elif request.method == 'POST':
        print(request.form['value'])
        currentThreshold = request.form['value']
        return str(200)

@app.route('/updown', methods = ['GET', 'POST'])
def subebaja():
    if request.method == 'GET':
        global updown_value
        return str(updown_value)
    elif request.method == 'POST':
        print(request.form['value'])
        updown_value = request.form['value']
        return str(200)

if __name__ == "__main__":
    app.run(processes=10,debug=True)
from __main__ import app

@app.route('/check', methods=['GET'])
def check():
    return 'Ceci est l\'endpoint 1'
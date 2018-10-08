#Importing Python Libraries 
from flask import Flask, render_template, request, jsonify, abort
import cf_deployment_tracker
import os
import json
import requests
import numpy as np

#Importing Tensorflow
import tensorflow as tf

#Importing the Watson Machine Learning Client API and the libraries for preprocessing the uploaded images
from watson_machine_learning_client import WatsonMachineLearningAPIClient
from keras.preprocessing import image
from keras.applications.inception_v3 import decode_predictions, preprocess_input
from io import BytesIO

# Emit Bluemix deployment event
cf_deployment_tracker.track()

app = Flask(__name__)
BASE = './assets/'

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

# Inception v3 initial parameters.

INPUT_LAYER = 'Mul'
INPUT_HEIGHT = 299
INPUT_WIDTH = 299


# Load your WML Credentials here.
wml_credentials={
  "Insert your WML credentials here"
}

#Creating an instance to run the WML API Client with the Tensorflow model
client = WatsonMachineLearningAPIClient(wml_credentials)
client._refresh_token()

#The REST API URL provided by your WML instance
scoring_url = "Insert your WML scoring URL"

# On Bluemix, get the port number from the environment variable PORT
# When running this app on the local machine, default the port to 8000
port = int(os.getenv('PORT', 8000))


@app.route('/')
def home():
    return render_template('index.html')

#Function which receives the image and post to the rest api 
@app.route('/api/classify', methods=['POST'])
def upload_image():
    if request.json:
        # TODO validation.
        print(request.json['url'])
        # Spoof User-Agent as some websites don't like non-browser requests.
        headers = {'User-Agent':
                   'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/64.0.3282.140 Safari/537.36'}
        resp = requests.get(request.json['url'], headers=scoring_eader)
        if resp.status_code == 200:
            scores = run_model(resp.content)
            return jsonify(scores)
        else:
            abort(400, 'Server could not access image at given url.')
    elif request.files:
        if 'file' not in request.files:
            abort(400, '"file" key not in part.')
        file = request.files['file']
        if not file.filename:
            abort(400, 'No selected file.')
        if file and allowed_file(file.filename):
            image_data = file.read()
            scores = run_model(image_data)
            return jsonify(scores)
    else:
        abort(400)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Function to preprocess the images, which includes sizing to the Inception V3 required dimensions and normalization
def adjust_image(image_contents, input_height=299, input_width=299,
                 input_mean=128, input_std=128):
    image_reader = tf.image.decode_image(image_contents, channels=3)
    float_caster = tf.cast(image_reader, tf.float32)
    dims_expander = tf.expand_dims(float_caster, 0)
    resized = tf.image.resize_bilinear(dims_expander, [input_height, input_width])
    normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])
    with tf.Session() as ses:
        result = ses.run(normalized)
    return result

#Running the model with the image preprocessed
def run_model(image_data):
    image_data = BytesIO(image_data)
    img = image.load_img(image_data,target_size=(299,299))
    input_image = image.img_to_array(img)
    input_image = np.expand_dims(input_image, axis=0)
    input_image = preprocess_input(input_image).tolist()
    #Image vectorized as payload 
    scoring_data = {'values': input_image}
    #The Scoring URL
    score = client.deployments.score(scoring_url, scoring_data)
    return score

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)

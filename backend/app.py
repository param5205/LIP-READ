"""
app.py - Flask backend API for the lip reading model.

Run:   python app.py
Test:  curl -X POST -F "video=@sample.mp4" http://127.0.0.1:5000/predict
"""
import os
import tempfile

from flask import Flask, jsonify, request
from flask_cors import CORS

from predict import get_model, predict_video

app = Flask(__name__)
CORS(app)  # lets your frontend (React/HTML) call this API from another origin
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload limit

ALLOWED_EXT = {".mp4", ".webm", ".avi", ".mov"}

get_model()  # load the model at startup so the first request is fast


@app.get("/")
def health():
    return jsonify(status="ok")


@app.post("/predict")
def predict():
    if "video" not in request.files:
        return jsonify(error="Send the video as form-data with key 'video'."), 400

    file = request.files["video"]
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify(error=f"Unsupported file type. Use one of {sorted(ALLOWED_EXT)}."), 400

    # OpenCV reads from a path, so save to a temp file first
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        file.save(tmp)
        path = tmp.name

    try:
        text = predict_video(path)
    except ValueError as e:                      # e.g. no face detected
        return jsonify(error=str(e)), 422
    except Exception:
        app.logger.exception("Prediction failed")
        return jsonify(error="Internal error while processing the video."), 500
    finally:
        os.remove(path)

    return jsonify(prediction=text)


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="File too large (max 20 MB)."), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
# LIP-READ - Automated Lip Reading System

## Project Overview
This project aims to develop a deep learning based system that can read lips from video and convert it into text without using audio. The user can upload a video or record via webcam, and the system predicts the spoken text.

## Team Members
- Member Jiya - Data Collection & Preprocessing
- Member Param - Model Development & Backend
- Member Kanishka - Frontend & Documentation

## Tech Stack
- Frontend: HTML, CSS, JavaScript, MediaPipe FaceMesh (lips-only tracking), IndexedDB
- Backend: Python, Flask
- Machine Learning: 3D CNN + BiGRU, CTC loss, OpenCV, MediaPipe
- Tools: VS Code, Kaggle, 【entity-GitHub¦canonical_name=GitHub】, 【entity-GitHub¦canonical_name=GitHub】 Pages

## Folder Structure
LIP-READ/
├── index.html      - Frontend: Landing + Upload + Live Camera
├── style.css       - Frontend: Landing styles
├── script.js       - Frontend: Camera, recording, backend connection, IndexedDB
├── result.html     - Frontend: Result page (video + text + translation)
├── result.css      - Frontend: Result page styles
├── result.js       - Frontend: Translation, TTS, video playback from IndexedDB
├── images/
│   └── Ai.png      - Logo / Hero image
├── backend/        - Flask API + ML model
│   ├── app.py
│   ├── model.py
│   ├── predict.py
│   ├── preprocess.py
│   ├── train.py
│   ├── test.py
│   ├── live.py
│   └── requirements.txt
├── model/ (trained weights - not uploaded)
├── data/ (dataset - not uploaded)
└── README.md

## Frontend (UI + Lip Tracking)

The frontend is built with plain HTML/CSS/JS for easy 【entity-GitHub¦canonical_name=GitHub】 Pages hosting. No audio is captured - only lip movements.

Features:
- Landing Page: Grid background + blue blur blobs, centered hero, fully responsive
- Upload Video: Drag & drop / browse, supports mp4/webm/avi/mov
- Live Camera: Video-only recording (audio: false), real-time lip dots using MediaPipe FaceMesh v0.4.1633559619, Muh Khula / Closed status
- Result Page: Shows video from IndexedDB (no 5MB localStorage issue), predicted text, Hindi/English/Spanish translation, Speak & Copy

Key Fixes Done:
- Video saved in IndexedDB (not localStorage) to support large files
- onplay handler attached before vid.play() so upload analysis starts
- Translation sends only predicted sentence, not full report
- English->English translation skipped
- Live text resets when mouth closes
- CDN scripts version pinned, cleanup on goHome()

How to Run Frontend:
python -m http.server 8000
Open http://localhost:8000

## Backend (model + API)

The backend/ folder contains the lip reading model, training and testing scripts, prediction, live webcam mode and the Flask API.

Files:
- model.py: 3D CNN + BiGRU lip reading model (CTC loss)
- preprocess.py: Mouth cropping, preprocessing and decoding
- train.py: Trains the model and saves best weights to lipreader.pt
- test.py: Evaluates model on test split (CER and WER)
- predict.py: Runs trained model on a video
- live.py: Real-time lip reading from webcam
- app.py: Flask API

Setup:
cd backend
pip install -r requirements.txt
python app.py

First run downloads face_landmarker.task (needs internet once).

Dataset format:
backend/data/videos/clip001.mp4
backend/data/labels/clip001.txt

Usage:
python train.py
python test.py
python predict.py path/to/video.mp4
python live.py
python app.py

API:
POST http://127.0.0.1:5000/predict
Form-data key: video (mp4/webm/avi/mov, up to 20MB)
Success: {"prediction": "text"}
Error: {"error": "message"} -> 400, 413, 422, 500

Status: Code complete, model not trained yet (needs dataset).

## Full Setup (Frontend + Backend Connected)

1. Clone repo:
git clone https://github.com/param5205/LIP-READ.git
cd LIP-READ

2. Run Backend (Terminal 1):
cd backend
pip install -r requirements.txt
python app.py

3. Run Frontend (Terminal 2):
cd ..
python -m http.server 8000
Open http://localhost:8000
Frontend will POST video to http://localhost:5000/predict

If backend is not running, frontend shows honest message: "Backend connect nahi ho raha" instead of fake text.

## Current Status
Frontend: Done (GitHub Pages ready)
Backend: Code complete, training pending
Integration: Frontend -> POST /predict -> IndexedDB playback -> Translation

# LIP-READ: Automated Lip Reading System

A deep learning system that reads lip movements from a video and converts them into text.
Built by a team of three as a college project.

## Team
| Member | Module |
|---|---|
| Jiya | Module 1: dataset handling and preprocessing tools |
| Param | Module 2: model, training, testing, prediction, Flask backend |
| Kanishka | Module 3: frontend and documentation |

## How it works
1. The user uploads a video (or records one with the webcam) on the web page.
2. The page sends the clip to the Flask API (`POST /predict`).
3. The backend finds the face with MediaPipe and crops the mouth region.
4. The mouth frames (75 frames, grayscale, 96x96) go through a 3D CNN + bidirectional GRU model trained with CTC loss.
5. The output is decoded into text and shown on the result page, where it can be translated, spoken or copied.

## Tech stack
- Frontend: HTML, CSS, JavaScript, MediaPipe (face overlay)
- Backend: Python, Flask, PyTorch, OpenCV, MediaPipe
- Tools: VS Code, Git, GitHub, Kaggle

## Folder structure
```
LIP-READ/
├── index.html, script.js, style.css     Frontend: home page (upload / live camera)
├── result.html, result.js, result.css   Frontend: result and translation page
├── backend/                             Module 2: model and Flask API
│   ├── model.py            3D CNN + BiGRU model
│   ├── preprocess.py       mouth cropping, text encoding and decoding
│   ├── train.py            training
│   ├── test.py             evaluation (CER and WER)
│   ├── predict.py          prediction from one video
│   ├── live.py             real-time webcam lip reading
│   ├── app.py              Flask API
│   ├── convert_grid.py     converts the GRID download into the training format
│   └── requirements.txt
├── preprocessing.py, dataset_management.py,
│   run_module1.py, requirements_module1.txt   Module 1 tools
├── README_MODULE1.md                    Module 1 notes
└── README.md
```
The dataset and the trained weights (`backend/lipreader.pt`) are not stored in the repository.

## Setup
```
git clone https://github.com/param5205/LIP-READ.git
cd LIP-READ/backend
python -m venv venv
venv\Scripts\activate            # Windows (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```
The first run downloads a small face-landmark model (`face_landmarker.task`), so an internet connection is needed once. After that everything runs offline, except the translation on the result page.

## Dataset
We use the GRID corpus from Kaggle (about 14 GB). It is too large for GitHub, so each person downloads it separately. Videos are grouped by speaker (`data/s1_processed/*.mpg`), with labels in `data/s1_processed/align/*.align`.

Convert it to the format the training code reads:
```
python convert_grid.py --videos "path\to\archive\data" --out path\to\output --speakers s1 s2 s3 s4
```
Use `--limit 50` for a quick test. The converter writes:
```
<output>/videos/s1_bbaf2n.mp4
<output>/labels/s1_bbaf2n.txt     (the spoken sentence, lowercase)
```
Then make the code find it as `backend/data/videos` and `backend/data/labels` (copy the folders there, or on Windows link them with `mklink /J`).

## Training and testing (run inside `backend/`)
```
python train.py                      # train and save the best weights to lipreader.pt
python test.py                       # evaluate on held-out clips (CER and WER)
python predict.py path/to/video.mp4  # predict from one video
python live.py                       # live lip reading with the webcam
```
A GPU is strongly recommended for training (for example a free Kaggle notebook).

## Run the app
1. Start the backend from `backend/`: `python app.py` (runs on http://127.0.0.1:5000).
2. Open `index.html` from the project root in a browser.
3. Choose **Upload Video** or **Live Camera** and click Analyze.

The backend needs a trained `lipreader.pt` in `backend/`.

## API
`POST http://127.0.0.1:5000/predict`
- Body: form-data, key `video` (mp4, webm, avi or mov, up to 20 MB)
- Success: `{"prediction": "text"}`
- Error: `{"error": "message"}` with status 400, 413, 422 or 500

## Results
Trained for 30 epochs on GRID speakers and tested on 400 held-out clips:

| Test clips | CER | WER |
|---|---|---|
| 400 | 8.79% | 26.62% |

CER = character error rate, WER = word error rate (lower is better). Most errors are single letters that look alike on the lips, for example reading `o` instead of `f`.

## Module 1 tools (Jiya)
```
pip install -r requirements_module1.txt
python run_module1.py preprocess video.mp4 --output processed/video_frames.npy
python run_module1.py manifest path/to/dataset
python run_module1.py inventory path/to/dataset
```
See `README_MODULE1.md` for details.

## Limitations
- The test clips come from the same speakers as the training clips, so accuracy on a new person's face will be lower.
- The model learned the fixed sentence pattern and small vocabulary of GRID, so it cannot read free speech. Open-vocabulary reading needs a large pretrained model.
- Lip reading is inherently ambiguous, because many sounds look alike on the lips.
- The video replay on the result page may stay empty for GRID `.mp4` clips, because browsers cannot play their older video format. The prediction is not affected.

## Future work
- Train on more speakers and test on speakers the model has not seen.
- Use a large pretrained model (such as Auto-AVSR) for open-vocabulary reading.
- Add a language model to correct similar-looking words.
- Deploy the backend to the cloud.

## Status
- Backend, API and frontend are complete and connected.
- The model is trained (30 epochs), with the results above.

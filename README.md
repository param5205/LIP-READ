# LIP-READ: Automated Lip Reading System

A deep learning system that reads lip movements from a video and converts them into text.
Built by a team of three as a college project.

## Team
| Member | Module |
|---|---|
| Jiya | Module 1: dataset handling and preprocessing tools |
| Param | Module 2: model, training, testing, prediction, live mode, Flask backend |
| Kanishka | Module 3: frontend and documentation |

## How it works
1. The user uploads a video (or records one with the webcam) on the web page, replays it, and presses **Analyze Clip**.
2. The page sends the clip to the Flask API (`POST /predict`).
3. The backend finds the face with MediaPipe and crops the mouth region.
4. The mouth frames (75 frames, grayscale, 96x96) go through a 3D CNN + bidirectional GRU model trained with CTC loss.
5. The output is decoded into text and shown on the result page, where the clip can be replayed and the text translated, spoken or copied.

There is also a real-time mode (`live.py`) that reads one sentence at a time from the webcam.

## Tech stack
- Frontend: HTML, CSS, JavaScript, MediaPipe (face overlay), IndexedDB (saved clips)
- Backend: Python 3.12, Flask, PyTorch, OpenCV, MediaPipe
- Tools: VS Code, Git, GitHub, Kaggle (free GPU for training)

## Folder structure
```
LIP-READ/
├── Frontend/
│   ├── index.html, script.js, style.css     Home page: upload / live camera, replay before analyzing, My Clips
│   └── result.html, result.js, result.css   Result page: text, replay, translation
├── backend/                             Module 2: model and Flask API
│   ├── model.py            3D CNN + BiGRU model
│   ├── preprocess.py       mouth cropping, text encoding and decoding
│   ├── train.py            training and fine-tuning
│   ├── test.py             evaluation (CER and WER)
│   ├── predict.py          prediction from one video
│   ├── live.py             real-time webcam lip reading
│   ├── app.py              Flask API
│   ├── grid_grammar.py     optional output clean-up (GRID grammar, or match to known phrases)
│   ├── convert_grid.py     converts the GRID download into the training format
│   ├── record_clips.py     records your own webcam clips for fine-tuning
│   ├── browser_copy.py     makes browser-playable (H.264) copies of clips
│   ├── practice_sentences.txt   200 GRID-style sentences to read while recording
│   ├── intro_sentences.txt      200 lines of the intro demo, to read while recording
│   ├── intro_phrases.txt        the four intro lines used for phrase matching
│   └── requirements.txt
├── Data/, images/
├── preprocessing.py, dataset_management.py,
│   run_module1.py, requirements_module1.txt   Module 1 tools
├── README_MODULE1.md                    Module 1 notes
└── README.md
```
The dataset and the trained weights (`backend/lipreader.pt`) are not stored in the repository.

## Setup
Use Python 3.12 (newer versions are not yet supported by all packages).
```
git clone https://github.com/param5205/LIP-READ.git
cd LIP-READ/backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1      # Windows PowerShell (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```
The first run downloads a small face-landmark model (`face_landmarker.task`), so an internet connection is needed once. After that everything runs offline, except the translation on the result page.

## Getting the trained model (`lipreader.pt`)
The weights are about 28.5 MB and are not in Git. Download them from: **<add the Google Drive or GitHub Release link here>** and save the file as `backend/lipreader.pt`.
https://drive.google.com/drive/folders/1aPLSmtz40TrsKjDb_vGietJCMEFuDZiW?usp=sharing

To make your own: train on Kaggle (see below), open the notebook's Output tab, download `lipreader.pt` with the download icon (the browser may save it as `lipreader.zip`; it is already the model, so just copy it to `backend/lipreader.pt`).

## Dataset
We use the GRID corpus from Kaggle (about 14 GB). It is too large for GitHub, so each person downloads it separately. Videos are grouped by speaker (`data/s1_processed/*.mpg`), with labels in `data/s1_processed/align/*.align`.

Convert it to the format the training code reads:
```
python convert_grid.py --videos "path\to\archive\data" --out data --speakers s1 s2 s3 s4
```
Use `--limit 50` for a quick test (it stops after that many clips in total). The converter writes:
```
data/videos/s1_bbaf2n.mp4
data/labels/s1_bbaf2n.txt     (the spoken sentence, lowercase)
```
The code reads `backend/data/videos` and `backend/data/labels`.

## Training and testing (run inside `backend/`)
```
python train.py                                       # train from scratch, saves the best weights to lipreader.pt
python train.py --init lipreader.pt --epochs 15       # continue / fine-tune from saved weights
python test.py                                        # evaluate on held-out clips (CER and WER)
python predict.py path/to/video.mp4                   # predict from one video
python live.py                                        # live lip reading with the webcam
```
A GPU is strongly recommended for training (for example a free Kaggle notebook).

### Fine-tuning on your own face and phrases
The model learned GRID speakers in a studio, so it works better after fine-tuning on your own webcam clips.
1. Record clips (they are saved as `data/videos/me_*.mp4` with `data/labels/me_*.txt`):
   ```
   python record_clips.py --sentences practice_sentences.txt --start 1 --count 50
   ```
   Press SPACE, wait for the countdown, say the sentence aloud within 3 seconds. `d` deletes the last clip, `s` skips, `q` quits.
   Use `--sentences intro_sentences.txt` for the intro lines, or leave `--sentences` out for random GRID sentences.
2. Upload the clips as a Kaggle dataset, copy them into `data/videos` and `data/labels` next to a sample of converted GRID clips.
3. Fine-tune and test on your own held-out clips:
   ```
   python train.py --init start.pt --epochs 15 --own-holdout 0.2
   python test.py --own-holdout 0.2
   ```
   `--own-holdout 0.2` keeps the last 20% of your `me_*` clips out of training as the test set.

### Live mode
```
python live.py                                    # sentence mode: SPACE, countdown, say one sentence
python live.py --mode continuous                  # sliding window (less accurate)
python live.py --phrases intro_phrases.txt        # match the output to your known phrases
python live.py --no-snap                          # do not force the GRID 6-word grammar
```
Keys: SPACE = record, c = clear, q = quit. By default the output is cleaned up to the GRID grammar (command, colour, preposition, letter, digit, adverb). For the website, set `$env:LIPREAD_PHRASES="intro_phrases.txt"` before `python app.py` to match the output to known phrases.

## Run the app
1. Start the backend from `backend/` with the venv active: `python app.py` (runs on http://127.0.0.1:5000).
2. Open `Frontend/index.html` in Chrome.
3. Choose **Upload Video** or **Live Camera**. The clip opens in a player so you can replay it, then click **Analyze Clip**. Past clips are listed under **My Clips**, each with its own play button.

The backend needs a trained `lipreader.pt` in `backend/`.

Browsers cannot play the `.mp4` clips written by OpenCV (older video codec). If the player says it cannot play a clip, make a browser-friendly copy:
```
pip install imageio-ffmpeg
python browser_copy.py path\to\clip.mp4        # creates clip_web.mp4
```

## API
`POST http://127.0.0.1:5000/predict`
- Body: form-data, key `video` (mp4, webm, avi or mov, up to 20 MB)
- Success: `{"prediction": "text"}`
- Error: `{"error": "message"}` with status 400, 413, 422 or 500

## Results
Test clips come from speakers that were also used in training.

| Run | Training data | Test clips | CER | WER |
|---|---|---|---|---|
| 1 | about 4 speakers (400 clips) | 400 | 8.79% | 26.62% |
| 2 | 10 speakers (1,000 clips) | 1,000 | 3.63% | 9.35% |
| 3 | 15 speakers (1,500 clips) | 1,500 | 2.59% | 7.18% |
| 4 | 17 speakers (1,700 clips) | 1,700 | 2.70% | 7.04% |

CER = character error rate, WER = word error rate (lower is better). Most errors are single letters that look alike on the lips.

**Fine-tuned on our own clips (intro demo).** After fine-tuning on our own webcam clips and four intro lines, the raw model output on 80 held-out intro clips had CER 40.19% and WER 78.89%. Most words are close but have one or two wrong letters, so WER is high. With phrase matching (`--phrases intro_phrases.txt`) the output is matched to the nearest known line. This is a closed-set demo of the pipeline on a custom vocabulary, not free-speech reading.

## Module 1 tools (Jiya)
```
pip install -r requirements_module1.txt
python run_module1.py preprocess video.mp4 --output processed/video_frames.npy
python run_module1.py manifest path/to/dataset
python run_module1.py inventory path/to/dataset
```
See `README_MODULE1.md` for details.

## Limitations
- The model learned the fixed sentence pattern and small vocabulary of GRID, plus the four intro lines. It cannot read free speech. Open-vocabulary reading needs a large pretrained model.
- Accuracy on a new person's face, camera or lighting is lower than the test numbers, because the test clips come from speakers seen in training.
- The intro fine-tune used about 200 clips of one person, so it works best for that person and setup.
- Each clip is a fixed 3-second window (75 frames), so a sentence must be said within 3 seconds.
- Lip reading is inherently ambiguous, because many sounds look alike on the lips.
- Browsers cannot play GRID `.mp4` clips written by OpenCV unless they are converted with `browser_copy.py`. The prediction is not affected.

## Future work
- Record more varied clips (more people, lighting and camera positions) and add data augmentation.
- Test on speakers the model has not seen.
- Use a large pretrained model (such as Auto-AVSR) for open-vocabulary reading.
- Add a language model to correct similar-looking words.
- Deploy the backend to the cloud.

## Status
- Backend, API, live mode and frontend are complete and connected.
- The model is trained on GRID (17 speakers) and fine-tuned on our own clips, with the results above.

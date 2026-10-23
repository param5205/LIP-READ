# Lip Reading System — Module 1: Data Handling (Jiya)

This package covers the three tasks assigned to Jiya:
- Kaggle dataset management/inventory
- `preprocessing.py` video preprocessing
- Data cleaning and conversion

## Files included
- `dataset/preprocessing.py`: face detection baseline, approximate mouth-region crop,
  grayscale conversion, resize, pixel normalization, sequence padding/truncation,
  save to NumPy `.npy`.
- `dataset/dataset_management.py`: video file inventory, dataset manifest CSV,
  transcript cleaning, GRID `.align` parsing.
- `run_module1.py`: one command-line entry point for all Module 1 actions.
- `requirements_module1.txt`: Python dependencies.

## Install dependencies
Open VS Code terminal in the folder that contains `run_module1.py`:

```bash
python -m pip install -r requirements_module1.txt
```

## A. Test preprocessing using your existing uploaded video
Use the real filename shown in your project's `uploads` folder. Example:

```bash
python run_module1.py preprocess uploads/video.mp4 --output processed/video_frames.npy
```

If your video has a different name, replace `video.mp4` with that name.
Expected output includes frames read, saved array shape (75, 50, 100), min/max pixel values
and output file location. This demonstrates preprocessing; inspect results before training.

## B. After the GRID dataset is downloaded and extracted
Use the real path to your extracted dataset folder. Windows example:

```bash
python run_module1.py manifest "D:/Datasets/GRID" --output dataset_manifest.csv
python run_module1.py inventory "D:/Datasets/GRID" --output dataset_inventory.csv
```

The manifest records video paths, matching same-name transcript paths where available,
cleaned transcript text and whether a transcript was found. The inventory creates a
CSV listing files and sizes. These scripts do not alter or delete the source dataset.

## C. Data cleaning/conversion
- Transcript text is lowercased and whitespace normalized.
- Common silence labels (`sil`, `sp`, `spn`) are removed.
- `.align` files are parsed into token timing rows.
- Video sequences are converted into fixed-length normalized NumPy arrays.

## Important limitations
- The Kaggle GRID Corpus ZIP in your screenshot is approximately 14 GB. Do not download it
  unless you have enough free disk space and time. The actual dataset download and manifest
  generation cannot be completed until the dataset is present on your laptop.
- The built-in Haar face detector provides only an approximate mouth crop, not precise lip
  landmarks. A research-quality system should use facial landmarks and visually validate crops.
- Module 1 does not train CNN+LSTM or produce predicted words; that is Module 2's task.

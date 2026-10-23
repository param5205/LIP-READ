"""Jiya / Module 1: video preprocessing pipeline for the Lip Reading System."""
from pathlib import Path
import cv2
import numpy as np
import json
DEFAULT_FRAME_SIZE = (100, 50)  # width, height
DEFAULT_SEQUENCE_LENGTH = 75


def create_face_detector():
    """Load OpenCV's built-in frontal-face detector."""
    if not hasattr(cv2, "CascadeClassifier"):
        # OpenCV 5 removed CascadeClassifier. Fall back to the fixed mouth-region crop.
        print("WARNING: this OpenCV has no CascadeClassifier (OpenCV 5?). "
              "Using the fixed lower-face crop. Install opencv-python<5 for face detection.")
        return None
    xml = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(xml)
    if detector.empty():
        raise RuntimeError("Could not load OpenCV Haar face detector.")
    return detector


def crop_approx_mouth(gray_frame, face_detector):
    """Approximate mouth crop from the lower portion of the largest detected face.

    Fallback: crop lower-middle frame if no face is detected. For accurate research
    results, replace this baseline with facial landmarks and inspect sample crops.
    """
    h, w = gray_frame.shape[:2]
    faces = () if face_detector is None else face_detector.detectMultiScale(
        gray_frame, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40)
    )
    if len(faces):
        x, y, fw, fh = max(faces, key=lambda item: int(item[2]) * int(item[3]))
        x1, x2 = max(0, x + int(fw * 0.15)), min(w, x + int(fw * 0.85))
        y1, y2 = max(0, y + int(fh * 0.58)), min(h, y + int(fh * 0.93))
        crop = gray_frame[y1:y2, x1:x2]
        if crop.size:
            return crop
    crop = gray_frame[int(h * 0.50):int(h * 0.95), int(w * 0.15):int(w * 0.85)]
    return crop if crop.size else gray_frame


def extract_frames(video_path, frame_size=DEFAULT_FRAME_SIZE,
                   max_frames=DEFAULT_SEQUENCE_LENGTH, crop_mouth=True):
    """Read video frames, grayscale, optionally crop mouth, resize and normalize.

    Returns float32 array shaped [T, height, width] with values in [0, 1].
    """
    video_path = Path(video_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"OpenCV could not open video: {video_path}")

    detector = create_face_detector() if crop_mouth else None
    frames = []
    try:
        while len(frames) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            roi = crop_approx_mouth(gray, detector) if crop_mouth else gray
            resized = cv2.resize(roi, frame_size, interpolation=cv2.INTER_AREA)
            frames.append(resized.astype(np.float32) / 255.0)
    finally:
        cap.release()

    if not frames:
        return np.empty((0, frame_size[1], frame_size[0]), dtype=np.float32)
    return np.stack(frames).astype(np.float32)


def make_fixed_length(frames, sequence_length=DEFAULT_SEQUENCE_LENGTH):
    """Pad with zeros or truncate to [sequence_length, height, width]."""
    frames = np.asarray(frames, dtype=np.float32)
    if frames.ndim != 3:
        raise ValueError("frames must have shape [T, H, W]")
    h, w = frames.shape[1:]
    output = np.zeros((sequence_length, h, w), dtype=np.float32)
    n = min(len(frames), sequence_length)
    if n:
        output[:n] = frames[:n]
    return output


def preprocess_and_save(video_path, output_path, sequence_length=DEFAULT_SEQUENCE_LENGTH,
                        frame_size=DEFAULT_FRAME_SIZE, crop_mouth=True):
    """Preprocess one video and save a normalized fixed-length .npy array."""
    frames = extract_frames(video_path, frame_size, sequence_length, crop_mouth)
    if len(frames) == 0:
        raise ValueError("No frames were read from the video.")
    sequence = make_fixed_length(frames, sequence_length)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, sequence)
    return {
        "input_video": str(Path(video_path)),
        "frames_read": int(len(frames)),
        "sequence_shape": list(sequence.shape),
        "min_pixel": float(sequence.min()),
        "max_pixel": float(sequence.max()),
        "saved_to": str(output_path),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Preprocess one lip-reading video.")
    parser.add_argument("video", help="Path to video")
    parser.add_argument("--output", default="processed/video_frames.npy")
    parser.add_argument("--no-mouth-crop", action="store_true",
                        help="Use full grayscale frame instead of approximate mouth crop")
    args = parser.parse_args()
    print(json.dumps(preprocess_and_save(args.video, args.output,
                                         crop_mouth=not args.no_mouth_crop), indent=2))
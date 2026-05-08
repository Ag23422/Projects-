import os
import cv2
import numpy as np
import logging
from ultralytics import YOLO
import sys
import torch
from tqdm import tqdm

# SuperGlue path
sys.path.append('/home/ansh/Desktop/innefu_project /SuperGluePretrainedNetwork')
from models.matching import Matching
from models.utils import frame2tensor

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('process_log.txt'),
        logging.StreamHandler()
    ]
)

def list_image_files(folder):
    exts = ('.png', '.jpg', '.jpeg')
    return sorted([os.path.join(dp, f) for dp, _, fn in os.walk(folder) for f in fn if f.lower().endswith(exts)])

def load_superglue_model(superpoint_weights, superglue_weights=None):
    config = {
        'superpoint': {
            'nms_radius': 4,
            'keypoint_threshold': 0.005,
            'max_keypoints': 1024,
        },
        'superglue': {
            'weights': 'indoor',
            'sinkhorn_iterations': 20,
            'match_threshold': 0.2,
        }
    }
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    matching = Matching(config).eval().to(device)

    if superpoint_weights and os.path.exists(superpoint_weights):
        matching.superpoint.load_state_dict(torch.load(superpoint_weights, map_location=device))
    if superglue_weights and os.path.exists(superglue_weights):
        matching.superglue.load_state_dict(torch.load(superglue_weights, map_location=device))

    return matching, device

def is_currency(yolo_model, image, min_kp):
    results = yolo_model(image)
    for res in results:
        if not hasattr(res, 'boxes') or res.boxes is None:
            continue
        for box in res.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            roi = image[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            keypoints = cv2.goodFeaturesToTrack(gray, maxCorners=min_kp, qualityLevel=0.01, minDistance=10)
            if keypoints is not None and len(keypoints) >= min_kp:
                return True
    return False

def superpoint_superglue_match(matching, device, img1, img2):
    img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    image0 = frame2tensor(img1_gray, device)
    image1 = frame2tensor(img2_gray, device)
    with torch.no_grad():
        pred = matching({'image0': image0, 'image1': image1})
        matches = pred['matches0'][0].cpu().numpy()
    return np.sum(matches > -1)

def compare_images_superglue(input_img, dataset_root, matching, device, min_matches=50, chunk_size=100):
    folders = sorted([f for f in os.listdir(dataset_root) if os.path.isdir(os.path.join(dataset_root, f))])
    all_image_paths = []
    for folder in folders:
        folder_path = os.path.join(dataset_root, folder)
        all_image_paths.extend([(os.path.join(folder_path, f), folder) for f in list_image_files(folder_path)])

    total_images = len(all_image_paths)
    logging.info(f"Total images to compare: {total_images}")
    
    best_folder, best_score = None, 0

    for i in range(0, total_images, chunk_size):
        chunk = all_image_paths[i:i+chunk_size]
        logging.info(f"Processing chunk {i+1} to {i+len(chunk)}")

        for img_path, folder in tqdm(chunk, desc=f"Chunk {i//chunk_size + 1}"):
            cmp_img = cv2.imread(img_path)
            if cmp_img is None:
                continue
            matches = superpoint_superglue_match(matching, device, input_img, cmp_img)

            if matches > best_score and matches >= min_matches:
                best_score = matches
                best_folder = folder
                logging.info(f"New best match: Folder={folder}, Score={matches}")

    return best_folder, best_score

def main():
    # Paths
    input_folder = "/home/ansh/Desktop/innefu_project /cropped_inputs"
    dataset_folder = "/home/ansh/Desktop/innefu_project /segregated_by_denomination_cropped/train"
    yolo_weights = "/home/ansh/Downloads/weights_x_hyp.pt"
    superpoint_weights = "/home/ansh/Desktop/innefu_project /SuperGluePretrainedNetwork/models/weights/superpoint_v1.pth"
    superglue_weights = "/home/ansh/Downloads/super/superglue_epoch10.pth"
    matched_dir = "currency_matched"

    min_kp = 10
    confidence_thresh = 0.5

    os.makedirs(matched_dir, exist_ok=True)

    logging.info("Loading YOLO model...")
    yolo_model = YOLO(yolo_weights)

    logging.info("Loading SuperPoint + SuperGlue...")
    matching, device = load_superglue_model(superpoint_weights, superglue_weights)

    input_images = list_image_files(input_folder)
    if not input_images:
        logging.error("No input images found.")
        return

    for img_path in input_images:
        img = cv2.imread(img_path)
        if img is None:
            logging.warning(f"Unable to read image {img_path}")
            continue

        if not is_currency(yolo_model, img, min_kp):
            logging.info(f"No currency detected in {img_path}")
            continue

        best_folder, score = compare_images_superglue(img, dataset_folder, matching, device, min_matches=min_kp)

        logging.info(f"\nImage: {os.path.basename(img_path)}")
        logging.info(f"Matched folder: {best_folder if best_folder else 'None'} with score: {score:.2f}")

        if best_folder and score >= confidence_thresh:
            out_path = os.path.join(matched_dir, os.path.basename(img_path))
            cv2.imwrite(out_path, img)
            logging.info(f"Saved matched image to {out_path}")
        else:
            logging.info(f"No confident match found for {img_path}")

if __name__ == '__main__':
    main()

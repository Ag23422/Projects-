import os
import io
import csv
import time
import requests
from PIL import Image
from tqdm import tqdm
import torch
import open_clip
from torchvision.transforms import functional as TF

from serpapi import GoogleSearch

# ====== CONFIGURATION ======
SERPAPI_KEY ='919f4f1e7dca6ea2affd70afe9d99a256c2fdd954c6935d1cb4ee72897362520'  
RESULTS_PER_PROMPT = 100 
TOP_K = 80  
OUTPUT_FOLDER = 'usd_currency_dataset_serpapi'
PAIRS_FILE = 'usd_currency_image_text_pairs_serpapi.csv'

PROMPTS = [
   ""
]
device = "cuda" if torch.cuda.is_available() else "cpu"
model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
tokenizer = open_clip.get_tokenizer('ViT-B-32')
model = model.to(device).eval()

def search_images_serpapi(query, num_results=100):
    params = {
        "q": query,
        "tbm": "isch",
        "num": num_results,
        "api_key": SERPAPI_KEY,
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    images = [] # max images per search allowed in free trial
    for img in results.get("images_results", []):
        images.append(img['original'])
    return images


def download_image(url):
    try:
        response = requests.get(url, timeout=5)
        image = Image.open(io.BytesIO(response.content)).convert('RGB')
        return image
    except Exception:
        return None
    
def rank_images(images, prompt):
    valid_images = []
    image_tensors = []

    for img in images:
        if img is not None:
            valid_images.append(img)
            image_tensors.append(preprocess(img).unsqueeze(0))

    if not image_tensors:
        return []

    image_input = torch.cat(image_tensors).to(device)
    text_input = tokenizer([prompt]).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        text_features = model.encode_text(text_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        similarity = (image_features @ text_features.T).squeeze()

    scores = similarity.cpu().numpy().tolist()
    ranked = list(zip(valid_images, scores))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


def process_prompt(prompt):
    print(f"\n🔎 Searching: {prompt}")
    image_urls = search_images_serpapi(prompt, RESULTS_PER_PROMPT)
    print(f"Found {len(image_urls)} images")

    downloaded_images = [download_image(url) for url in tqdm(image_urls)]
    ranked = rank_images(downloaded_images, prompt)

    folder_name = prompt.replace(" ", "_").replace("$", "Dollar")
    folder_path = os.path.join(OUTPUT_FOLDER, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    image_text_pairs = []

    for idx, (img, score) in enumerate(ranked[:TOP_K]):
        img_path = os.path.join(folder_path, f"img_{idx+1}.jpg")
        img.save(img_path)
        image_text_pairs.append((img_path, prompt))
        print(f"Saved: {img_path} (Score: {score:.3f})")

    return image_text_pairs

def build_dataset():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    all_pairs = []

    for prompt in PROMPTS:
        pairs = process_prompt(prompt)
        all_pairs.extend(pairs)
        time.sleep(1.5)  

    with open(PAIRS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['image_path', 'text'])
        writer.writerows(all_pairs)

    print(f"\n✅ Dataset complete: {len(all_pairs)} images collected")
    print(f"Pairs saved to: {PAIRS_FILE}")

if __name__ == "__main__":
    build_dataset()

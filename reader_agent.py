import cv2
import os
import time
from PIL import Image
from mlx_vlm import load, generate

# --- CONFIGURATION ---
MODEL_ID = "mlx-community/gemma-4-e4b-it-4bit"
CAM_INDEX = 1 

print("🚀 INITIALIZING MULTI-MODAL BURST AGENT...")
model, processor = load(MODEL_ID)
print("✅ Brain Loaded.")

def capture_burst():
    """Captures 3 images with slight delays to catch different angles/focus."""
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    if not cap.isOpened():
        print("❌ Error: Camera not found.")
        return []

    if not os.path.exists("captures"): os.makedirs("captures")
    
    image_paths = []
    print("\n📸 STARTING BURST CAPTURE (3 IMAGES)")
    print("Tip: Tilt the book slightly between shots for better clarity.")

    for i in range(1, 4):
        print(f"👉 Get ready for Image {i}/3...")
        # Give user 10 seconds to adjust the book
        for count in range(10, 0, -1):
            print(f" {count}...", end="\r")
            time.sleep(1)
            
        # Warm-up/Focus for each shot
        for _ in range(20): cap.read()
        
        ret, frame = cap.read()
        if ret:
            path = f"captures/burst_{i}.jpg"
            cv2.imwrite(path, frame)
            image_paths.append(path)
            print(f"✅ Captured Image {i}")
        
    cap.release()
    return image_paths

def run_experiment():
    img_paths = capture_burst()
    if not img_paths: return

    target_word = input("\n🔍 Which word/phrase should I explain? ")

    # 1. Multi-Image Prompting (Source: 2026 Multimodal Best Practices)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "I am providing 3 images of the same book page from different angles to ensure clarity."},
                {"type": "image"}, # burst_1
                {"type": "image"}, # burst_2
                {"type": "image"}, # burst_3
                {"type": "text", "text": f"Find the word '{target_word}' on this page and explain its meaning contextually. Be concise."}
            ]
        }
    ]

    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    if not prompt.endswith("<|thought|>\n"):
        prompt += "<|thought|>\n"

    print(f"\n🧠 [THINKING] Cross-referencing 3 images for '{target_word}'...")
    
    try:
        # Load all 3 images into a list
        pil_images = [Image.open(p) for p in img_paths]
        
        result = generate(
            model, 
            processor, 
            prompt, 
            pil_images,  # Passing the list of 3 images
            verbose=True,
            temp=0.1,
            max_tokens=600
        )
        
        full_output = result.text

        # 2. UPDATED PARSING (Splits at the <channel|> or </|thought|> token)
        # Based on your previous output, Gemma 4 uses '<channel|>' as the final separator.
        if "<channel|>" in full_output:
            explanation = full_output.split("<channel|>")[-1].strip()
        elif "</|thought|>" in full_output:
            explanation = full_output.split("</|thought|>")[-1].strip()
        else:
            # Fallback for unexpected formats
            explanation = full_output.strip()

        # Final cleanup: remove any trailing tags
        explanation = explanation.replace("<turn|>", "").strip()

        print(f"\n📢 AI EXPLANATION: {explanation}")
        
        # 3. CLEAN AUDIO OUTPUT
        # We only 'say' the explanation part
        if len(explanation) > 10:
            os.system(f"say \"{explanation}\"")
        else:
            print("⚠️ Explanation too short, something went wrong with the parse.")
            
    except Exception as e:
        print(f"❌ Error during reasoning: {e}")

if __name__ == "__main__":
    try:
        while True:
            print("\n" + "="*40)
            print("  M4 READER AGENT: BURST VISION MODE")
            print("="*40)
            input("Press ENTER to start the 3-shot capture...")
            run_experiment()
    except KeyboardInterrupt:
        print("\nDemo exiting.")
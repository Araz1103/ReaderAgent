import cv2
import os
import time
import subprocess
import re
import threading
from PIL import Image
from mlx_vlm import load, generate

# --- CONFIG ---
MODEL_ID = "mlx-community/gemma-4-e4b-it-4bit"
CAM_INDEX = 0 # iPhone (0) or Mac (1)

print("🚀 LOADING AGENT BRAIN...")
model, processor = load(MODEL_ID)
chat_history = [] 
STATUS = "IDLE"

def speak(text):
    """Cleanly speaks text via Siri."""
    def run_speech():
        # Clean markdown and special characters
        clean_text = re.sub(r'\*', '', text).replace('"', '').replace("'", "")
        # Use subprocess for safety
        subprocess.run(["say", "-v", "Siri", clean_text])
    threading.Thread(target=run_speech).start()

def run_agent_logic(user_query, image_paths=None):
    """Handles Multi-Turn Logic with image memory management."""
    global chat_history, STATUS
    STATUS = "THINKING"
    
    # --- FIX: IMAGE MEMORY MANAGEMENT ---
    # Before adding a new turn, convert OLD image tags in history to text
    # This prevents the 'StopIteration' error and saves RAM.
    for message in chat_history:
        if isinstance(message["content"], list):
            new_content = []
            for item in message["content"]:
                if item["type"] == "image":
                    # Keep a placeholder so the AI knows it looked at something
                    pass 
                else:
                    new_content.append(item)
            # Ensure we don't leave it empty; add a text note
            if not any(i["type"] == "text" for i in new_content):
                new_content.append({"type": "text", "text": "[Referencing previous images]"})
            message["content"] = new_content

    # Create the new content block
    content = []
    if image_paths:
        # Prompt telling the AI to use the 3 new images
        content.append({"type": "text", "text": "I am providing 3 images of the same book page. Use them to ensure you see all the text clearly."})
        for _ in image_paths:
            content.append({"type": "image"})
        content.append({"type": "text", "text": f"Find the word based on user query: '{user_query}'. Look at the images of the page and explain its meaning contextually. Be concise."})
    else:
        # Follow-up without new images
        content.append({"type": "text", "text": user_query})

    chat_history.append({"role": "user", "content": content})
    
    # Apply Template
    prompt = processor.apply_chat_template(chat_history, add_generation_prompt=True)
    if not prompt.endswith("<|thought|>\n"):
        prompt += "<|thought|>\n"

    # Only pass the CURRENT burst of images
    pil_images = [Image.open(p) for p in image_paths] if image_paths else []
    
    print("\n🧠 Agent is thinking...")
    # Lower temp and repetition penalty for stability
    result = generate(
        model, 
        processor, 
        prompt, 
        pil_images, 
        verbose=True, 
        temp=0.1, 
        max_tokens=800,
        repetition_penalty=1.2
    )
    
    full_output = result.text

    # Parsing logic
    if "<channel|>" in full_output:
        ans = full_output.split("<channel|>")[-1].strip()
    elif "</|thought|>" in full_output:
        ans = full_output.split("</|thought|>")[-1].strip()
    else:
        ans = full_output.strip()

    # Save the text response to history
    chat_history.append({"role": "assistant", "content": [{"type": "text", "text": ans}]})
    STATUS = "IDLE"
    return ans

def main():
    global STATUS
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    if not os.path.exists("captures"): os.makedirs("captures")

    print("\n--- Agent Active. Press SPACE to capture, ENTER to just talk, Q to quit ---")
    
    while True:
        ret, frame = cap.read()
        if not ret: break

        display_frame = frame.copy()
        color = (0, 255, 0) if STATUS == "IDLE" else (0, 255, 255)
        cv2.putText(display_frame, f"STATUS: {STATUS}", (50, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)
        
        cv2.imshow("Reader Agent Eye", cv2.resize(display_frame, (960, 540)))
        
        key = cv2.waitKey(1) & 0xFF
        
        # TRIGGER: New Vision + Question
        if key == ord(' '):
            speak("Let me take a look at that.")
            burst_paths = []
            for i in range(1, 4):
                STATUS = f"CAPTURING {i}"
                for _ in range(10): cap.read() # Warmup
                ret, frame = cap.read()
                if ret:
                    p = f"captures/burst_{i}.jpg"
                    cv2.imwrite(p, frame)
                    burst_paths.append(p)
                time.sleep(1)

            user_query = input("\n🔍 Query (With new images): ")
            answer = run_agent_logic(user_query, burst_paths)
            print(f"\n📢 AI: {answer}")
            speak(answer)

        # TRIGGER: Follow-up question (No new images)
        elif key == ord('f'): # Follow Up Key
            user_query = input("\n🔍 Follow-up question (No new images): ")
            answer = run_agent_logic(user_query, None)
            print(f"\n📢 AI: {answer}")
            speak(answer)

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
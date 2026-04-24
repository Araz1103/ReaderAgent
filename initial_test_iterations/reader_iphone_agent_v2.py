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
CAM_INDEX = 0  # iPhone Index
STATUS = "IDLE" # Global status to show on the viewfinder

print("🚀 LOADING AGENT BRAIN...")
model, processor = load(MODEL_ID)
chat_history = [] 

def speak(text):
    """Cleanly speaks text via Siri."""
    global STATUS
    # We don't want the speak function to block the viewfinder
    def run_speech():
        clean_text = re.sub(r'\*', '', text).replace('"', '').replace("'", "")
        subprocess.run(["say", "-v", "Siri", clean_text])
    
    threading.Thread(target=run_speech).start()

def run_agent_logic(user_query, image_paths=None):
    """Handles Multi-Turn Logic and returns the answer."""
    global chat_history, STATUS
    STATUS = "THINKING"
    
    content = []
    if image_paths:
        content.append({"type": "text", "text": "I am providing 3 images of the same book page. Use them to ensure you see all the text clearly."})
        for _ in image_paths: content.append({"type": "image"})
        content.append({"type": "text", "text": f"Find the word based on user query: '{user_query}'. Look at the images of the page and explain its meaning contextually. Be concise."})
    else:
        content.append({"type": "text", "text": user_query})

    chat_history.append({"role": "user", "content": content})
    prompt = processor.apply_chat_template(chat_history, add_generation_prompt=True)
    if not prompt.endswith("<|thought|>\n"): prompt += "<|thought|>\n"

    pil_images = [Image.open(p) for p in image_paths] if image_paths else []
    
    # generate() is the heavy lifter. Window will 'freeze' here briefly
    # but it will still be visible.
    result = generate(model, processor, prompt, pil_images, verbose=True, temp=0.1, max_tokens=800)
    
    full_output = result.text
    # 2. UPDATED PARSING (Splits at the <channel|> or </|thought|> token)
    # Gemma 4 uses '<channel|>' as the final separator.
    if "<channel|>" in full_output:
        ans = full_output.split("<channel|>")[-1].strip()
    elif "</|thought|>" in full_output:
        ans = full_output.split("</|thought|>")[-1].strip()
    else:
        # Fallback for unexpected formats
        ans = full_output.strip()
    # if "<channel|>" in full_output:
    #     ans = full_output.split("<channel|>")[-1].strip()
    # else:
    #     ans = full_output.split("</|thought|>")[-1].strip()

    chat_history.append({"role": "assistant", "content": [{"type": "text", "text": ans}]})
    STATUS = "IDLE"
    return ans

def main():
    global STATUS
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    if not os.path.exists("captures"): os.makedirs("captures")

    print("\n--- Agent Active. Press SPACE to capture, Q to quit ---")
    
    while True:
        ret, frame = cap.read()
        if not ret: break

        # 1. ADD HUD (Heads-Up Display) to the frame
        display_frame = frame.copy()
        color = (0, 255, 0) if STATUS == "IDLE" else (0, 255, 255)
        if STATUS == "THINKING": color = (0, 165, 255)
        
        cv2.putText(display_frame, f"STATUS: {STATUS}", (50, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)
        
        if STATUS == "IDLE":
            cv2.putText(display_frame, "Press SPACE to Analyze", (50, 140), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Show the Viewfinder
        cv2.imshow("Reader Agent Eye", cv2.resize(display_frame, (960, 540)))
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):
            # Start the agentic sequence
            speak("Looking at the page now.")
            burst_paths = []
            
            for i in range(1, 4):
                STATUS = f"CAPTURING SHOT {i}"
                # Update the window to show the "Capturing" text
                for _ in range(10):
                    ret, frame = cap.read()
                    temp_frame = frame.copy()
                    cv2.putText(temp_frame, f"STATUS: {STATUS}", (50, 80), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
                    cv2.imshow("Reader Agent Eye", cv2.resize(temp_frame, (960, 540)))
                    cv2.waitKey(1)

                p = f"captures/agent_burst_{i}.jpg"
                cv2.imwrite(p, frame)
                burst_paths.append(p)
                time.sleep(2)  # Short pause between shots

            # Move to Reasoning
            user_query = input("\n🔍 Query (Voice simulation): ")
            answer = run_agent_logic(user_query, burst_paths)
            speak(answer)
            print(f"\n📢 AI: {answer}")

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
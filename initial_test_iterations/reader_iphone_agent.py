import cv2
import os
import time
import subprocess
import re
from PIL import Image
from mlx_vlm import load, generate

# --- CONFIG ---
MODEL_ID = "mlx-community/gemma-4-e4b-it-4bit"
CAM_INDEX = 0  # iPhone Index
# CAM_INDEX = 1 # Try 1 if 0 is the Mac Camera

print("🚀 LOADING AGENT BRAIN...")
model, processor = load(MODEL_ID)
chat_history = [] 

def speak(text):
    """Cleanly speaks text via Siri."""
    print(f"📢 AGENT: {text}")
    # Remove markdown/special chars for shell safety
    clean_text = re.sub(r'\*', '', text).replace('"', '').replace("'", "")
    subprocess.run(["say", "-v", "Siri", clean_text])

def run_agent_logic(user_query, image_paths=None):
    """Handles the Multi-Turn Conversation Logic."""
    global chat_history
    
    # Format the message for Gemma 4
    content = []
    if image_paths:
        for _ in image_paths:
            content.append({"type": "image"})
        content.append({"type": "text", "text": f"Context: These are images of my book. {user_query}"})
    else:
        content.append({"type": "text", "text": user_query})

    chat_history.append({"role": "user", "content": content})

    # Apply Template
    prompt = processor.apply_chat_template(chat_history, add_generation_prompt=True)
    if not prompt.endswith("<|thought|>\n"):
        prompt += "<|thought|>\n"

    # Generate
    pil_images = [Image.open(p) for p in image_paths] if image_paths else []
    
    print("\n🧠 Agent is thinking...")
    result = generate(model, processor, prompt, pil_images, verbose=True, temp=0.1)
    
    # Parse Result
    full_output = result.text
    if "<channel|>" in full_output:
        ans = full_output.split("<channel|>")[-1].strip()
    elif "</|thought|>" in full_output:
        ans = full_output.split("</|thought|>")[-1].strip()
    else:
        ans = full_output.strip()

    chat_history.append({"role": "assistant", "content": [{"type": "text", "text": ans}]})
    return ans

def main():
    global chat_history
    speak("Hello! I am active. Use the window to align your book.")
    
    # Start the iPhone Camera Stream
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Camera disconnected.")
            break

        # VIEW_FINDER: Display the live iPhone feed on your Mac
        # Resize it so it doesn't take over your whole screen
        cv2.imshow("Reader Agent Viewfinder", cv2.resize(frame, (854, 480)))
        
        # KEYBOARD INTERACTION (Will be replaced by Voice Wake-Word next)
        key = cv2.waitKey(1) & 0xFF
        
        # Press SPACE to ask a question about the current view
        if key == ord(' '):
            cv2.destroyWindow("Reader Agent Viewfinder") # Close during analysis
            
            user_query = input("\n🔍 What is your question? (or 'Hey Reader, tell me meaning of...') ")
            
            # AGENTIC FEEDBACK
            speak("Understood. Let me capture three clean shots to be sure.")
            
            # BURST CAPTURE logic while the camera is already open
            burst_paths = []
            for i in range(1, 4):
                speak(f"Capturing shot {i}...")
                # Let focus settle
                for _ in range(15): cap.read() 
                ret, frame = cap.read()
                if ret:
                    p = f"captures/agent_burst_{i}.jpg"
                    cv2.imwrite(p, frame)
                    burst_paths.append(p)
            
            # RUN AI TURN
            answer = run_agent_logic(user_query, burst_paths)
            speak(answer)
            
            print("\n✅ Analysis complete. Returning to Viewfinder. Press Q to quit.")
            # Re-open the viewfinder
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if not os.path.exists("captures"): os.makedirs("captures")
    main()
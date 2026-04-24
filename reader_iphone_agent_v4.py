import copy
import cv2
import os
import time
import subprocess
import re
import threading
from PIL import Image
from mlx_vlm import load, generate

# --- 1. CONFIGURATION & MODELS ---
MODEL_ID = "mlx-community/gemma-4-e4b-it-4bit"
CAM_INDEX = 0  # 0 for iPhone, 1 for Mac 
STATUS = "IDLE"
CURRENT_IMAGES = [] # Stores the active 3 PIL images
CHAT_HISTORY = []   # Stores the multi-turn conversation

print("🚀 LOADING ALFRED'S BRAIN (Gemma 4 E4B)...")
model, processor = load(MODEL_ID)

# --- 2. SYSTEM PROMPTS & FEW-SHOT EXAMPLES ---
# This is the most critical part for a 4B model to act as an agent.

# DECISION PROMPT with strict rules and examples to choose between [CAMERA] and [CONTINUE]
DECISION_PROMPT = """You are Alfred, a Contextual Reading Assistant. Your ONLY job is to decide if we need to call the [CAMERA] or [CONTINUE].

The user is reading a book, and they will ask you to explain words or concepts they encounter. 
You have to answer their queries based on the book they are reading. For that, you have a CAMERA tool.
The CAMERA allows you to see the page of the book, for context, to answer user's queries. 
You can ask the user to take pictures of the page when you need more context to answer their question, and call the CAMERA tool to capture images.

TOOL DESCRIPTION:
- CAMERA: Use this if the user asks about a new word, a new page, or if you cannot see the text required to answer.

DECISION RULES:
1. If you need to see the book, and if the user asks about a NEW word/page not in the history and images, your response MUST start with: [CAMERA]
2. If the user asks a follow-up about the CURRENT context and you can answer using the images already in your memory or answer from previous turns, start with: [CONTINUE]

EXAMPLES:
---------------------------------------
User: What does 'ephemeral' mean here?
Alfred: [CAMERA] I need to see the page first. Please align your book.
User: Is it a metaphor?
Alfred: [CONTINUE] I can answer this from looking at the previous context.
---------------------------------------
---------------------------------------
User: Can you explain what is implied when it is said Tom is devious?
Alfred: [CAMERA] I need to see what you are reading. Please align your book.
User: What are some synonyms of devious?
Alfred: [CONTINUE] I can answer the synonyms of devious from the previous context.
User: What does the author mean by "the world is a stage" in the last paragraph?
Alfred: [CAMERA] I need to see the last paragraph. Please take a picture of what you are reading.
---------------------------------------
"""

# ANSWERING PROMPT (used in the reasoning phase, after decision and tool use)
ANSWERING_PROMPT = """You are Alfred, a helpful Contextual Reading Assistant.

The user is reading a book, and they will ask you to explain words or concepts they encounter. 
You have to answer their queries using your knowledge of language & literature, based on the book they are reading.

Prefer to explain words and concepts user asks about contextually, from the book, using the images you have.
Combine your knowledge of language & literature, to help answer the user's query, and help them understand what they are reading.
But you can also use your general knowledge of language and literature to help answer the user's query, to help them understand what they are reading.

RULES:
1. You can use the images to find the exact sentences for context.
2. Be concise and helpful. Use your knowledge of language and literature to explain, and try to ground your answers in the text you see in the images.
So explain what the word or concept means in general and then explain what it means in the context of the book.
3. Do not mention technical tags or tools. Provide the explanation directly without narrating your internal process.
4. In case the user asks about a word or concept that is not in the images you have, you can mention you could not find it in the images of what they are reading, 
and use your general knowledge to explain it as best as you can.
5. MANDATORY TRANSITION: Use your internal thought process for analysis, but you MUST always conclude it with the <channel|> token before providing your final response to the user.

FORMAT TEMPLATE:
User: [User Query]
Assistant: <|thought|> [Your internal analysis of what the word or concept means, the book text, literary context, and word location] <channel|> [Your clean, concise final explanation for the user]
"""

# --- 3. THE VISION TOOL ---
def capture_burst_tool(cap):
    """
    The 'Eye' of Alfred. 
    Provides a 10s alignment window, then 3 shots with 5s gaps.
    """
    global STATUS
    image_paths = []
    
    # --- Step A: 10s Alignment ---
    start_time = time.time()
    while time.time() - start_time < 10:
        ret, frame = cap.read()
        if not ret: break
        
        countdown = 10 - int(time.time() - start_time)
        STATUS = f"ALIGN BOOK ({countdown}s)"
        
        # Display Alignment HUD
        display = frame.copy()
        cv2.putText(display, "ALFRED IS WATCHING", (50, 80), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 255, 0), 3)
        cv2.putText(display, f"ALIGN YOUR BOOK: {countdown}s", (50, 150), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 2)
        cv2.rectangle(display, (400, 200), (1520, 880), (0, 255, 0), 2) # Alignment box
        
        cv2.imshow("Alfred Viewfinder", cv2.resize(display, (960, 540)))
        cv2.waitKey(1)

    # --- Step B: 3-Shot Capture with 5s Gaps ---
    for i in range(1, 4):
        # 5s gap for user to tilt/adjust
        gap_start = time.time()
        while time.time() - gap_start < 5:
            ret, frame = cap.read()
            gap_countdown = 5 - int(time.time() - gap_start)
            STATUS = f"GET READY FOR SHOT {i} ({gap_countdown}s)"
            
            display = frame.copy()
            cv2.putText(display, f"CAPTURING SHOT {i} IN: {gap_countdown}s", (50, 80), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 255, 255), 3)
            cv2.imshow("Alfred Viewfinder", cv2.resize(display, (960, 540)))
            cv2.waitKey(1)
        
        # The actual capture
        ret, frame = cap.read()
        if ret:
            p = f"captures/alfred_burst_{i}.jpg"
            cv2.imwrite(p, frame)
            image_paths.append(p)
            print(f"✅ Shot {i} captured.")
            
    return image_paths

# --- 4. THE BRAIN (Orchestration) ---
def speak(text):
    def run():
        clean = re.sub(r'\[.*?\]', '', text) # Remove [CAMERA] or [CONTINUE] tags
        clean = re.sub(r'\*', '', clean).replace('"', '').replace("'", "")
        subprocess.run(["say", "-v", "Siri", clean])
    threading.Thread(target=run).start()

def extract_clean_answer(full_text):
    """
    Extracts only the final answer after the AI's thought process.
    Supports all variations of Gemma 4 thought-end tags and hallucinated ReAct tags.
    """
    # 1. Expand markers to catch Gemma 4's varied end-of-thought tokens
    markers = ["<channel|>", "</|thought|>", "<|end_thought|>", "<response>", "</thought>", "Assistant:", "Alfred:"]
    
    last_idx = -1
    marker_len = 0
    
    for marker in markers:
        idx = full_text.rfind(marker)
        if idx > last_idx:
            last_idx = idx
            marker_len = len(marker)
            
    if last_idx != -1:
        # Cut the text right after the marker
        ans = full_text[last_idx + marker_len:].strip()
    else:
        # Fallback if the model didn't use a tag properly
        ans = full_text.strip()
        
    # 2. Aggressive Regex Cleanup
    # This removes any lingering XML-style tags (<thought>, <action>, etc.)
    # and any bracketed tags ([CONTINUE], [CAMERA]) in one pass.
    ans = re.sub(r'<.*?>', '', ans)  # Removes everything between <>
    ans = re.sub(r'\[.*?\]', '', ans)  # Removes everything between []
    
    # 3. Final Polish
    # Remove lingering pipes (|) and extra whitespace
    ans = ans.replace('|', '').strip()
    
    return ans


def alfred_brain(user_query, cap):
    global CHAT_HISTORY, STATUS, CURRENT_IMAGES
    
    # --- 1. THE DECISION ENGINE ---
    STATUS = "DECIDING"

    # We build the 'Context' for Alfred to make his choice
    # We put the DECISION Prompt in the first turn to set the 'Rules' for deciding between CAMERA and CONTINUE.
    # We create the decision list. If History is empty, we merge Prompt + Query.
    if not CHAT_HISTORY:
        decision_messages = [
            {"role": "user", "content": [{"type": "text", "text": f"{DECISION_PROMPT}\n\nUSER REQUEST: {user_query}"}]}
        ]
    else:
        # History exists, so we keep System Prompt at top and append history

        # 1. Create a deep copy of CHAT_HISTORY so we don't modify the original
        decision_messages = copy.deepcopy(CHAT_HISTORY)

        # 2. Inject the DECISION_PROMPT into the VERY FIRST message of the history
        # This keeps the turn structure (user -> model -> user) perfect.
        first_content = decision_messages[0]["content"]
        # Prepend the prompt to the existing text
        for item in first_content:
            if item["type"] == "text":
                item["text"] = f"{DECISION_PROMPT}\n\nPREVIOUS CONTEXT:\n{item['text']}"
                break

        # 3. Append the new query as the final user turn      
        decision_messages.append({"role": "user", "content": [{"type": "text", "text": f"USER REQUEST: {user_query}"}]})

    # This turns our list into the high-performance Gemma 4 string
    decision_prompt = processor.apply_chat_template(decision_messages, add_generation_prompt=True)
    
    # Check if we need to pass the 'Visual Memory' (images) to help the decision
    images_to_pass = CURRENT_IMAGES if "<|image|>" in decision_prompt else []

    print(f"🧠 Alfred is evaluating the request...")
    
    # Get the [CAMERA] vs [CONTINUE] decision
    decision_result = generate(model, processor, decision_prompt, images_to_pass, temp=0.1, max_tokens=100)
    decision_text = decision_result.text.strip()
    
    print(f"🤖 Decision: {decision_text}")

    # --- 2. EXECUTION PHASE ---
    if "[CAMERA]" in decision_text:
        speak("I'll take a look. Please align the page in the viewfinder.")
        
        new_paths = capture_burst_tool(cap)
        CURRENT_IMAGES = [Image.open(p) for p in new_paths]
        
        # CLEAR IMAGES FROM HISTORY: We want the model to only "see" the 3 NEW images.
        # We keep the TEXT of the history so it remembers the conversation.
        for msg in CHAT_HISTORY:
            if isinstance(msg["content"], list):
                # We filter out the 'image' type items
                msg["content"] = [c for c in msg["content"] if c["type"] != "image"]
                # Ensure we don't have an empty content list
                if not msg["content"]:
                    msg["content"] = [{"type": "text", "text": "[Previous context]"}]

        # TASK PROMPT: Specifically for image analysis
        task_prompt = (
            "I am providing 3 images of the same book page. Use them to ensure you see all the text clearly. "
            f"Find the word or concept based on user query: '{user_query}'. "
            "Look at the images and try to explain the meaning contextually, leveraging your knowledge of language & literature. Be concise."
        )
        
        # New turn with 3 image tags
        content = [{"type": "image"} for _ in CURRENT_IMAGES]
        content.append({"type": "text", "text": task_prompt})
        CHAT_HISTORY.append({"role": "user", "content": content})
        
    else:
        # 3. CONTINUE PHASE: Answer from memory
        # We add the query to history. It will use the images from the previous turn!
        CHAT_HISTORY.append({"role": "user", "content": [{"type": "text", "text": user_query}]})

    # --- 4. FINAL RESPONSE GENERATION ---
    STATUS = "THINKING"

    # 1. Create a temporary deep copy of the history
    reasoning_context = copy.deepcopy(CHAT_HISTORY)

    # 2. Inject the ANSWERING_PROMPT into the VERY FIRST message of the history
    # This ensures the turn structure remains: User -> Model -> User -> Model
    if reasoning_context:
        first_msg_content = reasoning_context[0]["content"]
        for item in first_msg_content:
            if item["type"] == "text":
                # Prepend the rules to the existing text context
                item["text"] = f"{ANSWERING_PROMPT}\n\nCONTEXT:\n{item['text']}"
                break

    final_prompt = processor.apply_chat_template(reasoning_context, add_generation_prompt=True)
    if not final_prompt.endswith("<|thought|>\n"): 
        final_prompt += "<|thought|>\n"
    
    # Sync images with the final prompt
    final_images = CURRENT_IMAGES if "<|image|>" in final_prompt else []

    # Optional: Debug line to verify images are being sent
    print(f"DEBUG: Passing {len(final_images)} images to Vision Encoder")

    result = generate(model,
                      processor,
                      final_prompt, 
                      final_images, 
                      verbose=True,
                      temp=0.1,
                      max_tokens=800, 
                      stop_strings=["<turn|>", "<|turn|>"] # Safety: stops model from runaway chatting
                      )
    
    # --- 5. PARSE, SPEAK, AND RECORD ---
    # Use our helper function to extract only the clean answer
    # This strips away the <|thought|> tags, the <channel|> tags, and the technical [CAMERA]/[CONTINUE] tags.
    clean_ans = extract_clean_answer(result.text)

    # Update history with ONLY the clean assistant response
    # This prevents the model from seeing its previous "Thinking" on the next turn.
    CHAT_HISTORY.append({"role": "assistant", "content": [{"type": "text", "text": clean_ans}]})
    
    print(f"\n📢 ALFRED: {clean_ans}")
    speak(clean_ans)
    STATUS = "IDLE"

# --- 5. INTERACTION LOOP ---
def main():
    if not os.path.exists("captures"): os.makedirs("captures")
    
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    print("\n--- Alfred is Ambient. ---")
    
    while True:
        ret, frame = cap.read()
        if not ret: break

        # Always show the HUD
        hud = frame.copy()
        cv2.putText(hud, f"ALFRED: {STATUS}", (40, 60), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 0), 2)
        cv2.imshow("Alfred Viewfinder", cv2.resize(hud, (854, 480)))
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '): # Simulate Wake Word
            query = input("\n🗣️ You: ")
            if query.lower() in ['q', 'exit']: break
            alfred_brain(query, cap)
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
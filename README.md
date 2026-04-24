# Alfred: Local Ambient Contextual Reader Agent

Alfred is a state-of-the-art, **on-device AI reading assistant** designed for the **Apple M4 MacBook Air**. Alfred uses multimodal vision and speech-to-text to help you understand physical books in real-time. By leveraging Apple Silicon's Unified Memory, Alfred runs entirely locally—ensuring 100% privacy and sub-second latency.

---

## 🚀 Key Features

### 🧠 Dual-Brain Orchestration
Alfred uses a decoupled architecture to manage complex tasks with high reliability:
*   **The Dispatcher (Decision Brain):** A specialized prompt that evaluates user queries to decide if fresh visual context is required (**`[CAMERA]`**) or if the question can be answered from memory (**`[CONTINUE]`**).
*   **The Researcher (Answering Brain):** A dedicated persona focused on deep literary analysis, OCR, and contextual explanation.

### 👁️ Visual Working Memory
Unlike standard vision models that "forget" the image once the turn is over, Alfred maintains a **Visual Working Memory**. He captures a **3-shot high-res burst** (to solve blur and lighting issues) and keeps these images in the context window. You can ask follow-up questions about the same page (e.g., *"Who is the author referring to here?"*) without re-capturing images.

### 👂 Ambient Voice Trigger
In Voice Mode, Alfred sits in the background using a **Threaded Ear Loop**. He constantly monitors the room for the wake word **"Hey Alfred."** Once triggered, he engages in a natural voice-to-voice dialogue using `mlx-whisper`.

### 🛡️ Thread-Safe "Messenger" Architecture
To prevent macOS **"Trace Trap" crashes** (where background threads are forbidden from updating UI windows), Alfred uses a custom **Messenger Pattern**. The background "Ear" thread transcribes your voice and passes a message to the "Main Thread," which safely handles the Camera viewfinder and Gemma 4 reasoning.

---

## 🛠️ Tech Stack

-   **Brain:** [Gemma 4 E4B-it](https://huggingface.co/google/gemma-4-e4b-it) (4-bit Quantized via MLX).
-   **Ears:** [Whisper Tiny MLX](https://huggingface.co/mlx-community/whisper-tiny) (Running on the M4 Neural Engine).
-   **Vision:** OpenCV + iPhone Continuity Camera (Index 0).
-   **Core Frameworks:** `mlx-vlm` and `mlx-whisper` by Apple AI Research.
-   **Audio Engine:** SoX (High-fidelity 16kHz resampling) and macOS Native `say` command.

---

## 📂 Repository Structure

*   **`alfred_voice.py`**: The flagship ambient agent. Features hands-free wake-word detection, threaded audio processing, and the main thread HUD.
*   **`alfred_text.py`**: The manual-trigger version. Uses Spacebar to initiate queries; ideal for quiet environments.
*   **`test_devices`**: Contains `test_camera.py` and `test_ears.py`, diagnostic utilities to verify which cameras are available & microphone permissions, SoX resampling, and Whisper transcription speed.
*   **`captures/`**: Internal buffer for the 3-shot burst images and temporary audio files.
*   **`Architecture_Diagram.png`**: High level overview of how the Agent functions.

---

## 🧠 Additional Details

### 1. The Surgical Content Cleanup
To prevent memory bloat, Alfred uses a custom **Regex Parser** (`extract_clean_answer`). It identifies the transition between the model's internal `<|thought|>` channel and its external `<channel|>` output. This ensures that only clean, professional answers are saved to the long-term `CHAT_HISTORY`.

### 2. Context Injection Strategy
To maintain a strict `User -> Assistant -> User` turn structure required by MLX library, Alfred **merges** his instructions (Prompts) into the *beginning* of the first message of the conversation. This "anchors" his personality without breaking the conversation chain.

---

### 📜 The Engineering Journey: From Smart Glasses to Alfred

#### 🌟 The Vision: "Frictionless Reading"
The original inspiration for this project was a pair of **AI Smart Glasses**. Imagine reading a dense novel or a technical manual: you encounter a word like *"ephemeral"* or a concept like *"The Rosetta Stone."* Normally, you’d have to break your immersion, reach for a phone, and search for context.

I wanted to solve this by building a hands-free, voice-activated assistant that "sees" what the reader sees. To validate this vision, I decided to use my **MacBook Air M4** as a simulation environment. With its high-end compute, built-in microphone, and speakers—combined with the iPhone as a high-res camera—it provided the perfect "lab" to build the brain of what will eventually live in a pair of glasses.

---

#### 🛠 Chapter 1: The Optical Hurdle & The "Burst" Innovation
*   **The Problem:** I started with the Mac's built-in webcam, but it had a fixed focus. Book text was a blurry mess, and single frames often came back pitch black due to slow auto-exposure. Alfred was essentially "blind."
*   **The Pivot:** I integrated the **iPhone Continuity Camera**.
*   **The Solution:** Even with better hardware, one shot wasn't enough. I architected a **3-Shot Burst Tool**. By guiding the user through a 10s alignment window and three staggered shots, Alfred could "cross-reference" the text, achieving nearly 100% OCR accuracy.

#### 🧠 Chapter 2: The Memory Crisis (Visual Working Memory)
*   **The Requirement:** To feel like a real assistant, Alfred had to remember the page. If I asked a follow-up question, he shouldn't need a new photo.
*   **The Hurdle:** This led to constant **`StopIteration` crashes**. I discovered that local multimodal models are extremely strict: the number of `<|image|>` tags in the conversation history **must** exactly match the images in RAM.
*   **The Solution:** I engineered **Dynamic Context Sanitization**. Alfred now "scrubs" old image tags only when a new burst is triggered, allowing him to "re-scan" the same pixels across multiple conversational turns without crashing.

#### 🎭 Chapter 3: The "Double-Think" & Dual-Brain Logic
*   **The Problem:** Gemma 4 suffered an "Identity Crisis." It would repeat my prompts or leak its internal "Thinking" monologue into the spoken response.
*   **The Pivot:** I decoupled Alfred into a **Dual-Brain Architecture**:
    1.  **The Dispatcher:** A switcher that only decides: "Do I need the camera or can I answer from memory?"
    2.  **The Researcher:** A focused persona that only explains the text.
*   **The Innovation:** I implemented **In-Place Context Injection**. By merging instructions into the *beginning* of the first history turn, I maintained the strict `User -> Model` structure required by the M4 hardware while anchoring Alfred’s identity.

#### ✍️ Chapter 4: Linguistic Physics (Advanced Prompt Engineering)
*   **The Problem:** Even with the Dual-Brain setup, the 4B model was inconsistent. It would often skip the `<channel|>` separator or hallucinate "ReAct" tags like `<observation>`, making the output messy.
*   **The Experiment:** I initially used specific storytelling examples, but the model started "mimicking" the vocabulary instead of reasoning.
*   **The Breakthrough:** I pivoted to **Meta-Templates**. I provided a structural map using placeholders like `[Your internal analysis]` instead of specific words. This forced the model to fill in the logic itself while strictly adhering to the token rules.
*   **The Result:** By defining a **Mandatory Transition** rule and using a **Surgical Cut Regex Parser**, I ensured that Siri only ever speaks the clean final answer, never the "mental sandbox" behind it.

#### 🎙️ Chapter 4: The "Trace Trap" & The Ambient Ear
*   **The Goal:** Make Alfred truly hands-free using **mlx-whisper** for a "Hey Alfred" wake-word.
*   **The Crisis:** Moving the audio listener to a background thread caused an immediate **macOS `zsh: trace trap` crash**. I hit a hard OS limit: background threads are forbidden from updating UI/OpenCV windows on macOS.
*   **The Final Fix:** The **Main-Thread Messenger Pattern**. I moved the "Ear" to a background thread to handle transcription and created a global `pending_query` flag. The Main Thread (the UI owner) now "picks up" the voice command and safely triggers the Brain.

---

#### ✅ The Result: A Living Prototype
Alfred is now a perfectly stable, hands-free, visual-memory-capable agent. He manages hardware, handles high-concurrency threading, and performs high-level literary reasoning. This project proves that the "Smart Glasses" brain is not only possible but can run entirely **on-device, privately, and locally.**

---

### 🛠 Summary of Technical Milestones

| Milestone | Technical Hurdle | Engineering Solution |
| :--- | :--- | :--- |
| **Vision** | Fixed-focus blur & Black frames | **3-Shot Burst + iPhone Continuity** |
| **Memory** | Tag-Image Mismatch (`StopIteration`) | **Dynamic Image Tag Sanitization** |
| **Stability** | User-User Turn Collisions | **In-Place Context Injection** |
| **Precision** | Thought-Leaking & Hallucination | **Meta-Template Prompting + Regex Parser** |
| **Concurrency** | macOS Trace Trap (UI Threading) | **Main-Thread Messenger Pattern** |

## ⚙️ Setup & Installation

### Prerequisites
1.  **Hardware:** Apple Silicon Mac and minimum 8GB RAM (Tested on M4, 16GB+ RAM, can try with other variations).
2.  **System Tools:**
    ```bash
    brew install sox ffmpeg
    ```
3.  **Model Access:** Visit [Hugging Face](https://huggingface.co/google/gemma-4-e4b-it) to accept the Gemma 4 terms of service.

### Installation
```bash
# Clone the repository
git clone https://github.com/Araz1103/ReaderAgent.git
cd ReaderAgent

# Create a virtual environment (Python 3.12+ recommended)
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Login to Hugging Face (to download gated weights)
huggingface-cli login
```

---

## 🎮 How to Run

### Mode A: Ambient Voice (Hands-Free)
```bash
python alfred_voice.py
```
1.  Align your book using the **Viewfinder** window.
2.  Say **"Hey Alfred"**.
3.  Wait for **"Yes? How can I help?"** and ask your question.
4.  Alfred will guide you through the capture burst and speak the explanation.

### Mode B: Manual Text
```bash
python alfred_text.py
```
1.  Align your book.
2.  Press **Spacebar** to trigger a query.
3.  Type your question in the terminal.

---

## 📄 License
MIT License. Created for Research and Personal Productivity.
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
*   **`Architecture_Diagram.png/`**: High level overview of how the Agent functions.

---

## 🧠 Additional Details

### 1. The Surgical Content Cleanup
To prevent memory bloat, Alfred uses a custom **Regex Parser** (`extract_clean_answer`). It identifies the transition between the model's internal `<|thought|>` channel and its external `<channel|>` output. This ensures that only clean, professional answers are saved to the long-term `CHAT_HISTORY`.

### 2. Context Injection Strategy
To maintain a strict `User -> Assistant -> User` turn structure required by MLX library, Alfred **merges** his instructions (Prompts) into the *beginning* of the first message of the conversation. This "anchors" his personality without breaking the conversation chain.

---

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
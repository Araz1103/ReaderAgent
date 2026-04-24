import mlx_whisper
import subprocess
import os

# We use the tiny model for maximum speed on the M4
WHISPER_MODEL = "mlx-community/whisper-tiny"

def listen_test():
    audio_path = "test_audio.wav"
    print("🎤 RECORDING... say 'Hey Alfred, what is a mochi?'")
    
    # Records for 4 seconds
    subprocess.run(["rec", "-r", "16000", "-c", "1", audio_path, "trim", "0", "4"])
    
    print("🧠 TRANSCRIBING...")
    result = mlx_whisper.transcribe(audio_path, path_or_hf_repo=WHISPER_MODEL)
    print(f"🗣️  I HEARD: {result['text']}")

if __name__ == "__main__":
    listen_test()
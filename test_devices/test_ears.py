import mlx_whisper
import subprocess
import os
import time

# We use the tiny model for maximum speed on the M4
WHISPER_MODEL = "mlx-community/whisper-tiny"

def listen_test():
    audio_path = "test_audio.wav"

    for i in range(5):
        print(f"🔄 Attempt {i+1}/5")
        print("🎤 RECORDING... say 'Hey Alfred, what is a mochi?'")
        
        # Records for 4 seconds
        # -q: Quiet mode (clean terminal)
        # -c 1: Mono channel
        # rate 16k (at the end): Resamples the FILE to 16kHz instead of forcing the mic hardware
        try:
            subprocess.run(["rec", "-q", "-c", "1", audio_path, "rate", "16k", "trim", "0", "2.5"], check=True)
            #subprocess.run(["rec", "-r", "16000", "-c", "1", audio_path, "trim", "0", "4"])
            
            print("🧠 TRANSCRIBING...")
            start_time = time.time()
            result = mlx_whisper.transcribe(audio_path, path_or_hf_repo=WHISPER_MODEL)
            end_time = time.time()
            print(f"🗣️  I HEARD: {result['text']}")
            print(f"⚡ Speed: {end_time - start_time:.2f} seconds")
        except Exception as e:
            print(f"❌ Error: {e}")
            continue # Ignore minor audio glitches

if __name__ == "__main__":
    listen_test()
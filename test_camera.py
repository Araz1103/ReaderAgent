import cv2
import time

def test_indices():
    # Try indices 0 through 2
    for index in [0, 1, 2]:
        print(f"Testing Camera Index {index}...")
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            print(f"❌ Index {index} is not available.")
            continue
        
        print(f"✅ Index {index} opened! Looking for green light...")
        # Try to capture 5 frames
        for i in range(5):
            ret, frame = cap.read()
            if ret:
                filename = f"test_cam_{index}.jpg"
                cv2.imwrite(filename, frame)
                print(f"  - Captured frame! Saved as {filename}")
            time.sleep(0.5)
        
        cap.release()
        print(f"Index {index} released.\n")

def find_iphone():
    # We check 0-5 to find the iPhone
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Get the name/backend info
            print(f"Index {i} is available.")
            ret, frame = cap.read()
            if ret:
                # iPhone frames are usually vertical (higher height than width) 
                # or have a specific high resolution.
                h, w, _ = frame.shape
                print(f"  Resolution: {w}x{h}")
            cap.release()


if __name__ == "__main__":
    test_indices()
    find_iphone()
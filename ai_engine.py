import os
import pickle
import logging
from datetime import datetime

try:
    import cv2
except ImportError:
    cv2 = None

import numpy as np

try:
    import mediapipe as mp
except ImportError:
    mp = None

try:
    from deepface import DeepFace
except ImportError:
    DeepFace = None

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Consistent parameters across all methods
DETECTOR_BACKEND = 'retinaface'
MODEL_NAME = 'Facenet512'


class FaceDetectionEngine:
    def __init__(self):
        self.use_deepface = DeepFace is not None
        if mp is None and not self.use_deepface:
            logger.warning("MediaPipe and DeepFace not installed. Face detection will not work.")
            self.face_detection = None
            return

        if mp is not None:
            self.mp_face_detection = mp.solutions.face_detection
            self.mp_drawing = mp.solutions.drawing_utils
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.5
            )
        else:
            self.face_detection = None

    def detect_face(self, frame):
        """Detect faces in frame using DeepFace or MediaPipe"""
        if cv2 is None:
            logger.warning("OpenCV not installed. Face detection will not work.")
            return []

        # Prefer DeepFace if available
        if self.use_deepface:
            return self._detect_with_deepface(frame)

        # Fallback to MediaPipe
        if self.face_detection is None:
            logger.warning("Face detection not available.")
            return []
        return self._detect_with_mediapipe(frame)

    def _detect_with_deepface(self, frame):
        """Detect faces using DeepFace"""
        temp_path = os.path.join(Config.TRAINED_MODEL_FOLDER, 'temp_detect.jpg')
        try:
            os.makedirs(Config.TRAINED_MODEL_FOLDER, exist_ok=True)
            resized_frame = cv2.resize(frame, (640, 640))
            
            # ✅ Fix 1 & 2: Save frame before passing to DeepFace
            cv2.imwrite(temp_path, resized_frame)

            # ✅ Fix 4: Use consistent detector_backend
            faces = DeepFace.extract_faces(
                img_path=temp_path,
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=False
            )

            result = []
            for face in faces:
                facial_area = face['facial_area']
                result.append({
                    'bbox': (facial_area['x'], facial_area['y'],
                             facial_area['w'], facial_area['h']),
                    'confidence': face.get('confidence', 0.0)
                })

            return result
        except Exception as e:
            logger.error(f"DeepFace detection error: {e}")
            if self.face_detection is not None:
                return self._detect_with_mediapipe(frame)
            return []
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _detect_with_mediapipe(self, frame):
        """Detect faces using MediaPipe"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_frame)

        faces = []
        if results.detections:
            h, w, _ = frame.shape
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)

                faces.append({
                    'bbox': (x, y, width, height),
                    'confidence': float(detection.score[0])
                })

        return faces

    def draw_faces(self, frame, faces):
        """Draw bounding boxes around detected faces"""
        if cv2 is None:
            return frame
        for face in faces:
            x, y, w, h = face['bbox']
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"Conf: {face['confidence']:.2f}",
                        (x, max(10, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame

    def __del__(self):
        if hasattr(self, 'face_detection') and self.face_detection:
            self.face_detection.close()


class FaceRecognitionEngine:
    def __init__(self):
        self.known_face_ids = []
        self.known_face_names = []
        self.model_path = os.path.join(Config.TRAINED_MODEL_FOLDER, 'face_data.pkl')
        self.load_model()

    def load_model(self):
        """Load trained face recognition data"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_ids = data.get('ids', [])
                    self.known_face_names = data.get('names', [])
                logger.info(f"Loaded face recognition data with {len(self.known_face_ids)} employees")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self.known_face_ids = []
                self.known_face_names = []

    def save_model(self):
        """Save trained face recognition data"""
        os.makedirs(Config.TRAINED_MODEL_FOLDER, exist_ok=True)
        data = {
            'ids': self.known_face_ids,
            'names': self.known_face_names
        }
        with open(self.model_path, 'wb') as f:
            pickle.dump(data, f)

        logger.info(f"Model saved with {len(self.known_face_ids)} employees")

    def train_employee(self, employee_id, employee_name, image_paths):
        """Register employee face images"""
        if DeepFace is None:
            logger.warning("DeepFace not installed. Training will not work.")
            return 0

        valid_images = 0

        for img_path in image_paths:
            try:
                # Check image exists
                if not os.path.exists(img_path):
                    logger.warning(f"Image not found: {img_path}")
                    continue

                # Read image with OpenCV
                image = cv2.imread(img_path)

                if image is None:
                    logger.warning(f"Could not read image: {img_path}")
                    continue

                # Debug information
                logger.info(f"Processing: {img_path}")
                logger.info(f"Image type: {type(image)}")
                logger.info(f"Image shape: {image.shape}")

                # Detect face
                faces = DeepFace.extract_faces(
                img_path=img_path,
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=False
            )

                if faces and len(faces) > 0:
                    valid_images += 1
                    logger.info(f"✅ Valid face detected in {img_path}")
                else:
                    logger.warning(f"❌ No face detected in {img_path}")

            except Exception as e:
                logger.exception(f"Error processing {img_path}")

        if valid_images > 0:

            if employee_id not in self.known_face_ids:
                self.known_face_ids.append(employee_id)
                self.known_face_names.append(employee_name)

            self.save_model()

            logger.info(
                f"Registered employee {employee_name} with {valid_images} valid images"
            )

            return valid_images

        logger.warning("No valid images found for training.")
        return 0

    def recognize_face(self, frame, tolerance=0.6, target_employee_id=None):
        """
        Recognize face in frame using DeepFace.verify()
        """
        if DeepFace is None:
            logger.warning("DeepFace not installed.")
            return []
        if len(self.known_face_ids) == 0:
            logger.warning("No trained employees available.")
            return []
        results = []
        temp_path = os.path.join(
            Config.TRAINED_MODEL_FOLDER,
            "temp_frame.jpg"
        )
        try:
            os.makedirs(
                Config.TRAINED_MODEL_FOLDER,
                exist_ok=True
            )
            # Resize frame
            resized_frame = cv2.resize(
                frame,
                (640, 640)
            )
            success = cv2.imwrite(
                temp_path,
                resized_frame
            )
            print("\n========== TEMP IMAGE DEBUG ==========")
            print("Temp Path :", temp_path)
            print("Write Success :", success)
            print("File Exists :", os.path.exists(temp_path))
            if os.path.exists(temp_path):
                print(
                    "File Size :",
                    os.path.getsize(temp_path),
                    "bytes"
                )
            print("======================================\n")
            # Load temp image as numpy array
            temp_image = cv2.imread(temp_path)
            if temp_image is None:
                print("ERROR: Temp image loading failed")
                return []
            bbox = None
            # Face detection
            try:
                faces = DeepFace.extract_faces(
                    img_path=temp_image,
                    detector_backend="opencv",
                    enforce_detection=False
                )
                if faces:
                    facial_area = faces[0]["facial_area"]
                    bbox = (
                        facial_area["x"],
                        facial_area["y"],
                        facial_area["w"],
                        facial_area["h"]
                    )
            except Exception as e:
                print(
                    "Bbox Error:",
                    e
                )
            best_match_id = None
            min_distance = float("inf")
            print("\n")
            print("=" * 70)
            print("FACE RECOGNITION START")
            print("MODEL :", MODEL_NAME)
            print("BACKEND : opencv")
            if target_employee_id:
                print(
                    "OPTIMIZED MODE: Checking Employee ID:",
                    target_employee_id
                )
            else:
                print(
                    "STANDARD MODE: Checking all employees"
                )
            print("=" * 70)
            # Select employees
            if target_employee_id:
                if target_employee_id in self.known_face_ids:
                    employees_to_check = [
                        target_employee_id
                    ]
                else:
                    print(
                        "Employee not found:",
                        target_employee_id
                    )
                    return []
            else:
                employees_to_check = self.known_face_ids
            # Compare images
            for employee_id in employees_to_check:
                employee_folder = os.path.join(
                    Config.DATASET_FOLDER,
                    str(employee_id)
                )
                if not os.path.exists(employee_folder):
                    continue
                employee_images = [
                    f for f in os.listdir(employee_folder)
                    if f.lower().endswith(
                        (
                            ".jpg",
                            ".jpeg",
                            ".png"
                        )
                    )
                ]
                print(
                    "\nChecking Employee ID:",
                    employee_id
                )
                print(
                    "Total Images:",
                    len(employee_images)
                )
                for img_file in employee_images:
                    img_path = os.path.join(
                        employee_folder,
                        img_file
                    )
                    try:
                        print("\nComparing Images")
                        print(
                            "IMG1:",
                            temp_path
                        )
                        print(
                            "IMG2:",
                            img_path
                        )
                        # Load employee image
                        employee_image = cv2.imread(
                            img_path
                        )
                        if employee_image is None:
                            print(
                                "Employee image load failed"
                            )
                            continue
                        result = DeepFace.verify(
                            img1_path=temp_image,
                            img2_path=employee_image,
                            model_name=MODEL_NAME,
                            detector_backend="opencv",
                            enforce_detection=False
                        )
                        print("-"*60)
                        print(
                            "Image:",
                            img_file
                        )
                        print(
                            "Verified:",
                            result.get("verified")
                        )
                        print(
                            "Distance:",
                            result.get("distance")
                        )
                        print("-"*60)
                        if result.get(
                            "verified",
                            False
                        ):
                            distance = result.get(
                                "distance",
                                1.0
                            )
                            if distance < 0.38:
                                print(
                                    ">>> ACCEPTED <<<"
                                )
                                if distance < min_distance:
                                    min_distance = distance
                                    best_match_id = employee_id
                    except Exception as e:
                        print(
                            "Verification Error:",
                            e
                        )
                        continue
            print("="*70)
            print(
                "BEST MATCH:",
                best_match_id
            )
            print(
                "MIN DISTANCE:",
                min_distance
            )
            print("="*70)
            name = "Unknown"
            matched_employee_id = None
            confidence = 0.0
            if best_match_id is not None:
                idx = self.known_face_ids.index(
                    best_match_id
                )
                name = self.known_face_names[idx]
                matched_employee_id = best_match_id
                confidence = max(
                    0.0,
                    min(
                        1.0,
                        1.0 - min_distance
                    )
                )
            results.append({
                "name": name,
                "employee_id": matched_employee_id,
                "confidence": round(
                    confidence,
                    2
                ),
                "bbox": bbox
            })
        except Exception as e:
            logger.exception(
                f"Recognition Error : {e}"
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(
                    temp_path
                )

        return results
    def remove_employee(self, employee_id):
        """Remove employee from face recognition model"""
        if employee_id in self.known_face_ids:
            index = self.known_face_ids.index(employee_id)
            del self.known_face_ids[index]
            del self.known_face_names[index]

            employee_folder = os.path.join(Config.DATASET_FOLDER, str(employee_id))
            if os.path.exists(employee_folder):
                import shutil
                shutil.rmtree(employee_folder)

            self.save_model()
            return 1
        return 0


class FaceCapture:
    def __init__(self, employee_id, num_images=20):
        self.employee_id = employee_id
        self.num_images = num_images
        self.captured_count = 0
        self.cap = None
        self.detector = FaceDetectionEngine()
        self.save_dir = os.path.join(Config.DATASET_FOLDER, str(employee_id))
        os.makedirs(self.save_dir, exist_ok=True)

    def start_capture(self):
        """Start webcam capture"""
        if cv2 is None:
            raise Exception("OpenCV not installed. Cannot capture from webcam.")
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise Exception("Could not open webcam")
        return self.cap

    def capture_frame(self):
        """Capture frame and save cropped face for better accuracy"""
        if cv2 is None:
            return None, False
        ret, frame = self.cap.read()
        if not ret:
            return None, False

        faces = self.detector.detect_face(frame)
        drawn_frame = self.detector.draw_faces(frame.copy(), faces)

        # ✅ Fix 7: Save Cropped Face instead of full frame
        if len(faces) > 0 and self.captured_count < self.num_images:
            x, y, w, h = faces[0]['bbox']
            
            # Boundary check
            h_img, w_img, _ = frame.shape
            x, y = max(0, x), max(0, y)
            w, h = min(w_img - x, w), min(h_img - y, h)

            if w > 0 and h > 0:
                face_crop = frame[y:y+h, x:x+w]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                img_path = os.path.join(self.save_dir, f"{timestamp}.jpg")
                cv2.imwrite(img_path, face_crop)
                self.captured_count += 1
                return drawn_frame, True

        return drawn_frame, False

    def stop_capture(self):
        """Stop webcam capture"""
        if self.cap:
            self.cap.release()
        if cv2 is not None:
            cv2.destroyAllWindows()

    def get_captured_images(self):
        """Get list of captured images"""
        if os.path.exists(self.save_dir):
            return [os.path.join(self.save_dir, f) for f in os.listdir(self.save_dir)
                    if f.endswith(('.jpg', '.jpeg', '.png'))]
        return []


def train_all_employees():
    """Train face recognition for all employees with face images"""
    if cv2 is None:
        logger.warning("OpenCV not installed. Training will not work.")
        return
    recognizer = FaceRecognitionEngine()

    if not os.path.exists(Config.DATASET_FOLDER):
        logger.warning("Dataset folder does not exist")
        return

    for employee_folder in os.listdir(Config.DATASET_FOLDER):
        employee_path = os.path.join(Config.DATASET_FOLDER, employee_folder)
        if os.path.isdir(employee_path):
            employee_id = employee_folder
            image_paths = [os.path.join(employee_path, f) for f in os.listdir(employee_path)
                           if f.endswith(('.jpg', '.jpeg', '.png'))]

            if len(image_paths) >= getattr(Config, 'MIN_FACE_IMAGES_REQUIRED', 1):
                from models import Employee
                employee = Employee.query.filter_by(id=int(employee_id)).first()
                if employee:
                    recognizer.train_employee(employee_id, employee.name, image_paths)
                    logger.info(f"Trained employee {employee.name} with {len(image_paths)} images")
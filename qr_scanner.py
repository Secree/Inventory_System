"""
QR Code Scanner for Water Gallon Inventory System
Detects and decodes QR codes from camera or image files
"""

import cv2
import numpy as np
from PIL import Image


class QRCodeScanner:
    def __init__(self):
        """Initialize QR code scanner"""
        self.last_scanned_data = None
    
    def scan_from_image(self, image_path):
        """
        Scan QR code from an image file
        
        Args:
            image_path: Path to the image file
        
        Returns:
            tuple: (success, data_dict, message)
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            
            if image is None:
                return False, None, "Could not read image file"
            
            # Use OpenCV's QRCodeDetector
            qr_detector = cv2.QRCodeDetector()
            qr_data, bbox, _ = qr_detector.detectAndDecode(image)
            
            if not qr_data:
                return False, None, "No QR code found in image"
            
            # Parse QR code data
            data_dict = self._parse_qr_data(qr_data)
            
            if data_dict:
                self.last_scanned_data = data_dict
                return True, data_dict, "QR code scanned successfully"
            else:
                return False, None, "Invalid QR code format"
            
        except Exception as e:
            return False, None, f"Error scanning QR code: {str(e)}"
    
    def scan_from_camera(self, camera_index=0, timeout=30):
        """
        Scan QR code from camera feed
        
        Args:
            camera_index: Camera device index (default 0)
            timeout: Timeout in seconds
        
        Returns:
            tuple: (success, data_dict, message)
        """
        try:
            # Open camera
            cap = cv2.VideoCapture(camera_index)
            
            if not cap.isOpened():
                return False, None, "Could not open camera"
            
            print("Camera opened. Point camera at QR code...")
            print("Press 'q' to cancel")
            
            # Create QR code detector
            qr_detector = cv2.QRCodeDetector()
            
            frame_count = 0
            max_frames = timeout * 30  # Assuming 30 FPS
            
            while frame_count < max_frames:
                # Read frame
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Detect and decode QR code
                qr_data, bbox, _ = qr_detector.detectAndDecode(frame)
                
                # Draw rectangle around detected QR code
                if bbox is not None and len(bbox) > 0:
                    bbox = bbox.astype(int)
                    cv2.polylines(frame, [bbox], True, (0, 255, 0), 3)
                    cv2.putText(frame, "QR Code Detected!", (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Display frame
                cv2.imshow('QR Code Scanner - Press Q to cancel', frame)
                
                # Check if QR code found
                if qr_data:
                    data_dict = self._parse_qr_data(qr_data)
                    
                    if data_dict:
                        cap.release()
                        cv2.destroyAllWindows()
                        self.last_scanned_data = data_dict
                        return True, data_dict, "QR code scanned successfully"
                
                # Check for exit key
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                frame_count += 1
            
            # Cleanup
            cap.release()
            cv2.destroyAllWindows()
            
            return False, None, "No QR code detected or timeout reached"
            
        except Exception as e:
            # Ensure cleanup
            try:
                cap.release()
                cv2.destroyAllWindows()
            except:
                pass
            
            return False, None, f"Error scanning from camera: {str(e)}"
    
    def _parse_qr_data(self, qr_data):
        """
        Parse QR code data into dictionary
        Expected format: "INVENTORY_ID:GAL001|NAME:Blue Container"
        
        Args:
            qr_data: Raw QR code data string
        
        Returns:
            dict: Parsed data or None if invalid
        """
        try:
            data_dict = {}
            
            # Split by pipe separator
            parts = qr_data.split('|')
            
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    data_dict[key.strip()] = value.strip()
            
            # Validate required fields
            if 'INVENTORY_ID' in data_dict and 'NAME' in data_dict:
                return {
                    'inventory_id': data_dict['INVENTORY_ID'],
                    'name': data_dict['NAME']
                }
            
            return None
            
        except Exception as e:
            print(f"Error parsing QR data: {e}")
            return None
    
    def decode_qr_from_numpy(self, frame):
        """
        Decode QR code from a numpy array (OpenCV frame)
        Useful for real-time camera processing
        
        Args:
            frame: Numpy array representing the image
        
        Returns:
            tuple: (success, data_dict, message)
        """
        try:
            decoded_objects = pyzbar.decode(frame)
            
            if not decoded_objects:
                return False, None, "No QR code found"
            
            qr_data = decoded_objects[0].data.decode('utf-8')
            data_dict = self._parse_qr_data(qr_data)
            
            if data_dict:
                return True, data_dict, "QR code decoded successfully"
            else:
                return False, None, "Invalid QR code format"
            
        except Exception as e:
            return False, None, f"Error decoding QR code: {str(e)}"
    
    def get_last_scanned(self):
        """Get the last successfully scanned QR code data"""
        return self.last_scanned_data


if __name__ == '__main__':
    # Test QR code scanner
    scanner = QRCodeScanner()
    
    print("QR Code Scanner Test")
    print("1. Scan from image file")
    print("2. Scan from camera")
    
    choice = input("Enter choice (1 or 2): ")
    
    if choice == '1':
        image_path = input("Enter image path: ")
        success, data, message = scanner.scan_from_image(image_path)
        print(f"\n{message}")
        if success:
            print(f"Scanned data: {data}")
    
    elif choice == '2':
        success, data, message = scanner.scan_from_camera()
        print(f"\n{message}")
        if success:
            print(f"Scanned data: {data}")

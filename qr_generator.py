"""
QR Code Generator for Water Gallon Inventory System
Generates unique QR codes for each gallon
"""

import qrcode
import os
from PIL import Image


class QRCodeGenerator:
    def __init__(self, output_dir='qr_codes'):
        """Initialize QR code generator"""
        self.output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """Create output dir and make sure it is writable"""
        os.makedirs(self.output_dir, exist_ok=True)
        if not os.access(self.output_dir, os.W_OK):
            try:
                os.chmod(self.output_dir, 0o755)
            except Exception as exc:
                raise PermissionError(
                    f"Output directory '{self.output_dir}' is not writable"
                ) from exc
    
    def generate_qr(self, inventory_id, name, save_path=None):
        """
        Generate QR code for a gallon
        
        Args:
            inventory_id: Unique inventory ID
            name: Name of the gallon
            save_path: Optional custom save path
        
        Returns:
            tuple: (success, message, file_path)
        """
        try:
            self._ensure_output_dir()
            # Create QR code data (JSON-like format)
            qr_data = f"INVENTORY_ID:{inventory_id}|NAME:{name}"
            
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,  # Controls size (1-40)
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction
                box_size=10,  # Size of each box in pixels
                border=4,  # Border size in boxes
            )
            
            # Add data
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Determine save path
            if save_path is None:
                save_path = os.path.join(self.output_dir, f"{inventory_id}.png")
            
            # Save image
            img.save(save_path)
            
            return True, "QR code generated successfully", save_path
            
        except Exception as e:
            return False, f"Error generating QR code: {str(e)}", None
    
    def generate_qr_with_label(self, inventory_id, name, save_path=None):
        """
        Generate QR code with text label
        
        Args:
            inventory_id: Unique inventory ID
            name: Name of the gallon
            save_path: Optional custom save path
        
        Returns:
            tuple: (success, message, file_path)
        """
        try:
            self._ensure_output_dir()
            from PIL import ImageDraw, ImageFont
            
            # Generate basic QR code first
            qr_data = f"INVENTORY_ID:{inventory_id}|NAME:{name}"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=4,
                border=4,
            )
            
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert QR image to RGB if needed
            if qr_img.mode != 'RGB':
                qr_img = qr_img.convert('RGB')
            
            # Create new image with space for text
            qr_width, qr_height = qr_img.size
            new_height = qr_height + 80  # Add space for text
            
            new_img = Image.new('RGB', (qr_width, new_height), 'white')
            new_img.paste(qr_img, (0, 0))
            
            # Add text
            draw = ImageDraw.Draw(new_img)
            
            try:
                # Try to use a nicer font
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                # Fallback to default font - use basic font size
                font = ImageFont.load_default()
            
            # Draw inventory ID
            text1 = f"ID: {inventory_id}"
            text2 = f"{name}"
            
            # Calculate text position (centered) using getbbox which is more compatible
            try:
                # Use getbbox method for better compatibility
                bbox1 = font.getbbox(text1)
                text1_width = bbox1[2] - bbox1[0]
                text1_x = (qr_width - text1_width) // 2
                
                bbox2 = font.getbbox(text2)
                text2_width = bbox2[2] - bbox2[0]
                text2_x = (qr_width - text2_width) // 2
            except:
                # Fallback to approximate centering
                text1_width = len(text1) * 6
                text1_x = max(0, (qr_width - text1_width) // 2)
                
                text2_width = len(text2) * 6
                text2_x = max(0, (qr_width - text2_width) // 2)
            
            draw.text((text1_x, qr_height + 10), text1, fill='black', font=font)
            draw.text((text2_x, qr_height + 40), text2, fill='black', font=font)
            
            # Determine save path
            if save_path is None:
                save_path = os.path.join(self.output_dir, f"{inventory_id}_labeled.png")
            
            # Save image
            new_img.save(save_path)
            
            return True, "QR code with label generated successfully", save_path
            
        except Exception as e:
            return False, f"Error generating labeled QR code: {str(e)}", None
    
    def generate_batch_qr(self, gallons_list):
        """
        Generate QR codes for multiple gallons
        
        Args:
            gallons_list: List of dictionaries with 'inventory_id' and 'name'
        
        Returns:
            tuple: (success_count, failed_count, results)
        """
        success_count = 0
        failed_count = 0
        results = []
        
        for gallon in gallons_list:
            inventory_id = gallon.get('inventory_id')
            name = gallon.get('name')
            
            if not inventory_id or not name:
                failed_count += 1
                results.append({
                    'inventory_id': inventory_id,
                    'status': 'failed',
                    'message': 'Missing inventory_id or name'
                })
                continue
            
            success, message, file_path = self.generate_qr_with_label(inventory_id, name)
            
            if success:
                success_count += 1
                results.append({
                    'inventory_id': inventory_id,
                    'status': 'success',
                    'message': message,
                    'file_path': file_path
                })
            else:
                failed_count += 1
                results.append({
                    'inventory_id': inventory_id,
                    'status': 'failed',
                    'message': message
                })
        
        return success_count, failed_count, results


if __name__ == '__main__':
    # Test QR code generation
    generator = QRCodeGenerator()
    
    # Test single QR code
    success, message, path = generator.generate_qr_with_label('GAL001', 'Blue 5-Gallon Container')
    print(f"{message}")
    if success:
        print(f"QR code saved to: {path}")

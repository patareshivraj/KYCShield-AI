import os
import time
from PIL import Image
import numpy as np

# Create mock files
os.makedirs("tests/fixtures", exist_ok=True)

# 1. Normal PDF
with open("tests/fixtures/Aadhaar.pdf", "wb") as f:
    f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n198\n%%EOF\n")

with open("tests/fixtures/BankStatement.pdf", "wb") as f:
    f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n198\n%%EOF\n")

# 2. Normal Image
img = Image.fromarray(np.uint8(np.random.rand(800, 600, 3) * 255))
img.save("tests/fixtures/PAN.jpg")

# 3. Large File
with open("tests/fixtures/large.pdf", "wb") as f:
    f.seek(15 * 1024 * 1024)
    f.write(b"0")

# 4. Exe File
with open("tests/fixtures/malicious.exe", "wb") as f:
    f.write(b"MZ executable")

# 5. Rotated Image
img_rot = img.rotate(90, expand=True)
img_rot.save("tests/fixtures/rotated.jpg")

# 6. Cropped Image (edges filled to simulate crop)
img_crop = np.zeros((800, 600, 3), dtype=np.uint8)
img_crop[10:790, 10:590] = 255
Image.fromarray(img_crop).save("tests/fixtures/cropped.jpg")

print("Fixtures created.")

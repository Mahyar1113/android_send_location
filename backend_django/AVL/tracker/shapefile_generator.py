import os
import struct
from datetime import datetime

def generate_shapefile(points, directory, base_name):
    if not points or len(points) < 2:
        raise ValueError("At least 2 points are required for a Polyline.")

    if not os.path.exists(directory):
        os.makedirs(directory)
    
    shp_file = os.path.join(directory, f"{base_name}.shp")
    shx_file = os.path.join(directory, f"{base_name}.shx")
    dbf_file = os.path.join(directory, f"{base_name}.dbf")

    coords = [[p['longitude'], p['latitude']] for p in points]

    write_shp_file(coords, shp_file)
    write_shx_file(coords, shx_file)
    write_dbf_file(coords, dbf_file)

def write_shp_file(points, shp_file):
    num_points = len(points)
    record_content_length = 4 + 32 + 4 + 4 + (4 * 1) + (16 * num_points)  # Shape Type + Bounding Box + NumParts + NumPoints + Parts + Points
    file_length = 100 + 8 + record_content_length  # Header + Record Header + Content
    file_length_words = file_length // 2

    with open(shp_file, 'wb') as f:
        # File Header (Big Endian)
        f.write(struct.pack('>i', 9994))  # File Code
        f.write(struct.pack('>5i', 0, 0, 0, 0, 0))  # Unused
        f.write(struct.pack('>i', file_length_words))  # File Length
        # Data (Little Endian)
        f.write(struct.pack('<i', 1000))  # Version
        f.write(struct.pack('<i', 3))  # Shape Type (Polyline)

        # Bounding Box
        min_x = min(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_x = max(p[0] for p in points)
        max_y = max(p[1] for p in points)
        f.write(struct.pack('<4d', min_x, min_y, max_x, max_y))  # Xmin, Ymin, Xmax, Ymax
        f.write(struct.pack('<4d', 0.0, 0.0, 0.0, 0.0))  # Zmin, Zmax, Mmin, Mmax

        # Record Header (Big Endian)
        f.write(struct.pack('>i', 1))  # Record Number
        f.write(struct.pack('>i', record_content_length // 2))  # Content Length

        # Record Contents (Little Endian)
        f.write(struct.pack('<i', 3))  # Shape Type (Polyline)
        f.write(struct.pack('<4d', min_x, min_y, max_x, max_y))  # Bounding Box
        f.write(struct.pack('<i', 1))  # NumParts
        f.write(struct.pack('<i', num_points))  # NumPoints
        f.write(struct.pack('<i', 0))  # Parts Index
        for lon, lat in points:
            f.write(struct.pack('<2d', lon, lat))  # Points

def write_shx_file(points, shx_file):
    num_points = len(points)
    record_content_length = 4 + 32 + 4 + 4 + (4 * 1) + (16 * num_points)
    file_length = 100 + 8  # Header + 1 Record
    file_length_words = file_length // 2

    with open(shx_file, 'wb') as f:
        # File Header (Big Endian)
        f.write(struct.pack('>i', 9994))  # File Code
        f.write(struct.pack('>5i', 0, 0, 0, 0, 0))  # Unused
        f.write(struct.pack('>i', file_length_words))  # File Length
        # Data (Little Endian)
        f.write(struct.pack('<i', 1000))  # Version
        f.write(struct.pack('<i', 3))  # Shape Type
        # Bounding Box
        min_x = min(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_x = max(p[0] for p in points)
        max_y = max(p[1] for p in points)
        f.write(struct.pack('<4d', min_x, min_y, max_x, max_y))
        f.write(struct.pack('<4d', 0.0, 0.0, 0.0, 0.0))

        # Index Record (Big Endian)
        f.write(struct.pack('>i', 50))  # Offset (after 100-byte header)
        f.write(struct.pack('>i', record_content_length // 2))  # Content Length

def write_dbf_file(points, dbf_file):
    num_records = len(points)
    field_length = 10  # طول فیلد ID
    record_length = 1 + field_length  # 1 بایت برای فلگ حذف + طول فیلد
    num_fields = 1  # فقط یک فیلد (ID)
    header_length = 32 + (num_fields * 32) + 1  # هدر پایه + تعریف فیلد + پایان‌دهنده
    file_length = header_length + (num_records * record_length) + 1  # هدر + رکوردها + پایان فایل

    with open(dbf_file, 'wb') as f:
        # File Header (Little Endian)
        current_date = datetime.now()
        f.write(struct.pack('<B', 3))  # Version (dBase III)
        f.write(struct.pack('<B', current_date.year - 1900))  # Year
        f.write(struct.pack('<B', current_date.month))  # Month
        f.write(struct.pack('<B', current_date.day))  # Day
        f.write(struct.pack('<i', num_records))  # Number of Records
        f.write(struct.pack('<H', header_length))  # Header Length
        f.write(struct.pack('<H', record_length))  # Record Length
        f.write(b'\x00' * 20)  # Reserved

        # Field Descriptor
        f.write(b'ID        ')  # Field Name (10 chars)
        f.write(b'C')  # Field Type (Character)
        f.write(struct.pack('<i', 0))  # Field Data Address (Reserved)
        f.write(struct.pack('<B', field_length))  # Field Length
        f.write(struct.pack('<B', 0))  # Decimal Count
        f.write(b'\x00' * 14)  # Reserved
        f.write(b'\x0D')  # Header Terminator

        # Records
        for i in range(num_records):
            f.write(b'\x20')  # Record not deleted
            id_str = f"{i+1:<{field_length}}".encode('ascii')  # ID with padding
            f.write(id_str)

        f.write(b'\x1A')  # End of File
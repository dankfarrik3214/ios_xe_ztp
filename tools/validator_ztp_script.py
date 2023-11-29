import os
import hashlib

def file_exists(filename):
    """Check if a file exists in the current directory."""
    return os.path.isfile(filename)

def calculate_md5(filename):
    """Calculate the MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def extract_software_mappings():
    """Extracts the software_mappings dictionary from ztp.py."""
    with open('ztp.py', 'r') as file:
        lines = file.readlines()

    start = end = None
    brace_count = 0
    for i, line in enumerate(lines):
        if 'software_mappings = {' in line:
            start = i
            brace_count += line.count('{') - line.count('}')
        elif start is not None:
            brace_count += line.count('{') - line.count('}')
            if brace_count == 0:
                end = i
                break

    if start is not None and end is not None:
        mappings_code = ''.join(lines[start:end + 1])
        exec(mappings_code, globals())
        return globals().get('software_mappings', {})
    else:
        return {}

def validate_software_files(software_mappings):
    """Validate software files based on the mappings."""
    for model, details in software_mappings.items():
        software_image = details.get('software_image')
        expected_md5 = details.get('software_md5_checksum')

        print(f"*** Model {model}: Firmware File - {software_image} ***")
        if software_image and expected_md5:
            if file_exists(software_image):
                actual_md5 = calculate_md5(software_image)
                if actual_md5 == expected_md5:
                    print(f"--- {software_image}: VALID MD5 checksum.")
                else:
                    print(f"--- {software_image}: INVALID MD5 checksum.")
            else:
                print(f"--- {software_image} is NOT present in the directory.")

if __name__ == "__main__":
    print("### Validator ZTP Script ###")
    print("This script checks for the presence of 'ztp.py', extracts 'software_mappings',")
    print("and validates the existence and MD5 checksums of the software files.\n")

    if file_exists("ztp.py"):
        print("*** ztp.py file found. ***")
        software_mappings = extract_software_mappings()
        if software_mappings:
            print("*** software_mappings extracted successfully. ***")
            validate_software_files(software_mappings)
        else:
            print("*** software_mappings not found in ztp.py. ***")
    else:
        print("*** ztp.py file is not present in the directory. ***")

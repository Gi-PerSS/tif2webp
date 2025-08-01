# TIFF to WebP Lossless Converter

This script is designed for batch conversion of TIFF files to WebP Lossless format with maximum compression. It provides a flexible way to process TIFF files in various directories, offering detailed statistics and logging for monitoring the conversion process.

## Features

- **Flexible Input Options**:
  - Process the current directory for subdirectories containing TIFF files.
  - Process a specified directory.
  - Process directories listed in a provided TXT file.

- **Conversion Logic**:
  - Creates a corresponding `_webp` directory for each processed directory.
  - Converts only TIFF files that haven't been converted yet (unless forced).
  - Uses a single-threaded approach to minimize HDD load.

- **Statistics and Logging**:
  - Tracks processing time for each file.
  - Calculates compression ratios.
  - Provides overall space savings.
  - Generates a detailed report upon completion.

## Usage

### Command Line Arguments

- **No Arguments**: Scans the current directory for subdirectories containing TIFF files and processes them.
- **Directory Path**: Processes the specified directory.
- **TXT File Path**: Processes directories listed in the provided TXT file.

### Example Commands

- **Process Current Directory**:
  ```bash
  python tiff2webp.py
  ```

- **Process Specific Directory**:
  ```bash
  python tiff2webp.py /path/to/directory
  ```

- **Process Directories from TXT File**:
  ```bash
  python tiff2webp.py directories.txt
  ```

### Output

- Converted WebP files are saved in a new directory with the suffix `_webp`.
- A log file `tiff2webp.log` is created to record the conversion process.
- A summary report is displayed upon completion, including total files processed, time taken, average compression ratio, and space saved.

## Requirements

- Python 3.x
- `cwebp` command-line tool (part of the WebP suite)
- `tqdm` library for progress bars

### Installation

1. **Install WebP Tools**:
   - On Ubuntu: `sudo apt-get install webp`
   - On macOS: `brew install webp`
   - On Windows: Download from [Google's WebP page](https://developers.google.com/speed/webp/download)

2. **Install Python Dependencies**:
   ```bash
   pip install tqdm
   ```

## Logging

- Logs are written to `tiff2webp.log` in the current directory.
- Console output provides real-time updates on the conversion process.

## Error Handling

- The script handles errors gracefully, logging any issues encountered during conversion.
- If a critical error occurs, the script will exit with an error message.

## License

This script is provided under the MIT License. See the LICENSE file for details.

---

[Читать на русском](README_RU.markdown)
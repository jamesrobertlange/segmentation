# URL Analysis Tool

This tool analyzes URLs from CSV files, providing insights, segmentation suggestions, and ngram analysis.

## Installation

1. Ensure you have Python 3.7+ installed on your system.

2. Clone this repository:
   ```
   git clone https://github.com/yourusername/url-analysis-tool.git
   cd url-analysis-tool
   ```

3. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

4. Install the required packages:
   ```
   pip install flask pandas aiohttp tqdm
   ```

## Setup

1. Ensure you have the following folder structure in your project directory:
   ```
   url-analysis-tool/
   ├── app.py
   ├── templates/
   │   └── upload.html
   ├── uploads/
   └── results/
   ```

2. If the `uploads` and `results` folders don't exist, create them:
   ```
   mkdir uploads results
   ```

## Running the Application

1. From the project directory, run:
   ```
   python app.py
   ```

2. Open a web browser and go to `http://localhost:5000`.

## Usage

1. Enter a client name in the provided field.

2. Either upload a new CSV file or select a previously uploaded file from the dropdown.

3. Click "Analyze URLs" to start the analysis.

4. Once complete, you can view the results on the page and download JSON, TXT, and CSV files with the full analysis.

5. The generated files will be saved in the `results` folder.

## CSV File Format

The tool looks for any column containing "URL" in its name (case-insensitive). Examples of valid column names include:
- URL
- URLs
- Full URL
- Canonical URL

Ensure your CSV file has at least one column with "URL" in its name.

If your CSV file uses a custom separator, you can specify it in the first line of the file like this:
```
sep=,
Full URL
https://www.example.com/
...
```

## Features

- Flexible URL column detection
- Support for custom CSV separators
- Ngram analysis of URL patterns
- Segmentation suggestions
- Insights on domain, subdomain, and path distributions
- Export results in JSON, TXT, and CSV formats
- Local file management (upload and select previously uploaded files)

## Troubleshooting

If you encounter any issues:

1. Ensure all required packages are installed.
2. Check that the `templates`, `uploads`, and `results` folders exist and have the correct permissions.
3. Verify that your CSV file contains a column with "URL" in its name.
4. Check the Flask application logs for any error messages.
5. Ensure you have write permissions for both the `uploads` and `results` folders.
6. If download links don't work, verify that the files are being created in the `results` folder after analysis.

For further assistance, please open an issue on the GitHub repository.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
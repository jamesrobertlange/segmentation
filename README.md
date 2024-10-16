# URL Analysis Tool

This tool analyzes URLs from CSV files, providing insights, segmentation suggestions, and ngram analysis.

## Features

- Flexible URL column detection
- Support for custom CSV separators
- Ngram analysis of URL patterns
- Segmentation suggestions
- Insights on domain, subdomain, and path distributions
- Export results in TXT and CSV formats
- Local file management (upload and select previously uploaded files)
- Botify segmentation rule generation
- Markdown export of all segmentation recommendations

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
   pip install -r requirements.txt
   ```

## Setup

1. The project structure should look like this:
   ```
   url-analysis-tool/
   ├── app.py
   ├── botify_segmentation.py
   ├── gunicorn.conf.py
   ├── requirements.txt
   ├── .gitignore
   ├── README.md
   ├── templates/
   │   └── upload.html
   ├── uploads/
   │   └── sample-pagelist.csv
   └── results/
   ```

2. The `uploads` and `results` folders should be created automatically when you run the application. If not, create them manually:
   ```
   mkdir uploads results
   ```

## Running the Application

1. For development, run:
   ```
   python app.py
   ```

2. For production, use Gunicorn:
   ```
   gunicorn app:app -c gunicorn.conf.py
   ```

3. Open a web browser and go to `http://localhost:10000` (or the appropriate port if you've changed it).

## Usage

1. Enter a client name in the provided field.

2. Either upload a new CSV file or select a previously uploaded file from the dropdown.

3. Click "Analyze URLs" to start the analysis.

4. Once complete, you can view the results on the page and download TXT and CSV files with the full analysis.

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

## File Management

- The tool allows you to upload new CSV files and select from previously uploaded files.
- All uploaded files are stored in the `uploads` folder.
- Analysis results are stored in the `results` folder.
- You can delete all uploaded and result files using the "Delete All Files" button on the web interface.

## Troubleshooting

If you encounter any issues:

1. Ensure all required packages are installed (`pip install -r requirements.txt`).
2. Check that the `templates`, `uploads`, and `results` folders exist and have the correct permissions.
3. Verify that your CSV file contains a column with "URL" in its name.
4. Check the application logs for any error messages.
5. Ensure you have write permissions for both the `uploads` and `results` folders.
6. If download links don't work, verify that the files are being created in the `results` folder after analysis.

For further assistance, please open an issue on the GitHub repository.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Deployment

This project is configured for deployment on Render.com. See the `render.yaml` file for deployment settings.
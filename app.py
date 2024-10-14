import re
from collections import Counter
from urllib.parse import urlparse, parse_qs
import traceback
import json
from datetime import datetime
import asyncio
import aiohttp
import pandas as pd
import csv
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import os
from tqdm import tqdm

app = Flask(__name__)

# Increase maximum file size to 20MB
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB in bytes

UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'csv'}
CHUNK_SIZE = 10000  # Process URLs in chunks of 10000

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def find_url_columns(df):
    url_columns = [col for col in df.columns if 'url' in col.lower()]
    app.logger.info(f"Columns in DataFrame: {df.columns.tolist()}")
    app.logger.info(f"URL columns found: {url_columns}")
    return url_columns

def read_csv_with_custom_header(file_path):
    with open(file_path, 'r') as f:
        first_line = f.readline().strip()
        if first_line.startswith('sep='):
            separator = first_line[-1]
            df = pd.read_csv(file_path, sep=separator, skiprows=[0])
        else:
            df = pd.read_csv(file_path)
    return df

async def analyze_url(url, session):
    try:
        parsed_url = urlparse(url)
        
        results = {
            'subdomain': '',
            'domain': '',
            'path': parsed_url.path,
            'path_without_params': parsed_url.path.split(';')[0].split('?')[0],
            'query_params': list(parse_qs(parsed_url.query).keys()),
            'file_extension': '',
            'segments': [],
            'protocol': parsed_url.scheme,
            'path_length': len(parsed_url.path.split('/')),
            'query_param_count': len(parse_qs(parsed_url.query))
        }
        
        domain_parts = parsed_url.netloc.split('.')
        if len(domain_parts) > 2:
            results['subdomain'] = '.'.join(domain_parts[:-2])
        results['domain'] = '.'.join(domain_parts[-2:])
        
        if '.' in parsed_url.path.split('/')[-1]:
            results['file_extension'] = parsed_url.path.split('/')[-1].split('.')[-1]
        
        results['segments'] = [f"level_{i+1}:{seg}" for i, seg in enumerate(parsed_url.path.split('/')) if seg]
        
        return results
    except Exception as e:
        print(f"Error processing URL {url}: {str(e)}")
        return None

async def analyze_urls_chunk(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [analyze_url(url, session) for url in urls]
        results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]

def merge_results(chunk_results):
    merged = {
        'subdomains': Counter(),
        'domains': Counter(),
        'paths': Counter(),
        'paths_without_params': Counter(),
        'query_params': Counter(),
        'file_extensions': Counter(),
        'segments': Counter(),
        'protocol': Counter(),
        'path_length': Counter(),
        'query_param_count': Counter(),
    }
    
    for result in chunk_results:
        merged['subdomains'][result['subdomain']] += 1
        merged['domains'][result['domain']] += 1
        merged['paths'][result['path']] += 1
        merged['paths_without_params'][result['path_without_params']] += 1
        merged['query_params'].update(result['query_params'])
        if result['file_extension']:
            merged['file_extensions'][result['file_extension']] += 1
        merged['segments'].update(result['segments'])
        merged['protocol'][result['protocol']] += 1
        merged['path_length'][result['path_length']] += 1
        merged['query_param_count'][result['query_param_count']] += 1
    
    return merged

def generate_insights(analysis_results):
    insights = []
    
    total_urls = sum(analysis_results['domains'].values())
    insights.append(f"Total URLs analyzed: {total_urls}")
    insights.append(f"Most common protocol: {analysis_results['protocol'].most_common(1)[0][0]}")
    
    if analysis_results['subdomains']:
        insights.append(f"Most common subdomain: {analysis_results['subdomains'].most_common(1)[0][0]}")
    
    insights.append(f"Most common domain: {analysis_results['domains'].most_common(1)[0][0]}")
    insights.append(f"Most common path: {analysis_results['paths'].most_common(1)[0][0]}")
    insights.append(f"Most common path without parameters: {analysis_results['paths_without_params'].most_common(1)[0][0]}")
    
    if analysis_results['query_params']:
        insights.append(f"Most common query parameter: {analysis_results['query_params'].most_common(1)[0][0]}")
    
    if analysis_results['file_extensions']:
        insights.append(f"Most common file extension: {analysis_results['file_extensions'].most_common(1)[0][0]}")
    
    avg_path_depth = sum(k*v for k,v in analysis_results['path_length'].items()) / total_urls
    insights.append(f"Average path depth: {avg_path_depth:.2f}")
    
    avg_query_params = sum(k*v for k,v in analysis_results['query_param_count'].items()) / total_urls
    insights.append(f"Average number of query parameters: {avg_query_params:.2f}")
    
    segmentation_suggestions = []
    for segment, count in analysis_results['segments'].most_common(10):
        level, value = segment.split(':')
        segmentation_suggestions.append(f"@{value}\npath */{value}/*")
    
    return insights, segmentation_suggestions

def ngram_analysis(urls, n=2, min_count=5):
    ngrams = Counter()
    for url in urls:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        for i in range(len(path_parts) - n + 1):
            ngram = '/'.join(path_parts[i:i+n])
            ngrams[ngram] += 1
    
    return {ngram: count for ngram, count in ngrams.items() if count >= min_count}

async def main(urls):
    try:
        chunk_results = []
        for i in tqdm(range(0, len(urls), CHUNK_SIZE), desc="Processing URL chunks"):
            chunk = urls[i:i+CHUNK_SIZE]
            chunk_result = await analyze_urls_chunk(chunk)
            chunk_results.extend(chunk_result)
        
        analysis_results = merge_results(chunk_results)
        insights, segmentation_suggestions = generate_insights(analysis_results)
        
        ngrams = ngram_analysis(urls)
        
        return {
            'analysis': analysis_results,
            'insights': insights,
            'segmentation_suggestions': segmentation_suggestions,
            'ngrams': ngrams
        }
    except Exception as e:
        return {
            'error': str(e),
            'traceback': traceback.format_exc()
        }

def export_results(result, format, client_name):
    date_str = datetime.now().strftime("%Y%m%d")
    filename_base = f"url_analysis_{client_name}_{date_str}"
    
    if format == 'json':
        filename = f"{filename_base}.json"
        file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        with open(file_path, 'w') as f:
            json.dump(result, f, indent=2, default=lambda x: list(x.items()) if isinstance(x, Counter) else x)
    elif format == 'txt':
        filename = f"{filename_base}.txt"
        file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        with open(file_path, 'w') as f:
            f.write("URL Analysis Results\n\n")
            f.write("Insights:\n")
            for insight in result['insights']:
                f.write(f"- {insight}\n")
            f.write("\nSegmentation Suggestions:\n")
            for suggestion in result['segmentation_suggestions']:
                f.write(f"{suggestion}\n\n")
            f.write("Full Analysis:\n")
            for key, value in result['analysis'].items():
                f.write(f"{key}:\n")
                for item, count in value.most_common(20):  # Limit to top 20 for readability
                    f.write(f"  {item}: {count}\n")
                f.write("\n")
            f.write("Ngram Analysis:\n")
            for ngram, count in sorted(result['ngrams'].items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {ngram}: {count}\n")
    elif format == 'csv':
        filename = f"{filename_base}.csv"
        file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        df = pd.DataFrame([(k, v) for k, v in result['ngrams'].items()], columns=['Ngram', 'Count'])
        df = df.sort_values('Count', ascending=False)
        df.to_csv(file_path, index=False)
    
    return filename

def find_url_columns(df):
    return [col for col in df.columns if 'url' in col.lower()]

@app.route('/list_files', methods=['GET'])
def list_files():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)]
    return jsonify(files)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        try:
            client_name = request.form.get('client_name', 'unnamed_client')
            
            file_path = None
            
            if 'file' in request.files and request.files['file'].filename != '':
                file = request.files['file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
            elif 'selected_file' in request.form and request.form['selected_file'] != '':
                filename = request.form['selected_file']
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            if not file_path:
                return jsonify({'error': 'No file selected or uploaded'}), 400
            
            # Process the file
            df = read_csv_with_custom_header(file_path)
            app.logger.info(f"CSV file read successfully. Shape: {df.shape}")
            url_columns = find_url_columns(df)
            
            if not url_columns:
                return jsonify({'error': f"No column containing 'URL' found in the CSV file. Columns found: {', '.join(df.columns.tolist())}"}), 400
            
            # If multiple URL columns are found, use the first one
            url_column = url_columns[0]
            urls = df[url_column].dropna().tolist()
            
            # Run the analysis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(main(urls))
            
            # Export results
            json_file = export_results(results, 'json', client_name)
            txt_file = export_results(results, 'txt', client_name)
            csv_file = export_results(results, 'csv', client_name)
            
            return jsonify({
                'message': 'Analysis complete',
                'json_file': json_file,
                'txt_file': txt_file,
                'csv_file': csv_file,
                'insights': results['insights'],
                'segmentation_suggestions': results['segmentation_suggestions'][:5],
                'top_ngrams': dict(sorted(results['ngrams'].items(), key=lambda x: x[1], reverse=True)[:10]),
                'url_column_used': url_column
            })
        except Exception as e:
            app.logger.error(f"Error processing file: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({'error': f"Error processing file: {str(e)}"}), 500
    
    return render_template('upload.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['RESULTS_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
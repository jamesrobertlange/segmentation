import re
from collections import Counter
from urllib.parse import urlparse, parse_qs
import traceback
from datetime import datetime
import asyncio
import aiohttp
import pandas as pd
import csv
import json
from flask import Flask, request, jsonify, render_template, send_file, Response
from werkzeug.utils import secure_filename
import os
import shutil
import logging
import io
from botify_segmentation import generate_botify_segmentation, export_botify_segmentation, export_segmentation_markdown

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'csv'}
CHUNK_SIZE = 1000  # Process URLs in chunks of 1000

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def find_url_columns(df):
    url_columns = [col for col in df.columns if 'url' in col.lower()]
    if not url_columns:
        app.logger.warning(f"No URL column found. Columns in DataFrame: {df.columns.tolist()}")
    return url_columns

def process_csv_chunk(chunk):
    url_columns = find_url_columns(chunk)
    if not url_columns:
        return None
    url_column = url_columns[0]
    urls = chunk[url_column].dropna().tolist()
    return urls

def read_csv_with_custom_header(file_path):
    with open(file_path, 'r') as f:
        first_line = f.readline().strip()
        if first_line.startswith('sep='):
            separator = first_line[-1]
            df = pd.read_csv(file_path, sep=separator, skiprows=[0])
        else:
            df = pd.read_csv(file_path)
    return df

def stream_csv(file_path):
    df = read_csv_with_custom_header(file_path)
    for i in range(0, len(df), CHUNK_SIZE):
        yield df[i:i+CHUNK_SIZE]

async def analyze_url(url):
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
        
        if parsed_url.netloc:
            domain_parts = parsed_url.netloc.split('.')
            if len(domain_parts) > 2:
                results['subdomain'] = '.'.join(domain_parts[:-2])
            results['domain'] = '.'.join(domain_parts[-2:])
        
        if '.' in parsed_url.path.split('/')[-1]:
            results['file_extension'] = parsed_url.path.split('/')[-1].split('.')[-1]
        
        results['segments'] = [f"{seg}" for seg in parsed_url.path.split('/') if seg]
        
        return results
    except Exception as e:
        app.logger.error(f"Error processing URL {url}: {str(e)}")
        return None

async def analyze_urls_chunk(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [analyze_url(url) for url in urls]
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
    insights.append(f"Total URLs analyzed: {total_urls:,}")
    
    if analysis_results['protocol']:
        insights.append(f"Most common protocol: {analysis_results['protocol'].most_common(1)[0][0]}")
    
    if analysis_results['subdomains']:
        insights.append(f"Most common subdomain: {analysis_results['subdomains'].most_common(1)[0][0]}")
    
    if analysis_results['domains']:
        insights.append(f"Most common domain: {analysis_results['domains'].most_common(1)[0][0]}")
    
    if analysis_results['paths']:
        insights.append(f"Most common path: {analysis_results['paths'].most_common(1)[0][0]}")
    
    if analysis_results['paths_without_params']:
        insights.append(f"Most common path without parameters: {analysis_results['paths_without_params'].most_common(1)[0][0]}")
    
    if analysis_results['query_params']:
        insights.append(f"Most common query parameter: {analysis_results['query_params'].most_common(1)[0][0]}")
    
    if analysis_results['file_extensions']:
        insights.append(f"Most common file extension: {analysis_results['file_extensions'].most_common(1)[0][0]}")
    
    if total_urls > 0:
        avg_path_depth = sum(k*v for k,v in analysis_results['path_length'].items()) / total_urls
        insights.append(f"Average path depth: {avg_path_depth:.2f}")
        
        avg_query_params = sum(k*v for k,v in analysis_results['query_param_count'].items()) / total_urls
        insights.append(f"Average number of query parameters: {avg_query_params:.2f}")
    
    return insights

def ngram_analysis(urls, n=2, min_count=5):
    ngrams = Counter()
    for url in urls:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        for i in range(len(path_parts) - n + 1):
            ngram = '/'.join(path_parts[i:i+n])
            ngrams[ngram] += 1
    
    return {ngram: count for ngram, count in ngrams.items() if count >= min_count}

async def process_urls(urls):
    chunk_results = []
    for i in range(0, len(urls), CHUNK_SIZE):
        chunk = urls[i:i+CHUNK_SIZE]
        chunk_result = await analyze_urls_chunk(chunk)
        chunk_results.extend(chunk_result)
        
        # Yield control to allow other tasks to run
        await asyncio.sleep(0)
    
    analysis_results = merge_results(chunk_results)
    insights = generate_insights(analysis_results)
    ngrams = ngram_analysis(urls)
    
    return {
        'analysis': analysis_results,
        'insights': insights,
        'ngrams': ngrams
    }

def process_urls_sync(urls):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(process_urls(urls))
    loop.close()
    
    # Generate Botify segmentation
    botify_segmentation, all_segments = generate_botify_segmentation(urls)
    results['botify_segmentation'] = botify_segmentation
    results['all_segments'] = all_segments
    
    return results

def export_results(result, format, client_name):
    date_str = datetime.now().strftime("%Y%m%d")
    filename_base = f"url_analysis_{client_name}_{date_str}"
    
    if format == 'txt':
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
            f.write("Botify Segmentation Rules:\n")
            f.write(result['botify_segmentation'])
            f.write("\n\nFull Analysis:\n")
            for key, value in result['analysis'].items():
                f.write(f"{key}:\n")
                for item, count in value.most_common(20):  # Limit to top 20 for readability
                    f.write(f"  {item}: {count:,}\n")
                f.write("\n")
            f.write("Ngram Analysis:\n")
            for ngram, count in sorted(result['ngrams'].items(), key=lambda x: x[1], reverse=True)[:20]:
                f.write(f"  {ngram}: {count:,}\n")
    elif format == 'csv':
        filename = f"{filename_base}.csv"
        file_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        df = pd.DataFrame([(k, v) for k, v in result['ngrams'].items()], columns=['Ngram', 'Count'])
        df = df.sort_values('Count', ascending=False)
        df.to_csv(file_path, index=False)
    
    # Export Botify segmentation rules
    botify_filename = f"botify_segmentation_{client_name}_{date_str}.txt"
    botify_file_path = os.path.join(app.config['RESULTS_FOLDER'], botify_filename)
    export_botify_segmentation(result['botify_segmentation'], botify_file_path)
    
    # Export all segmentation recommendations as markdown
    markdown_filename = f"all_segmentation_{client_name}_{date_str}.md"
    markdown_file_path = os.path.join(app.config['RESULTS_FOLDER'], markdown_filename)
    export_segmentation_markdown(result['all_segments'], markdown_file_path)
    
    return filename, botify_filename, markdown_filename

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        try:
            start_time = datetime.now()
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
            
            all_urls = []
            for chunk in stream_csv(file_path):
                urls = process_csv_chunk(chunk)
                if urls:
                    all_urls.extend(urls)
            
            results = process_urls_sync(all_urls)
            
            insights = results['insights']
            segmentation_suggestions = [f"@{segment}\npath */{segment}/*" for segment, _ in results['analysis']['segments'].most_common(10)]
            
            results['segmentation_suggestions'] = segmentation_suggestions
            
            txt_file, botify_file, markdown_file = export_results(results, 'txt', client_name)
            csv_file, _, _ = export_results(results, 'csv', client_name)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            response_data = {
                'message': 'Analysis complete',
                'txt_file': txt_file,
                'csv_file': csv_file,
                'botify_file': botify_file,
                'markdown_file': markdown_file,
                'insights': insights,
                'segmentation_suggestions': segmentation_suggestions,
                'top_ngrams': {k: f"{v:,}" for k, v in sorted(results['ngrams'].items(), key=lambda x: x[1], reverse=True)[:10]},
                'processing_time_seconds': processing_time,
                'file_size_mb': os.path.getsize(file_path) / (1024 * 1024),
                'total_urls_processed': f"{len(all_urls):,}"
            }
            
            return jsonify(response_data)
        
        except Exception as e:
            app.logger.error(f"Error processing file: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({'error': f"Error processing file: {str(e)}"}), 500
    
    return render_template('upload.html')

@app.route('/list_files', methods=['GET'])
def list_files():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)]
    return jsonify(files)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['RESULTS_FOLDER'], filename), as_attachment=True)

@app.route('/delete_files', methods=['POST'])
def delete_files():
    try:
        # Delete all files in the uploads folder except for sample.csv
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename != 'sample-pagelist.csv':
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        # Delete all files in the results folder
        for filename in os.listdir(RESULTS_FOLDER):
            file_path = os.path.join(RESULTS_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        return jsonify({'message': 'All files deleted successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error deleting files: {str(e)}")
        return jsonify({'error': f"Error deleting files: {str(e)}"}), 500

def is_development():
    return not os.environ.get('FLASK_ENV') == 'production'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
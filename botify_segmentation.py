from collections import Counter
from urllib.parse import urlparse
import os

def generate_botify_segmentation(urls, top_n=10):
    segments = Counter()
    all_segments = []
    
    for url in urls:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        for i, part in enumerate(path_parts, 1):
            segment = f"{part}"
            segments[segment] += 1
            all_segments.append((i, segment))
    
    top_segments = segments.most_common(top_n)
    
    botify_rules = ["[segment:auto_generated]"]
    
    for segment, count in top_segments:
        rule = f"@{segment}\npath */{segment}/*"
        botify_rules.append(rule)
    
    return "\n\n".join(botify_rules), all_segments

def export_botify_segmentation(segmentation_rules, file_path):
    with open(file_path, 'w') as f:
        f.write(segmentation_rules)
    return os.path.basename(file_path)

def export_segmentation_markdown(all_segments, file_path):
    segment_levels = {}
    for level, segment in all_segments:
        if level not in segment_levels:
            segment_levels[level] = set()
        segment_levels[level].add(segment)
    
    with open(file_path, 'w') as f:
        f.write("# Segmentation Recommendations\n\n")
        for level in sorted(segment_levels.keys()):
            f.write(f"## Level {level}\n\n")
            for segment in sorted(segment_levels[level]):
                f.write(f"```\n@{segment}\npath */{segment}/*\n```\n\n")
    
    return os.path.basename(file_path)
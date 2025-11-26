import json

def extract_posts(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)

    sessions_posts = []
    for item in data.get('matching_elements', []):
        if item.get('ame') == 'sessions':
            title = item.get('article', {}).get('title')
            if not title:
                # Use first line of text or first 100 chars as fallback title
                text = item.get('text', '')
                title = text.split('\n')[0][:100] if text else "No Title"
            
            sessions_posts.append({
                'title': title,
                'url': item.get('url'),
                'text': item.get('text', '')
            })
    
    return sessions_posts

if __name__ == "__main__":
    posts = extract_posts('/Users/stephen/dev/apify-incoming-linkedin/marked_posts_20251125_232257.json')
    print(json.dumps(posts, indent=2))

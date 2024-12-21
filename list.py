from bs4 import BeautifulSoup
import requests

def scrape_episodes(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    episodes = []
    
    # Find all span elements containing episode links
    spans = soup.find_all('span')
    
    for span in spans:
        # Find anchor tag within span
        link = span.find('a')
        if link and 'episode' in link.get('href', ''):
            episode = {
                'title': link.text.strip(),
                'url': link.get('href', '')
            }
            episodes.append(episode)
    
    return episodes

def get_episode_list(url):
    """Get list of episode URLs from series page"""
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        episodes = []
        # Find all span elements containing episode links
        spans = soup.find_all('span')
        
        for span in spans:
            link = span.find('a')
            if link and 'episode' in link.get('href', ''):
                episodes.append({
                    'title': link.text.strip(),
                    'url': link.get('href', '')
                })
        
        return episodes[::-1]  # Reverse to get oldest first
    except Exception as e:
        print(f"Error scraping episodes: {e}")
        return []

def main():
    with open('list.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    episodes = scrape_episodes(html_content)
    
    # Print results
    for ep in episodes:
        print(f"Title: {ep['title']}")
        print(f"URL: {ep['url']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
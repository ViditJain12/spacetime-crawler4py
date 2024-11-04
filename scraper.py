import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
from collections import defaultdict, Counter
from utils import get_logger

visited_urls = set()
subdomain_count = defaultdict(int)
word_counter = Counter()
longest_page_url = None
longest_page_word_count = 0
logger = get_logger("CRAWLER")

STOP_WORDS = {"ourselves", "hers", "between", "yourself", "but", "again", "there", "about", "once", "during", "out", "very", "having", 
        "with", "they", "own", "an", "be", "some", "for", "do", "its", "yours", "such", "into", "of", "most", "itself", "other", "off", "is", 
        "s", "am", "or", "who", "as", "from", "him", "each", "the", "themselves", "until", "below", "are", "we", "these", "your", "his", "through", 
        "don", "nor", "me", "were", "her", "more", "himself", "this", "down", "should", "our", "their", "while", "above", "both", "up", "to", 
        "ours", "had", "she", "all", "no", "when", "at", "any", "before", "them", "same", "and", "been", "have", "in", "will", "on", "does", 
        "yourselves",  "then", "that", "because", "what", "over", "why", "so", "can", "did", "not", "now", "under", "he", "you", "herself", "has", 
        "just", "where", "too", "only", "myself", "which", "those", "i", "after", "few", "whom", "t", "being", "if", "theirs", "my", "against", 
        "a", "by", "doing", "it", "how", "further", "was", "here", "than", "d", "b"}

def scraper(url, resp):
    links = extract_next_links(url, resp)
    report()
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    
    if resp.status != 200 or not resp.raw_response.content.strip():
        return []

    soup = BeautifulSoup(resp.raw_response.content, "html.parser")
    links = set()  # Use a set to avoid duplicates
    
    # Process text and links
    text = soup.get_text()
    word_count = count_words(text)
    if word_count > 50:  # Threshold to skip low-information pages
        process_longest_page(url, word_count)
        process_common_words(text)
        
        for link in soup.find_all("a", href=True):
            full_url = urljoin(url, link['href'])
            defragged_url = urldefrag(full_url)[0]
            if defragged_url not in visited_urls and is_valid(defragged_url):
                links.add(defragged_url)
                process_subdomain(defragged_url)

    return list(links)  # Convert set to list for return

def count_words(text):
    """
    Counts the words in the given text content.
    """
    words = re.findall(r'[0-9a-z]+', text.lower())  # Tokenize and lowercase
    return len(words)

def process_longest_page(url, word_count):
    """
    Updates information about the longest page found.
    """
    global longest_page_url, longest_page_word_count
    if word_count > longest_page_word_count:
        longest_page_word_count = word_count
        longest_page_url = url

def process_common_words(text):
    """
    Processes the text of a page to count occurrences of each word,
    ignoring stop words.
    """

    words = re.findall(r'[0-9a-z]+', text.lower())
    filtered_words = [word for word in words if word not in STOP_WORDS and not (word.isdigit() and len(word) == 1) and len(word) >= 3]
    word_counter.update(filtered_words)

def process_subdomain(url):
    """
    Updates the count of unique pages for each subdomain in uci.edu.
    """
    global visited_urls, subdomain_count
    parsed_url = urlparse(url)
    if parsed_url.netloc.endswith("uci.edu"):
        subdomain = parsed_url.netloc
        if url not in visited_urls:
            visited_urls.add(url)
            subdomain_count[subdomain] += 1

# Certain parts of this function has been taken from "https://github.com/Alvi09/Information-Retrieval-Web-Crawler/blob/main/Assignment%202%3A%20Web%20Crawler/scraper.py"
def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:        
        #If the URL is over 150 characters, it returns False to avoid very long URLs that might be dynamically generated or contain excessive query parameters.
        if len(url) > 150:
            return False

        parsed = urlparse(url)

        if parsed.scheme not in set(["http", "https"]):
            return False

        # Common query parameters, if any appear in the query part of the URL, the function returns False.
        query_bl = {"replytocom", "share", "page_id", "afg", "ical", "action"}
        if any([(query in parsed.query) for query in query_bl]):
            return False
        
        # Block certain patterns often found in calendar or listing URLs
        path_bl = {"/events/", "/day/", "/week/", "/month/", "/list/", "?filter"}
        if any([(path in url.lower()) for path in path_bl]):
            return False

        # Checks if valid domain
        allowed_domains = {"ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu", "today.uci.edu/department/information_computer_sciences/"}
        if not any(domain in parsed.netloc for domain in allowed_domains):
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def report():
    sorted_subdomains = sorted(subdomain_count.items())
    logger.info(f"Longest Page: {longest_page_url} with {longest_page_word_count} words")
    logger.info(f"Top 50 Words: {word_counter.most_common(50)}")
    logger.info(f"Subdomains: {sorted_subdomains}, number of subdomains: {len(sorted_subdomains)}")
    logger.info(f"Number of unique pages: {len(visited_urls)}")
from bs4 import BeautifulSoup
import requests
from flask import Flask, render_template
from flask_caching import Cache
from datetime import datetime
import re

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


def calculate_dense_rank(sorted_names, total_counts):
    """
    Measure dense rank for each name.

    This function maps each name to its dense rank, where dense rank is
    measured by most arrests with counts as a tiebreaker

    Args:
        sorted_names: A List of tuple pairs with name and times arrested
        total_counts: A dictionary mapping names to total counts

    Returns:
        A dict mapping each name to its dense rank.
    """
    ranks = {}
    last_count = None
    last_total_count = None  # Keep track of the last total count for tie-breaking
    current_rank = 0
    entries_processed = 0  # To handle true indexing for dense rank

    for name, count in sorted_names:
        # Increment entries processed count
        entries_processed += 1

        # Check both the count and the total_count to determine rank increment
        current_total_count = total_counts.get(name, 0)
        if count != last_count or current_total_count != last_total_count:
            current_rank = entries_processed
            last_count = count
            last_total_count = current_total_count

        ranks[name] = current_rank
    return ranks


def extract_name(text):
    """
    Extracts the name from a string.

    This function separates the name from the counts (if any)

    Args:
        text:   A string which may or may not include the counts

    Returns:
        A string of just the name
    """
    # Define delimiters
    delimiters = [" :", ":", " -", "- "]  # Prioritize " - " over ":"
    for delimiter in delimiters:
        if delimiter in text:
            name, _ = text.split(delimiter, 1)
            return name.strip()
    return text.strip()  # Return the whole text if no delimiter is found


@app.route('/')
@cache.cached(timeout=600)  # Cache this view for 10 minutes
def leaderboard():
    """
    Wrangles the data and communicates it to the html file.

    This function uses the previous functions in order to scrape and wrangle
    the data into a readable format that can be placed on the leaderboard

    Returns:
        none
    """

    # Set up the iterator, URL, date and dictionaries
    i = 0
    max_search = 5
    names_dict = {}
    image_links = {}
    total_counts = {}
    url = "https://brownsvillepd.blogspot.com/"
    today_date = datetime.now().strftime("%Y-%m-%d")
    earliest_date = datetime.now().strftime("%Y-%m-%d")

    # Search each page
    while i < max_search:
        i += 1
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')
        blog_posts = soup.select_one("#Blog1 > div.blog-posts.hfeed")

        # Extract the farthest possible date from the page
        if i > max_search - 2:
            for x in list(range(10)):
                date_tag = soup.select_one(f'#Blog1 > div.blog-posts.hfeed > div:nth-child({x}) > h2 > span')
                if not date_tag:
                    break
                else:
                    current_date = datetime.strptime(date_tag.text.strip(), '%A, %B %d, %Y')
                    if current_date < earliest_date:
                        earliest_date = current_date

        felony_misdemeanor_types = {
            "state jail felony": 1,
            "class a misdemeanor": 1,
            "class b misdemeanor": 1,
            "class c misdemeanor": 1,
            "3rd degree felony": 1,
            "2nd degree felony": 1,
            "1st degree felony": 1
        }

        # Find all posts, then process each one individually
        posts = soup.find_all(lambda tag: tag.name == 'div' and tag.get('id') and tag['id'].startswith('post-body-'))
        for post in posts:
            name_tag = post.select_one('p:nth-child(1) > span > b')
            if name_tag:
                name = name_tag.text.strip().lower()
                name = extract_name(name).title()
                if name not in total_counts:
                    total_counts[name] = 0

                if name in names_dict:
                    names_dict[name] += 1
                else:
                    names_dict[name] = 1

                # Use the specific ID of the post to build the image selector
                image_tag = post.select_one('div.separator > a > img')
                if image_tag:
                    image_links[name] = image_tag['src']
                # Iterate through possible charge descriptions
                for p_index in range(2, 7):  # Adjust range as necessary
                    charge_tag = post.select_one(f'p:nth-child({p_index}) > span > b')
                    if charge_tag:
                        charge_text = charge_tag.text.lower()
                        # Check for specific counts
                        counts_found = re.search(r'(\d+) counts', charge_text)
                        if counts_found:
                            count_sum = int(counts_found.group(1))
                            total_counts[name] += count_sum
                        else:
                            total_counts[name] += 1

        # Attempt to find the next link
        next_link = soup.find('a', id='Blog1_blog-pager-older-link')
        if next_link:
            url = next_link['href']
        else:
            break

    # Sort names by frequency
    sorted_names = sorted(names_dict.items(), key=lambda item: (item[1], total_counts.get(item[0], 0)), reverse=True)
    top_ten = sorted_names[:10]

    # fix the ranks
    ranked_names = calculate_dense_rank(sorted_names, total_counts)

    # Prepare data for the template
    top_ten_data = [(name, count, ranked_names.get(name, ''), total_counts.get(name, 0), image_links.get(name, '')) for
                    name, count in top_ten]

    return render_template('blogspot.html', top_ten=top_ten_data, earliest_date=earliest_date, todays_date=today_date)


if __name__ == '__main__':
    app.run(debug=True, port=4999)

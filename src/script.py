from bs4 import BeautifulSoup
import requests
from flask import Flask, render_template
from flask_caching import Cache
from datetime import datetime
import re
import random

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Found in counts
counts_keywords = {"disorderly", "conduct", "class", "c", "misdemeanor", "public", "intoxication", "traffic",
                   "violation", "assault", "(", ")", "a", "(fv)", "robbery", "2nd", "1st", "3rd", "degree",
                   "felony", "of", "state", "jail", "engaging", "in", "organized", "criminal", "activity",
                   "motor", "organized", "criminal", "mischief", "resisting", "theft", "transportation",
                   "marijuana", "possession", "burglary", "conviction", "convictions", "previous", "arrest",
                   "controlled", "subStance", "pg", "3"}

# a list of all charges and names
full_games_list = []


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

    # This function will be converted to a scraper and saver, will be queued for use by the other functions.

    # Set up the iterator, URL, date and dictionaries
    i = 0
    max_search = 1
    total_arrests = {}
    image_links = {}
    total_counts = {}
    full_games_size = 0
    url = "https://brownsvillepd.blogspot.com/"
    today_date = datetime.now().strftime("%Y-%m-%d")
    earliest_date = datetime.now().strftime("%Y-%m-%d")

    # Search each page
    while i < max_search:
        i += 1
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')

        # Extract the farthest possible date from the page
        if i > max_search - 2:
            for x in list(range(1, 50)):
                date_tag = soup.select_one(f'#Blog1 > div.blog-posts.hfeed > div:nth-child({x}) > h2 > span')
                if not date_tag:
                    break
                else:
                    current_date = datetime.strptime(date_tag.text, '%A, %B %d, %Y').strftime('%Y-%m-%d')
                    if current_date < earliest_date:
                        earliest_date = current_date

        # Find all posts, then process each one individually
        posts = soup.find_all(lambda tag: tag.name == 'div' and tag.get('id') and tag['id'].startswith('post-body-'))
        for post in posts:
            name_tag = post.select_one('p:nth-child(1) > span > b')
            if name_tag:
                name = name_tag.text.strip().lower()
                name = extract_name(name).title()
                if name not in total_counts:
                    total_counts[name] = 0

                if name in total_arrests:
                    total_arrests[name] += 1
                else:
                    total_arrests[name] = 1

                # Use the specific ID of the post to build the image selector
                image_tag = post.select_one('div.separator > a > img')
                if image_tag:
                    image_links[name] = image_tag['src']
                # Iterate through possible charge descriptions
                charges = []
                for p_index in range(2, 7):  # Adjust range as necessary
                    charge_tag = post.select_one(f'p:nth-child({p_index}) > span > b')
                    if charge_tag:
                        charge_text = charge_tag.text.lower()
                        charges.append(charge_text)
                        # Check for specific counts
                        counts_found = re.search(r'(\d+) counts', charge_text)
                        if counts_found:
                            count_sum = int(counts_found.group(1))
                            total_counts[name] += count_sum
                        else:
                            total_counts[name] += 1
                if image_tag and name_tag:
                    full_games_list.append([name, image_tag['src'], charges])

        # Attempt to find the next link
        next_link = soup.find('a', id='Blog1_blog-pager-older-link')
        if next_link:
            url = next_link['href']
        else:
            break

    # Sort names by counts & charges, then assign a rank # to the top 10
    sorted_names = sorted(total_arrests.items(), key=lambda item: (item[1], total_counts.get(item[0], 0)), reverse=True)
    top_ten = sorted_names[:10]
    ranked_names = calculate_dense_rank(sorted_names, total_counts)

    # Prepare data for the template
    top_ten_data = [(name, count, ranked_names.get(name, ''), total_counts.get(name, 0), image_links.get(name, '')) for
                    name, count in top_ten]
    print(full_games_list)
    return render_template('blogspot.html', top_ten=top_ten_data, earliest_date=earliest_date, todays_date=today_date)

@app.route('/api/random-game-data')
def random_batch():
    output = [random.choice(full_games_list), random.choice(full_games_list), random.choice(full_games_list)]
    print(output)
    return output


@app.route('/todays-game')
def todays_game():
    # generate 3 random numbers from 1 to the size and pick those. (logic will need to be moved to an event listener)

    return render_template('todays-game.html', full_games_list=full_games_list, todays_game_data=random_batch());


@app.route('/random-game')
def random_game():
    # Logic to generate a random game from historical data
    # You might want to randomize the selection of criminals and crimes here
    return render_template('random-game.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=4999)

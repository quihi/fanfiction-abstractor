"""parser.py downloads, parses, and creates messages from FFN and AO3 pages."""

from bs4 import BeautifulSoup
import cloudscraper
import re
import requests

HEADERS = {"User-Agent": "fanfiction-abstractor-bot"}
FFN_GENRES = set()
# create scraper to bypass cloudflare, always download desktop pages
options = {"desktop": True, "browser": "firefox", "platform": "linux"}
scraper = cloudscraper.create_scraper(browser=options)

# generate set of possible FFN genres
genres_list = ["Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy",
               "Friendship", "General", "Horror", "Humor", "Hurt/Comfort",
               "Mystery", "Parody", "Poetry", "Romance", "Sci-Fi", "Spiritual",
               "Supernatural", "Suspense", "Tragedy", "Western"]
for g1 in genres_list:
    for g2 in genres_list:
        FFN_GENRES.add(g1 + "/" + g2)
    FFN_GENRES.add(g1)

# dictionary of emoji to numbers, for parsing reacts
REACTS = {"1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣": 5,
          "6️⃣": 6, "7️⃣": 7, "8️⃣": 8, "9️⃣": 9, "🔟": 10}


def generate_ao3_work_summary(link):
    """Generate the summary of an AO3 work.

    link should be a link to an AO3 fic
    Returns the message with the fic info, or else a blank string
    """
    r = requests.get(link, headers=HEADERS)
    if r.status_code != requests.codes.ok:
        return ""
    if r.url == "https://archiveofourown.org/users/login?restricted=true":
        return ""
    soup = BeautifulSoup(r.text, "lxml")

    preface = soup.find(class_="preface group")
    title = preface.h2.string.strip()
    author = preface.h3.string
    if author is None:
        author = ", ".join(map(lambda x: x.string, preface.h3.find_all("a")))
    else:
        author = author.strip()

    summary = preface.find(class_="summary module")
    if summary:
        summary = format_html(summary)

    tags = soup.find(class_="work meta group")
    rating = tags.find("dd", class_="rating tags")
    category = tags.find("dd", class_="category tags")
    fandoms = tags.find("dd", class_="fandom tags")
    warnings = tags.find("dd", class_="warning tags")
    relationships = tags.find("dd", class_="relationship tags")
    characters = tags.find("dd", class_="character tags")
    freeform = tags.find("dd", class_="freeform tags")
    series = tags.find("dd", class_="series")
    words = tags.find("dd", class_="words").string
    chapters = tags.find("dd", class_="chapters").string
    kudos = tags.find("dd", class_="kudos")
    if kudos:
        kudos = kudos.string
    else:
        kudos = 0
    updated = tags.find("dd", class_="status")
    if updated:
        updated = updated.string
    else:
        updated = tags.find("dd", class_="published").string

    output = "**{}** (<{}>) by **{}**\n".format(title, link, author)
    if series:
        series = series.find_all(class_="position")[:5]
        for s in series:
            s_name = s.text.split()
            s = "**Part {}** of the **{}** series (<https://archiveofourown.org{}>)\n"\
                .format(s_name[1], " ".join(s_name[4:-1]), s.a["href"])
            output += s
    if fandoms:
        fandoms = list(map(lambda x: x.string, fandoms.find_all("a")))
        if len(fandoms) > 5:
            fandoms = ", ".join(fandoms[:5]) + "…"
        else:
            fandoms = ", ".join(fandoms)
    output += "**Fandoms:** {}\n".format(fandoms)
    if category:
        rating = ", ".join(map(lambda x: x.string, rating.find_all("a")))
        category = ", ".join(map(lambda x: x.string, category.find_all("a")))
        output += "**Rating:** {}          **Category:** {}\n".format(
            rating, category)
    else:
        rating = ", ".join(map(lambda x: x.string, rating.find_all("a")))
        output += "**Rating:** {}\n".format(rating)
    warnings = ", ".join(map(lambda x: x.string, warnings.find_all("a")))
    output += "**Warnings:** {}\n".format(warnings)
    if relationships:
        relationships = list(map(
            lambda x: x.string, relationships.find_all("a")))
        if len(relationships) > 2:
            relationships = ", ".join(relationships[:2]) + "…"
        else:
            relationships = ", ".join(relationships)
        output += "**Relationships:** {}\n".format(relationships)
    if characters:
        characters = list(map(lambda x: x.string, characters.find_all("a")))
        if len(characters) > 3:
            characters = ", ".join(characters[:3]) + "…"
        else:
            characters = ", ".join(characters)
        output += "**Characters:** {}\n".format(characters)
    if freeform:
        freeform = list(map(lambda x: x.string, freeform.find_all("a")))
        if len(freeform) > 5:
            freeform = ", ".join(freeform[:5]) + "…"
        else:
            freeform = ", ".join(freeform)
        output += "**Tags:** {}\n".format(freeform)
    if summary:
        output += "**Summary:** {}\n".format(summary)
    output += "**Words:** {} **Chapters:** {} **Kudos:** {} **Updated:** {}".format(
        words, chapters, kudos, updated)

    return output


def generate_ao3_series_summary(link):
    """Generate the summary of an AO3 work.

    link should be a link to an AO3 series
    Returns the message with the series info, or else a blank string
    """
    r = requests.get(link, headers=HEADERS)
    if r.status_code != requests.codes.ok:
        return ""
    if r.url == "https://archiveofourown.org/users/login?restricted=true":
        return ""
    soup = BeautifulSoup(r.text, "lxml")

    title = soup.find("h2", class_="heading").string.strip()
    preface = soup.find(class_="series meta group")
    next_field = preface.dd
    author = ", ".join(map(lambda x: x.string, next_field.find_all("a")))
    next_field = next_field.find_next_sibling("dd")
    begun = next_field.string
    next_field = next_field.find_next_sibling("dd")
    updated = next_field.string
    next_field = next_field.find_next_sibling("dt")
    if next_field.string == "Description:":
        next_field = next_field.find_next_sibling("dd")
        description = format_html(next_field)
        next_field = next_field.find_next_sibling("dt")
    else:
        description = None
    if next_field.string == "Notes:":
        next_field = next_field.find_next_sibling("dd")
        notes = format_html(next_field)
        next_field = next_field.find_next_sibling("dt")
    else:
        notes = None
    next_field = next_field.find_next_sibling("dd").dl.dd
    words = next_field.string
    next_field = next_field.find_next_sibling("dd")
    works = next_field.string
    complete = next_field.find_next_sibling("dd").string

    # format output
    output = "**{}** (<{}>) by **{}**\n".format(title, link, author)
    if description:
        output += "**Description:** {}\n".format(description)
    if notes:
        output += "**Notes:** {}\n".format(notes)
    output += "**Begun:** {} **Updated:** {}\n".format(begun, updated)
    output += "**Words:** {} **Works:** {} **Complete:** {}\n\n".format(
        words, works, complete)

    # Find titles and links to first few works
    works = soup.find_all(class_=re.compile("work blurb group work-.*"))
    for i in range(min(3, len(works))):
        title = works[i].h4.a
        output += "{}. __{}__: <https://archiveofourown.org{}>\n".format(
            i + 1, title.string, title["href"])
    if len(works) == 4:
        title = works[3].h4.a
        output += "4. __{}__: <https://archiveofourown.org{}>".format(
            title.string, title["href"])
    elif len(works) > 4:
        output += "        [and {} more works]".format(len(works) - 3)
    else:
        output = output[:-1]

    return output


def identify_work_in_ao3_series(link, number):
    """Do something.

    link should be a link to a series, number is an int for which fic
    Returns the link to that number fic in the series, or else None
    """
    r = requests.get(link, headers=HEADERS)
    if r.status_code != requests.codes.ok:
        return None
    if r.url == "https://archiveofourown.org/users/login?restricted=true":
        return None
    soup = BeautifulSoup(r.text, "lxml")

    preface = soup.find(class_="series meta group")
    next_field = preface.find("dl", class_="stats").dd
    next_field = next_field.find_next_sibling("dd")
    works = int(next_field.string)
    if works < number:
        return None

    # Find link to correct work
    works = soup.find_all(class_=re.compile("work blurb group work-.*"))
    fic = works[number - 1]
    return fic.h4.a["href"]


def generate_ffn_work_summary(link):
    """Do something.

    link should be a link to an FFN fic
    Returns the message with the fic info, or else a blank string
    """
    r = scraper.get(link)
    if r.status_code != requests.codes.ok:
        return None
    soup = BeautifulSoup(r.text, "lxml")

    # collect story data from page
    fandoms = soup.find(id="pre_story_links").span
    if fandoms.img:
        # is crossover
        fandoms = fandoms.a.string.replace(" Crossover", "").replace(" +", ",")
    else:
        # is not crossover
        fandoms = fandoms.a.find_next_sibling("a").string

    profile = soup.find(id="profile_top")
    title = profile.b.string
    next_field = profile.a
    author = next_field.string
    next_field = next_field.find_next_sibling("div")
    summary = next_field.string
    next_field = next_field.find_next_sibling("span")

    stats = next_field.text.split(" - ")
    rating = stats[0].replace("Rated: Fiction ", "")
    # next field varies.  have fun identifying it!
    # order: rating, language, genre, characters, chapters, words,
    #     reviews, favs, follows, updated, published, status, id
    genre = None
    characters = None
    updated = None
    index = 2
    field = stats[index]
    if field in FFN_GENRES:
        genre = field
        index += 1; field = stats[index]
    if "Chapters: " not in field and "Words: " not in field:
        characters = field
        index += 1; field = stats[index]
    if "Chapters: " in field:
        chapters = field.replace("Chapters: ", "")
        index += 1; field = stats[index]
    else:
        chapters = 1
    if "Words: " in field:
        words = field.replace("Words: ", "")
        index += 1; field = stats[index]
    else:
        print("Error: This is not the words field")
    if "Reviews: " in field:
        reviews = field.replace("Reviews: ", "")
        index += 1; field = stats[index]
    else:
        reviews = 0
    if "Favs: " in field:
        favs = field.replace("Favs: ", "")
        index += 1; field = stats[index]
    else:
        favs = 0
    if "Follows: " in field:
        follows = field.replace("Follows: ", "")
        index += 1; field = stats[index]
    else:
        follows = 0
    if "Updated: " in field:
        updated = field.replace("Updated: ", "")
        index += 1; field = stats[index]
    if "Published: " in field:
        if updated is None:
            updated = field.replace("Published: ", "")
        index += 1; field = stats[index]
    else:
        print("Error: This is not the published date field")
    if "Status: Complete" in field:
        complete = True
    else:
        complete = False

    output = "**{}** (<{}>) by **{}**\n".format(title, link, author)
    output += "**Fandoms:** {}\n".format(fandoms)
    if genre:
        output += "**Rating:** {}          **Genre:** {}\n".format(rating, genre)
    else:
        output += "**Rating:** {}\n".format(rating)
    if characters:
        output += "**Characters:** {}\n".format(characters)
    if summary:
        output += "**Summary:** {}\n".format(summary)
    # output += "**Reviews:** {} **Favs:** {} **Follows:** {}\n".format(\
    #     reviews, favs, follows)
    if complete:
        chapters = str(chapters) + "/" + str(chapters)
    else:
        chapters = str(chapters) + "/?"
    output += "**Words:** {} **Chapters:** {} **Favs:** {} **Updated:** {}".format(
        words, chapters, favs, updated)

    return output


def format_html(field):
    """Format an HTML segment for discord markdown.

    field should be a note or summary from AO3.
    """
    brs = field.find_all("br")
    for br in brs:
        br.replace_with("\n")
    ols = field.find_all("ol")
    for ol in ols:
        ol.name = "p"
    uls = field.find_all("ul")
    for ul in uls:
        ul.name = "p"
    for li in field.find_all("li"):
        li.string = "- {}".format(li.text.strip())
        li.unwrap()
    field = field.blockquote.find_all("p")
    result = list(map(lambda x: x.text.strip(), field))
    result = "\n\n".join(result)
    if len(result) > 250:
        result = result[:250] + "…"
    return result

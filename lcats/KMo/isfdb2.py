import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

DATE_RE = re.compile(r"\b(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?\b")

def convert_author (last_name_first: str) -> str:
    names = last_name_first.split(", ")
    first_name_first = names[1] + " " + names[0]

    return first_name_first

def _best_date_from_text(text: str) -> str | None:
    """
    Extract the first date-like token from text, preferring YYYY-MM-DD, then YYYY-MM, then YYYY.
    """
    if not text:
        return None
    m = DATE_RE.search(text)
    if not m:
        return None
    y, mth, d = m.group(1), m.group(2), m.group(3)
    if y and mth and d:
        return f"{y}-{mth}-{d}"
    if y and mth:
        return f"{y}-{mth}"
    return y if y else None

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()

def _match_title_author(row_title: str, row_author: str, q_title: str, q_author: str) -> bool:
    # ISFDB often lists multiple authors like "A / B". Do loose matching.
    rt, ra = _clean(row_title), _clean(row_author)
    print("****** " + str(rt) + " ----- " + str(ra) + "::::" + _clean(q_title))

    return _clean(q_title) == rt and _clean(q_author) == ra

def _find_title_link_from_search(html: str, title: str, author: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 2:
            continue
        result_title = tds[3].get_text(" ", strip=True)
        result_author = tds[4].get_text(" ", strip=True)
        
        if _match_title_author(result_title, result_author, title, convert_author(author)):
            a = tds[3].find("a")
            print("--- " + str(a.get("href", "")))

            if a and "/cgi-bin/title.cgi" in a.get("href", ""):
                return a["href"]
    return None

def _extract_date_from_title_page(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    # Typical pattern: a table with labels like "Date", sometimes "First Published"
    for row in soup.find_all("tr"):
        label_td = row.find("td", class_="label")
        val_td = row.find("td", class_="value")
        if not label_td or not val_td:
            continue
        label = label_td.get_text(" ", strip=True).lower()
        if any(k in label for k in ["date", "first published", "first publication"]):
            dt = _best_date_from_text(val_td.get_text(" ", strip=True))
            if dt:
                return dt

    # Some pages show a "Synopsis" or "Notes" block with a date embedded—scan as a fallback.
    text_blobs = soup.get_text(" ", strip=True)
    return _best_date_from_text(text_blobs)

def _extract_earliest_date_from_publications(html: str) -> str | None:
    """
    On a title page, there’s often a 'Publications' or 'Publication Record' section linking to pub pages (pub.cgi).
    We try two strategies:
      1) Parse dates shown inline in the title page’s publications table (if present).
      2) Visit each pub.cgi link and read its 'Publication Date' (rate-limited).
    We return the earliest date we can find.
    """
    soup = BeautifulSoup(html, "html.parser")
    candidate_dates: list[str] = []

    # 1) Inline dates in a publications table
    for table in soup.find_all("table"):
        # Heuristic: if the table has any link to pub.cgi, it’s a publications table.
        if not table.find("a", href=re.compile(r"/cgi-bin/pub\.cgi")):
            continue
        # Grab any cell text that looks like a date.
        for td in table.find_all("td"):
            dt = _best_date_from_text(td.get_text(" ", strip=True))
            if dt:
                candidate_dates.append(dt)

    # 2) Visit pub.cgi pages for more reliable 'Publication Date'
    pub_links = []
    for a in soup.find_all("a", href=re.compile(r"^/cgi-bin/pub\.cgi\?id=\d+")):
        url = "https://www.isfdb.org" + a["href"]
        pub_links.append(url)

    # Be kind to the site; small sleep between requests
    session = requests.Session()
    for url in pub_links[:15]:  # safety cap
        try:
            time.sleep(0.4)
            r = session.get(url, timeout=15)
            if r.status_code != 200:
                continue
            psoup = BeautifulSoup(r.text, "html.parser")

            # Look for a row labeled 'Publication Date' or 'Date'
            found = None
            for row in psoup.find_all("tr"):
                label_td = row.find("td", class_="label")
                val_td = row.find("td", class_="value")
                if not label_td or not val_td:
                    continue
                label = label_td.get_text(" ", strip=True).lower()
                if any(k in label for k in ["publication date", "pubdate", "date"]):
                    found = _best_date_from_text(val_td.get_text(" ", strip=True))
                    if found:
                        break
            if not found:
                # Fallback: scan entire page text
                found = _best_date_from_text(psoup.get_text(" ", strip=True))
            if found:
                candidate_dates.append(found)
        except requests.RequestException:
            continue

    if not candidate_dates:
        return None

    # Normalize for comparison: pad YYYY -> YYYY-12-31, YYYY-MM -> YYYY-MM-28 (approx),
    # but we should sort by earliest—so use start-of-period padding (YYYY-01-01, YYYY-MM-01)
    def sortable_key(dt: str) -> tuple[int, int, int]:
        m = DATE_RE.fullmatch(dt)
        if not m:
            # try partial matches at start
            m = DATE_RE.match(dt)
        if not m:
            return (9999, 12, 31)
        y = int(m.group(1))
        mo = int(m.group(2) or 1)
        day = int(m.group(3) or 1)
        return (y, mo, day)

    candidate_dates.sort(key=sortable_key)
    return candidate_dates[0]

def get_isfdb_date(title: str, author: str) -> str:
    """
    Return the earliest available publication date for (title, author) from ISFDB.

    Behavior:
      - Searches Title records; picks the matching Title page.
      - Tries to read a 'Date'/'First Published' on the Title page.
      - If missing/ambiguous, inspects Publication records and returns the earliest date found.
      - Date format returned is best-effort: 'YYYY-MM-DD', else 'YYYY-MM', else 'YYYY'.

    Returns:
      A date string as above, or 'Not found' / 'Error: <reason>'.
    """
    try:
        search_url = f"https://www.isfdb.org/cgi-bin/se.cgi?arg={quote_plus(title)}&type=All+Titles"
        print(search_url)
        r = requests.get(search_url, timeout=20)
        if r.status_code != 200:
            return "Error: Could not fetch search page"

        title_url = _find_title_link_from_search(r.text, title, author)
        if not title_url:
            return "Not found"

        rt = requests.get(title_url, timeout=20)
        if rt.status_code != 200:
            return "Error: Could not fetch title page"

        # 1) Title page date
        title_date = _extract_date_from_title_page(rt.text)
        print("-------> " + str(title_date))
        
        # 2) Publications fallback (earliest)
        pubs_earliest = _extract_earliest_date_from_publications(rt.text)

        # Choose earliest of the two if both exist
        if title_date and pubs_earliest:
            def key(d):  # same earliest comparison as above
                m = DATE_RE.match(d)
                y = int(m.group(1))
                mo = int(m.group(2) or 1)
                day = int(m.group(3) or 1)
                return (y, mo, day)
            return title_date if key(title_date) <= key(pubs_earliest) else pubs_earliest

        if title_date:
            return title_date
        if pubs_earliest:
            return pubs_earliest
        return "Not found"

    except requests.RequestException:
        return "Error: Network issue"

# --- Example usage ---
# print(get_isfdb_date("The War of the Worlds", "H. G. Wells"))
# print(get_isfdb_date("Story of Your Life", "Ted Chiang"))

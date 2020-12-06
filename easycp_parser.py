from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import urljoin
from time import sleep

CODEFORCES_REQEST_DELAY = 0.5


def CFProblem(url):

    html = urlopen(url).read().decode("utf-8")
    with open("page.html", 'w', encoding="utf-8") as file:
        file.write(html)

    with open("page.html", 'r', encoding="utf-8") as file:
        html = file.read()

    soup = BeautifulSoup(html, "html.parser").find("div", id="body").find("div", id="pageContent")
    test_blocks = soup.find("div", class_="sample-tests").findAll("div", class_="sample-test")

    result = []

    for test_block in test_blocks:

        inp = None
        for elem in test_block.findChildren("div"):

            if "input" in elem["class"]:
                elem = elem.find("pre")
                for item in elem.find_all("br"):
                    item.replace_with("\n")
                inp = elem.text.strip()

            elif "output" in elem["class"]:
                elem = elem.find("pre")
                for item in elem.find_all("br"):
                    item.replace_with("\n")
                result.append([inp, elem.text.strip()])
                inp = None

    return result


def CFProblemset(url):
    html = urlopen(url).read().decode("utf-8")
    with open("main_page.html", 'w', encoding="utf-8") as file:
        file.write(html)

    with open("main_page.html", 'r', encoding="utf-8") as file:
        html = file.read()

    soup = BeautifulSoup(html, "html.parser").find("div", id="body").find("div", id="pageContent")
    table = soup.find("div", class_="datatable").find("table", class_="problems").findAll("tr")

    sleep(CODEFORCES_REQEST_DELAY)

    result = {}
    for line in table:
        if line.find("td") is None:
            continue

        link = line.find("a")

        result[link.text.strip()] = CFProblem(urljoin(url, link.get("href")))

        sleep(CODEFORCES_REQEST_DELAY)

    return result


# TESTS:
# Parse CF problemset:
# result = CFProblemset("https://codeforces.com/contest/1340")
# print(result)

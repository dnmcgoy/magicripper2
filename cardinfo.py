# Cardinfo.py

import re
import string
#
import symbols

# stupid prefixes used by Gatherer HTML
PREFIX1 = "ctl00_ctl00_ctl00_MainContent_SubContent_SubContentHeader_"
PREFIX2 = "ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_"

# replace high-ASCII characters with their low-ASCII equivalents
characters = [
    # multicharacter exprs first
    ('\xe2\x80\x93', '-'),
    ('\xe2\x80\x94', '--'),
    ('\xe2\x80\x98', "'"),
    ('\xe2\x80\x99', "'"),
    ('\xe2\x80\xa8', " "),
    ('\xe2\x84\xa2', '(TM)'),

    ('\xc2\xa0', ' '),
    ('\xc2\xa1', '!'),
    ('\xc2\xb2', '2'),  # squared symbol
    ('\xc2\xba', 'o'),  # degree symbol; no equivalent in low ASCII :-/
    ('\xc3\x84', 'A'),
    ('\xc3\x86', 'Ae'),
    ('\xc3\xa1', 'a'),  
    ('\xc3\xa2', 'a'),
    ('\xc3\xa4', 'a'),
    ('\xc3\xa6', 'ae'),
    ('\xc3\xa8', 'e'),
    ('\xc3\xa9', 'e'),
    ('\xc3\xa0', 'a'),
    ('\xc3\xaa', 'e'),
    ('\xc3\xad', 'i'),
    ('\xc3\xb6', 'o'),  # o-umlaut
    ('\xc3\xba', 'u'),
    ('\xc3\xbb', 'u'),
    ('\xc3\xbc', 'u'),
    ('\xc2\xae', '(R)'),
    
    ('\x80', '-'),
    ('\x94', '-'),
    ('\x98', "'"),
    ('\xe2', '-'),

    # HTML entities work as well
    ("&nbsp;", " "),
]

class CardInfoGatherer:

    def __init__(self, soup):
        self.soup = soup

    def name(self):
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"nameRow")
        o = n.find('div', {'class': 'value'})
        return gather_contents(o)

    def manacost(self):
        syms = []
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"manaRow")
        if n is None: return []
        for o in n.findAll('img'):
            sym = o['alt'].lower().strip()
            sym = symbols.translate(sym)
            syms.append(sym)
        return map(str, syms)

    def type(self):
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"typeRow")
        o = n.find('div', {'class': 'value'})
        return gather_contents(o)

    def rules(self):
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"textRow")
        if n is None: return "" # always create a node for rules, even if empty
        parts = [gather_contents(o)
                 for o in n.findAll('div', {'class': 'cardtextbox'})]
        s = string.join(parts, "\n")
        return replace_bogus_mana(s)

    def flavor_text(self):
        # XXX much the same as rules_printed()... refactor
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"FlavorText")
        if n is None: return None
        parts = [gather_contents(o)
                 for o in n.findAll('div', {'class': 'cardtextbox'})]
        return string.join(parts, "\n")

    def rarity(self):
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"rarityRow")
        o = n.find('div', {'class': 'value'})
        rarity = gather_contents(o).lower().strip()
        return symbols.rarities[rarity]

    def number(self):
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"numberRow")
        if n is None: return None # older cards don't have a number
        o = n.find('div', {'class': 'value'})
        return gather_contents(o)

    def artist(self):
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"artistRow")
        o = n.find('div', id=get_card_prefix(self.soup)+"ArtistCredit")
        return gather_contents(o)

    def _power_toughness(self):
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"ptRow")
        if n is None: return None, None
        o = n.find('div', {'class': 'value'})
        s = gather_contents(o)
        parts = s.split('/')
        try:
            return parts[0].strip(), parts[1].strip()
        except IndexError:
            return None, None # does not have valid power/toughness
                              # this happens for Planeswalkers

    def power(self):
        p, t = self._power_toughness()
        return p

    def toughness(self):
        p, t = self._power_toughness()
        return t

    def loyalty(self):
        n = self.soup.find('div', id=get_card_prefix(self.soup)+"ptRow")
        if n is None: return None
        if "Loyalty:" not in gather_contents(n):
            return None # P/T
        o = n.find('div', {'class': 'value'})
        return gather_contents(o)
    
    def flip_multiverseid(self):
        return get_flip_multiverseid(self.soup)

def gather_contents(soupnode):
    """ Gather contents from a BeautifulSoup node, stripping HTML, replacing
        symbols, etc. """

    # replace images with text, e.g. {B}, {TAP}, etc.
    for n in soupnode.findAll('img'):
        symbol = n['alt'].lower().strip()
        our_symbol = symbols.translate(symbol) # may raise KeyError
        n.replaceWith("{" + our_symbol + "}")

    s = string.join([str(x) for x in soupnode.contents], "").strip()
    s = strip_html(s)
    return replace_chars(s)

def replace_chars(s):
    """ Replace high ASCII characters with low ASCII equivalents (sort of)."""
    for before, after in characters:
        s = s.replace(before, after)
    return s

re_html_tag = re.compile("<[^>]+>")

def strip_html(s):
    return re_html_tag.sub("", s)

def get_card_prefix(soupnode):
    actionDetail = soupnode.find("form", id="aspnetForm")['action']
    multiverseid = re.match(r"Details\.aspx\?multiverseid=([0-9]*).*", actionDetail).group(1)
    imageDetail = soupnode.find("img", src=re.compile('Image.ashx.*multiverseid='+multiverseid))
    if imageDetail:
        flipId = re.match(r"ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_ctl([0-9]*)_cardImage", imageDetail['id'])
        if flipId:
            return "ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_ctl" + flipId.group(1) + "_"
        else:
            return PREFIX2
    else:
        return PREFIX2

#FIXME copy pasta.  This can be refactored.
def get_flip_multiverseid(soupnode):
    actionDetail = soupnode.find("form", id="aspnetForm")['action']
    multiverseid = re.match(r"Details\.aspx\?multiverseid=([0-9]*).*", actionDetail).group(1)
    imageDetail = soupnode.find("img", src=re.compile('Image.ashx.*multiverseid='+multiverseid))
    if imageDetail:
        flipId = re.match(r"ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_ctl([0-9]*)_cardImage", imageDetail['id'])
        if flipId:
            if flipId.group(1) == "05":
                flipTagNumber = "06"
            else:
                flipTagNumber = "05"
            imageSrc = soupnode.find("img", id=re.compile("ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_ctl"+ flipTagNumber + "_cardImage"))['src']
            return re.match(r".*multiverseid=([0-9]*).*", imageSrc).group(1)
        else:
            return None
    else:
        return None
    

bogus_mana = [
    ('ooB', '{B}:'),
    ('ooG', '{G}:'),
    ('ooR', '{R}:'),
    ('ooU', '{U}:'),
    ('ooW', '{W}:'),
    ('ooX', '{X}:'),
    ('oocT', '{TAP}:'),
    ('oB', '{B}'),
    ('oG', '{G}'),
    ('oR', '{R}'),
    ('oU', '{U}'),
    ('oW', '{W}'),
    ('oX', '{X}'),
    ('ocT', '{TAP}'),
    ('(r/w)', '{RW}'),  # Figure of Destiny [EVE]
    ('(w/b)', '{WB}'),  # Stillmoon Cavalier [EVE]
    ('(g/w)', '{GW}'),  # Rhys the Redeemed [SHM]
]
re_bogus_mana_number = re.compile("o(\d+)")

def replace_bogus_mana(s):
    """ Some older rules text on Gatherer has bogus mana symbols, e.g. 'oB'
        instead of just 'B' or '{B}'. Let's replace them. This is only
        necessary for rules_printed. """
    for before, after in bogus_mana:
        s = s.replace(before, after)
    s = re_bogus_mana_number.sub("{\\1}", s)
    return s


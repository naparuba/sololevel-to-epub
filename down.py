#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import optparse
import os
import pickle as cPickle
import re
import shutil
import sys
import time
from urllib.request import urlopen

try:
    from bs4 import BeautifulSoup
except ImportError as exp:
    print('ERROR: missing bs4 lib. Launch pip3.exe install bs4')
    sys.exit(2)

try:
    from ebooklib import epub
except ImportError as exp:
    print('ERROR: missing ebooklib lib. Launch pip3.exe install ebooklib')
    sys.exit(2)

# NOTE: ce script est tres brut de fonderie, mais il a le merite de fonctionner
# Pour le faire fonctionner vous aurez besoin de deux repertoires: down et tmp
# * tmp : cache pour les pages
# * down: chache pour le parsing des pages, a besoin d'être --reset en cas de changement rename/pas rename
# Vous aurez aussi besoin de cablibre pour la transformation finale du ficheir epub (sinon
# il passe mal sur les liseuses, en tout cas sur la mienne (kobo h2o)


VERSION = '0.1'

# Ebook convert: to fix DRM things in the generated epub
EPUB_CONVERT = r'C:\Program Files\Calibre2\ebook-convert.exe'

EPUB_TMP_PTH = 'solo_leveling_tmp.epub'


def _get_epub_path(do_rename):
    if do_rename:
        return 'solo_leveling_with_rename.epub'
    else:
        return 'solo_leveling.epub'


# Vérifie que tmp et down existent
if not os.path.exists('tmp'):
    os.mkdir('tmp')
if not os.path.exists('down'):
    os.mkdir('down')

# je ne me souviens plus pourquoi, j'ai du avoir un bug avec une des lib
sys.setrecursionlimit(10000)

## Utilise pour remplacer les noms qui parfois on un affichage different, et faut bien le dire, j'ai un peu
#  de mal avec les noms coreens, j'ai deja confondu JinCeol et Jinwoo dans le passe ^^
names = [
    # jinwoo
    ('Sung Jinwoo', 'Jinwoo'),
    ('Jinwoo Sung', 'Jinwoo'),
    ('Jinwoo', 'Jinwoo'),
    ('Jin-Woo', 'Jinwoo'),
    
    # Cha
    ('Cha Hae', 'Cha'),
    ('Cha Hae-In', 'Cha'),
    
    # Jin
    ('Woo Jin-Cheol', 'Jin'),
    ('Woo Jincheol', 'Jin'),
    ('Woo Jin-Chul', 'Jin'),
    
    # Song
    ('Song Chiyeol', 'Song'),
    ('Song Chi-Yeol', 'Song'),
    
    # Baek
    ('Baek Yun-Ho', 'Baek'),
    ('Baek Yoon-ho', 'Baek'),
    ('Baek Yoonho', 'Baek'),
    
    # Choi
    ('Choi Jong-In', 'Choi'),
    ('Choi JongIn', 'Choi'),
    ('Choi Jong', 'Choi'),
    
    # M.Go
    ('Go Gun-hee', 'M.Go'),
    ('Goh Gun-Hui', 'M.Go'),
    ('Go Gunhee', 'M.Go'),
    ('Go Gunhee', 'Go'),
    ('Gunhee', 'Go'),
    
    # Hwang Dong-Su => Hwang
    ('Hwang Dong-Su', 'Hwang'),
    ('Hwang Dong-soo', 'Hwang'),
    ('Hwang Dongsoo', 'Hwang'),
    
    # Park Heejin => Park
    ('Park Heejin', 'Park'),
    ('Park Hee-jin', 'Park'),
    
    # Baekho => white tiger
    ('Baekho', 'White Tiger'),
    
    # Lee Juhee
    ('Lee Juhee', 'Juhee'),
    
    # Yoo Jinho => Jinho
    ('Yoo Jinho', 'Jinho'),
    ('Yoo Jin-ho', 'Jinho'),
    
    # Ma Dong-wook => Dong
    ('Ma Dong-wook', 'Dong'),
    ('Ma Dong', 'Dong'),
    
    # Min Byunggu => Byung
    ('Min Byunggu', 'Byung'),
    
    # Lim Tae-gyu => Lim
    ('Lim Tae-gyu', 'Lim'),

]

reg_names = []
for (name, dest) in names:
    reg_names.append((re.compile(re.escape(name), re.IGNORECASE), dest))


def rename_names(s):
    # FAKE
    # return s
    orig = s
    for rgx, dest in reg_names:
        # print "TRANSFORM", rgx, dest
        s = rgx.sub(dest, s)
        # print "INFO", s
    # if orig != s:
    #    #print "CHANGED", orig, s
    #    fuck
    return s


# some lines are starting with » and should be changed by «
def _fix_bad_line_characters(s):
    lines = s.splitlines()
    new_lines = []
    for line in lines:
        line = line.replace("> »", ">«").replace(">»", ">«").replace('I’', 'l\'')
        new_lines.append(line)
    return u'\n'.join(new_lines)


def _fix_french_quotes(s):
    """
    Corrige l'ordre des guillemets français ligne par ligne.
    
    Logique:
    On maintient un état "ouvert/fermé" basé sur les guillemets vus jusqu'à présent.
    - Si on est fermé (count_open == count_close) et qu'on voit un », c'est une erreur
    - On cherche alors le « qui suit et on inverse la paire
    """
    lines = s.splitlines()
    new_lines = []
    
    for line in lines:
        if '»' not in line or '«' not in line:
            new_lines.append(line)
            continue
            
        # Extraire tous les guillemets avec leurs positions
        quotes = []
        for i, char in enumerate(line):
            if char in ('«', '»'):
                quotes.append([i, char])  # Liste mutable
        
        if len(quotes) < 2:
            new_lines.append(line)
            continue
        
        chars = list(line)
        i = 0
        
        while i < len(quotes):
            # Compter combien d'ouvrants et fermants on a vus jusqu'ici
            count_open = sum(1 for j in range(i) if quotes[j][1] == '«')
            count_close = sum(1 for j in range(i) if quotes[j][1] == '»')
            
            current_char = quotes[i][1]
            
            # Si on n'est pas dans une citation (count_open == count_close)
            # et qu'on trouve un », c'est une erreur
            if count_open == count_close and current_char == '»':
                # Chercher le « qui suit
                for j in range(i + 1, len(quotes)):
                    if quotes[j][1] == '«':
                        # Inverser cette paire » ... «
                        pos1, pos2 = quotes[i][0], quotes[j][0]
                        chars[pos1] = '«'
                        chars[pos2] = '»'
                        quotes[i][1] = '«'
                        quotes[j][1] = '»'
                        break
                # Continuer après cette correction
            
            i += 1
        
        line = ''.join(chars)
        new_lines.append(line)
    
    return '\n'.join(new_lines)


STATUS_FINISH = 'finish'
STATUS_NOT_FINISH = 'not-finish'
STATUS_DOUBLE = 'double'

not_finish_chapter = None


def _get_chapter_file(chapter_nb):
    pth = 'down/chapter_%04d.txt' % chapter_nb
    return pth


def _do_write_chapter(chapter_nb, lines):
    pth = _get_chapter_file(chapter_nb)
    f = io.open(pth + '.tmp', 'w', encoding="utf-8")
    f.write(u'<html>\n<body>\n<h1>Chapter %s</h1>\n' % chapter_nb)
    
    # Nettoyage du contenu HTML
    content = '\n'.join(lines)
    
    # Correction de l'ordre des guillemets français (ligne par ligne)
    content = _fix_french_quotes(content)
    
    # Suppression d'attributs vides (ex: class="")
    content = re.sub(r"\s+\w+(?:[:\w+]*)?\s*=\s*(\"\"|'')", '', content)
    # Supprimer <p> qui ne contiennent que des espaces ou &nbsp;
    content = re.sub(r'<p[^>]*>\s*(?:&nbsp;|\u00A0|&#160;|&#xa0;|\s)*\s*</p>', '', content, flags=re.I)

    # Remplacer entités et caractère NBSP par un espace
    content = re.sub(r'&nbsp;|&#160;|&#x00A0;|&#xa0;', ' ', content, flags=re.I)
    content = content.replace('\u00A0', ' ')

    # Réduire suites d'espaces/tabs en un seul espace (léger)
    content = re.sub(r'[ \t]{2,}', ' ', content)

    # Collapser plus de 2 lignes vides
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    f.write(content)
    f.write(u'\n</body>\n</html>\n')
    f.close()
    shutil.move(pth + '.tmp', pth)


def get_chapter(url, url_nb, chapter_nb, do_write=True, do_rename=False):
    global not_finish_chapter
    status = STATUS_FINISH
    url = url.strip()
    if len(url) == 0:
        return
    
    half_chapter = False
    if url.startswith('*'):
        half_chapter = True
        url = url.replace('*', '')
    
    # Si on a un chapitre en doublons, qui en fait etait dans le precedent, on a un ! devant son url
    double_chapter = False
    if url.startswith('!'):
        double_chapter = True
        url = url.replace('!', '')
    
    # print " - Chapter %s / %s" % (chapter_nb, url)
    pth = _get_chapter_file(chapter_nb)
    if os.path.exists(pth) and do_write:
        print("   * skip %s" % url)
        return status
    
    # on se permet de sauvegarder le parsing du html, car il est long a calculer ^^
    cache_pth = 'tmp/chapter_%04d.soup' % url_nb
    if os.path.exists(cache_pth):
        with open(cache_pth, 'rb') as f:
            soup = cPickle.loads(f.read())
    else:  # on ne l'a jamais recupere, on le fait et on le parse
        page = urlopen(url)
        soup = BeautifulSoup(page, 'html5lib')
        soup_ser = cPickle.dumps(soup)
        with open(cache_pth, 'wb') as f:  # update du cache
            f.write(soup_ser)
        print("  - saved %s (%s)" % (cache_pth, len(soup_ser)))
    
    # la gros parsing bourin pour trouver no morceaux et modifier leur style
    div = soup.find('div', attrs={'class': 'entry-content'})
    # print "ALL DIV", div.prettify()
    ps = div.find_all(["p", "table", 'hr'], recursive=False)
    # print "Number of p", len(ps)
    
    # We will set div.border around strong
    was_in_strong = False
    
    lines = []
    _max = 0
    total = 0
    for p in ps:
        
        is_table = p.name == 'table'
        
        # on affiche pas les liens facebook et autres dans l epub
        txt = p.getText().strip()
        if 'Twitter' in txt and 'Facebook' in txt:
            print("BOGUS TWITTER", len(txt))
            continue
        # c'est une redite du numero du chapitre, on skip
        if txt.startswith('I Alone Level-up :'):
            continue
        # idem
        if 'Chapitre suivant' in txt:
            continue
        if len(txt) > _max:
            _max = len(txt)
        if not do_write:
            print("LINE:", len(txt), txt.encode('utf8'))
        total += len(txt)
        
        # on tente de voir a quoi correspond la ligne pour mettre le bon style. Pas parfait, mais fait le taf :)
        # note: le style est dans le css
        _class = ''
        if txt.startswith(u'«') or txt.startswith(u'“') or txt.startswith(u'‘') or txt.startswith(u'»') or txt.startswith(u'-') or txt.startswith(
                u'–'):
            _class = 'talk'
        elif txt.startswith(u'[') and txt.endswith(u']'):
            _class = 'strong'
        elif p.find_all('strong', recursive=False):
            _class = 'strong'
        elif is_table:
            _class += ' table'
        elif txt.endswith(u'~'):
            _class = 'onomatope'
        
        # new_line = '<p class="%s">%s</p>' % (_class, txt)
        p['class'] = _class
        
        new_line = str(p)
        
        if do_rename:
            new_line = rename_names(new_line)
        
        new_line = _fix_bad_line_characters(new_line)
        
        if 'strong' in _class:
            if was_in_strong:
                pass  # still strong
            else:
                lines.append('<div class="border">')
                was_in_strong = True
        else:
            if was_in_strong:
                was_in_strong = False
                lines.append('</div>')
        
        lines.append(new_line)
    
    # If the last was strong, close the div
    if was_in_strong:
        was_in_strong = False
        lines.append('</div>')
    
    if not do_write:
        return
    
    if not half_chapter:
        # print '\n'.join(lines)
        
        all_lines = lines
        if not_finish_chapter:
            all_lines = not_finish_chapter[:]
            all_lines.extend(lines)
            not_finish_chapter = None
        _do_write_chapter(chapter_nb, all_lines)
        # If is a double chapter: write a void one
        if double_chapter:
            _do_write_chapter(chapter_nb + 1, u'(ce chapitre était contenu dans le chapitre précédent)')
            status = STATUS_DOUBLE
        
        # print "   * done"
        return status
    else:  # must save it
        not_finish_chapter = lines
        return STATUS_NOT_FINISH


def _get_urls():
    with open('urls.txt', 'r') as f:
        buf = f.read()
        urls = buf.splitlines()
    return urls


def _get_chapters(urls, do_rename):
    print("NB CHAPTERS: %s" % len(urls))
    chapter_nb = 1
    for url_nb, url in enumerate(urls):
        if url.strip():
            print('\r' + ' ' * 80),
            print("\r ** get chapter %s (CHAPTER=%s URL=%s / %s)" % (url, chapter_nb, url_nb, len(urls))),
            sys.stdout.flush()
            status = get_chapter(url, url_nb + 1, chapter_nb, do_rename=do_rename)
            if status == STATUS_FINISH:
                chapter_nb += 1
            elif status == STATUS_DOUBLE:
                chapter_nb += 2
    
    print("Done")


# on a les infos, on cre le epub
def _create_epub(chapter_files):
    book = epub.EpubBook()
    
    # set metadata
    book.set_identifier('solo-leveling')
    book.set_title('Solo Leveling FR')
    book.set_language('fr')
    
    book.add_author('Chu-Gong, trad FR par Wuxia')
    
    with open('style.css', 'r') as style_f:
        style = style_f.read()
    
    default_css = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=style)
    
    book.add_item(default_css)
    
    chapters = []
    for chapter_file in chapter_files:
        if not chapter_file.endswith('.txt'):
            continue
        small_name = chapter_file.replace('.txt', '')
        chapter = epub.EpubHtml(title=small_name, file_name='%s.xhtml' % small_name, lang='fr')
        f = io.open('down/%s' % chapter_file, 'r', encoding='utf-8')
        chapter.content = f.read()
        chapter.add_item(default_css)  # without, no css
        book.add_item(chapter)
        
        chapters.append(chapter)
    
    book.set_cover("cover.jpg", open('cover.jpg', 'rb').read())
    
    # define Table Of Contents
    book.toc = tuple(chapters)
    
    # add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    book.add_item(default_css)
    
    # basic spine
    spine = chapters[:]
    spine.insert(0, 'nav')
    book.spine = spine
    
    # write to the file
    pth = EPUB_TMP_PTH
    epub.write_epub(pth, book, {})
    print("File is saved:", pth)


if __name__ == '__main__':
    parser = optparse.OptionParser("%prog ", version="%prog: " + VERSION,
                                   description='This tool is used to take trad from https://wuxialnscantrad.wordpress.com and make a epub from it')
    parser.add_option('--reset', action='store_true', dest='reset', default=False, help="Reset cache")
    parser.add_option('--change-names', action='store_true', default=True, dest='change_names', help="Change names to uniform ones.")
    opts, args = parser.parse_args()
    
    urls = _get_urls()
    
    print("Launching:")
    print("  - reset: %s" % opts.reset)
    print("  - change names: %s" % opts.change_names)
    
    if opts.reset:
        files = os.listdir('down')
        for p in files:
            os.unlink(os.path.join('down', p))
    
    _get_chapters(urls, opts.change_names)
    
    chapter_files = os.listdir('down')
    chapter_files.sort()
    
    _create_epub(chapter_files)
    
    tmp_pth = EPUB_TMP_PTH
    
    # Par contre il est gros, donc soumis au DRM si j'ai bien compris (pas clair), donc on demande a calibre
    # de nous le repackager, il fait ce qu'il faut et vire le DRM, en tout cas sinon ma liseuse kobo n'en veux pas
    epub_path = _get_epub_path(opts.change_names)
    cmd = '"%s"  %s   %s --disable-font-rescaling --cover cover.jpg' % (EPUB_CONVERT, EPUB_TMP_PTH, epub_path)
    print("Executing: %s" % cmd)
    
    before = time.time()
    os.system(cmd)
    print("Final transformation in %.1fs" % (time.time() - before))
    print('COUCOU Wuxia ^^')

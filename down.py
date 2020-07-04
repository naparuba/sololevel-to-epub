#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import shutil
from bs4 import BeautifulSoup
from urllib2 import urlopen
import io
import cPickle
import re

sys.setrecursionlimit(10000)

names = [
    # jinwoo
    ('Sung Jinwoo', 'Panda'),
    ('Jinwoo Sung', 'Panda'),
    ('Jinwoo', 'Panda'),
    ('Jin-Woo', 'Panda'),
    
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


def get_chapter(url, chapter_nb, do_write=True):
    url = url.strip()
    if len(url) == 0:
        return
    print
    " - Chapter %s / %s" % (chapter_nb, url)
    pth = 'down/chapter_%04d.txt' % chapter_nb
    if os.path.exists(pth) and do_write:
        print
        "   * skip %s" % url
        return
    
    cache_pth = 'tmp/chapter_%04d.soup' % chapter_nb
    if os.path.exists(cache_pth):
        with open(cache_pth, 'rb') as f:
            
            soup = cPickle.loads(f.read())
    else:
        page = urlopen(url)
        soup = BeautifulSoup(page, 'html5lib')
        soup_ser = cPickle.dumps(soup)
        with open(cache_pth, 'wb') as f:
            f.write(soup_ser)
        print
        "  - saved %s (%s)" % (cache_pth, len(soup_ser))
    
    div = soup.find('div', attrs={'class': 'entry-content'})
    # print "ALL DIV", div.prettify()
    ps = div.find_all(["p", "table"], recursive=False)
    # print "Number of p", len(ps)
    
    # We will set div.border around strong
    was_in_strong = False
    
    lines = []
    _max = 0
    total = 0
    for p in ps:
        # print "P", p , p.name
        is_table = p.name == 'table'
        # print str(p), dir(p)
        txt = p.getText().strip()
        # if len(line) > 5000:
        #    print "BOGUS LINE"
        #    continue
        if 'Twitter' in txt and 'Facebook' in txt:
            print
            "BOGUS TWITTER", len(txt)
            continue
        if txt.startswith('I Alone Level-up :'):
            continue
        if len(txt) > _max:
            _max = len(txt)
        if not do_write:
            print
            "LINE:", len(txt), txt.encode('utf8')
        total += len(txt)
        
        _class = ''
        if txt.startswith(u'«') or txt.startswith(u'“') or txt.startswith(u'‘') or txt.startswith(u'»') or txt.startswith(u'-') or txt.startswith(u'–'):
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
        new_line = unicode(p)
        
        new_line = rename_names(new_line)
        
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
    
    # print '\n'.join(lines)
    if do_write:
        print
        "TOTOL", total, _max
        f = io.open(pth + '.tmp', 'w', encoding="utf-8")
        f.write(u'<html><body><h1>Chapter %s</h1>\n' % chapter_nb)
        f.write(''.join(lines))
        f.write(u'</body></html>\n')
        f.close()
        shutil.move(pth + '.tmp', pth)
    print
    "   * done"


urls = []
with open('urls.txt', 'r') as f:
    buf = f.read()
    urls = buf.splitlines()

# print urls
# url = 'https://wuxialnscantrad.wordpress.com/2019/04/15/i-alone-level-up-chapitre-1-le-chasseur-de-rang-e/'
# url = 'https://wuxialnscantrad.wordpress.com/2019/04/17/i-alone-level-up-chapitre-4/ '
# url = 'https://wuxialnscantrad.wordpress.com/2019/04/22/i-alone-level-up-chapitre-15/'
# url = 'https://wuxialnscantrad.wordpress.com/2019/04/19/i-alone-level-up-chapitre-8-2/'
# get_chapter(url, 15, do_write=False)
# sys.exit(0)

print
"NB CHAPTERS: %s" % len(urls)
for chapter_nb, url in enumerate(urls):
    if url.strip():
        print
        " ** get chapter %s" % url
        get_chapter(url, chapter_nb + 1)

chapter_files = os.listdir('down')
print
"Chapter files", chapter_files

chapter_files.sort()

# for chapter_file in chapter_files:
#    if not chapter_file.endswith('.txt'):
#        print "SKIP", chapter_file
#        continue
#    print "Chapter", chapter_file


# bla

from ebooklib import epub

book = epub.EpubBook()

# set metadata
book.set_identifier('idsolo-leveling-1')
book.set_title('Solo Leveling 1-210')
book.set_language('fr')

book.add_author('Author Nap')

with open('style.css', 'r') as style_f:
    style = style_f.read()  # 'body { font-family: Times, Times New Roman, serif; }'

# print "STYLE", style

default_css = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=style)

book.add_item(default_css)

chapters = []
for chapter_file in chapter_files:
    if not chapter_file.endswith('.txt'):
        print
        "SKIP", chapter_file
        continue
    print
    "Chapter", chapter_file
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
epub.write_epub('solo_leveling.epub', book, {})

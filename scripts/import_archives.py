#!/usr/bin/env python3
"""One-time import of locally preserved VISPO articles; requires beautifulsoup4.
Run from any directory. Does not retrieve remote files or alter common navigation.
"""
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse,unquote,urljoin
from bs4 import BeautifulSoup,Comment
import hashlib,html,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent.parent/'site-replicas/source/vispo'
REPORT={'source':'site-replicas/source/vispo','import_date':'2026-10-08','articles':[],'missing_media':[],'unmapped_links':[],'skipped':[],'category_redirects':[]}
ASSETS=ROOT/'assets'; (ROOT/'docs').mkdir(exist_ok=True)
base=BeautifulSoup((ROOT/'news.html').read_text(),'html.parser')
header=str(base.header);nav=str(base.select_one('#mobile-nav'));footer=str(base.footer)
article_sources=defaultdict(list)
for p in (SOURCE/'archives').rglob('*.html'):
 rel=p.relative_to(SOURCE).as_posix();m=re.fullmatch(r'archives/(\d+)(?:/index)?\.html',rel)
 if m: article_sources[m[1]].append(p)
ids=set(article_sources)
legacy=['renewal','ordermade','vispo-pilates']
allowed={'p','div','section','article','span','h2','h3','h4','h5','h6','br','hr','strong','b','em','i','u','s','ul','ol','li','dl','dt','dd','table','thead','tbody','tfoot','tr','td','th','figure','figcaption','img','a','blockquote','time','sup','sub'}
def media(url,article):
 u=urlparse(urljoin('https://vispo-fit.com/',url));path=unquote(u.path).lstrip('/')
 if u.hostname not in ('vispo-fit.com','www.vispo-fit.com'):
  REPORT['missing_media'].append({'article':article,'source':url,'reason':'external media not copied'});return None
 p=SOURCE/path
 if not p.is_file():
  REPORT['missing_media'].append({'article':article,'source':path,'reason':'not present in saved copy'});return None
 ext=p.suffix.lower()
 if ext not in {'.jpg','.jpeg','.png','.gif','.webp','.pdf'}:
  REPORT['missing_media'].append({'article':article,'source':path,'reason':'unsupported type'});return None
 name='archive-'+hashlib.sha256(p.read_bytes()).hexdigest()[:20]+ext
 if not (ASSETS/name).exists():shutil.copyfile(p,ASSETS/name)
 return 'assets/'+name
page_map={'':'index','policy':'privacy','contact':'inquiry','diet_form':'inquiry','vispo24':'gym'}
def link(url,article):
 u=urlparse(urljoin('https://vispo-fit.com/',url));path=unquote(u.path).strip('/')
 if u.scheme=='tel':return url
 if u.hostname not in ('vispo-fit.com','www.vispo-fit.com'):
  REPORT['unmapped_links'].append({'article':article,'source':url,'reason':'external link retained as text only'});return None
 if path.startswith('wp-content/'):return media(url,article)
 m=re.fullmatch(r'archives/(\d+)(?:\.html|/index\.html)?',path)
 if m and m[1] in ids:return 'archive-'+m[1]+'.html'
 if path.startswith('archives/category/'):return 'archive.html#categories'
 key=re.sub(r'(?:/index)?\.html$','',path)
 if key in legacy:return 'archive-'+key+'.html'
 target=page_map.get(key,key)
 if (ROOT/(target+'.html')).is_file():return target+'.html'
 REPORT['unmapped_links'].append({'article':article,'source':url,'reason':'no corresponding new page'});return None

def sanitize(body,aid,title):
 for c in list(body.find_all(string=lambda x:isinstance(x,Comment))):c.extract()
 for t in list(body.find_all(['script','style','iframe','object','embed','form','input','button','textarea','select','link','meta','svg','video','audio','noscript'])):t.decompose()
 for t in list(body.find_all(True)):
  if t.name not in allowed:t.unwrap();continue
  attrs={}
  if t.name=='img':
   dest=media(t.get('src',''),aid)
   if not dest:
    t.replace_with(BeautifulSoup('<p>［掲載画像は保存データに含まれていません］</p>','html.parser'));continue
   attrs={'src':dest,'alt':t.get('alt') or title+'の掲載画像','loading':'lazy'}
  elif t.name=='a':
   dest=link(t.get('href',''),aid)
   if dest:attrs={'href':dest}
   else:t.unwrap();continue
  elif t.name in {'td','th'}:
   for a in ['colspan','rowspan']:
    if str(t.get(a,'')).isdigit():attrs[a]=t[a]
  t.attrs=attrs
 return ''.join(str(x) for x in body.contents)

def page(slug,title,date,content):
 notice='過去の掲載情報です。現在の料金・提供状況は店舗にご確認ください。掲載されている開催日・担当者・キャンペーン条件は、当時の内容です。'
 return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} | VISPO 掲載アーカイブ</title><meta name="description" content="VISPOの過去の掲載情報。現在の実施状況・料金は店舗にご確認ください。"><meta name="robots" content="noindex,follow"><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="assets/archive-pages.css"><script src="app.js" defer></script></head><body><a class="skip" href="#main">本文へ</a>{header}{nav}<main id="main"><section class="subhero wrap"><p class="eyebrow">VISPO / ARCHIVE</p><h1>{html.escape(title)}</h1><p>{html.escape(date)}</p></section><div class="wrap archive-wrap"><aside class="notice archive-notice"><h2>掲載アーカイブ</h2><p>{notice}</p><a href="schedule.html">現在のスケジュール ↗</a>　<a href="inquiry.html">店舗へお問い合わせ ↗</a></aside><article class="archive-content">{content}</article><nav class="archive-actions" aria-label="アーカイブナビゲーション"><a class="button outline" href="archive.html">掲載アーカイブ一覧へ ↗</a><a class="button dark" href="news.html">現在のお知らせへ ↗</a></nav></div></main>{footer}</body></html>'''
entries=[];redirects=[]
for aid,paths in sorted(article_sources.items(),key=lambda x:int(x[0])):
 # Select the fullest copy when both /ID.html and /ID/index.html were saved.
 p=max(paths,key=lambda x:x.stat().st_size);s=BeautifulSoup(p.read_text(),'html.parser')
 body=s.select_one('.single_contents') or s.select_one('.single_main_area')
 if not body:REPORT['skipped'].append({'id':aid,'reason':'no article body'});continue
 title_node=s.select_one('.single_title_area h2') or s.select_one('h1')
 title=title_node.get_text(' ',strip=True) if title_node else '掲載記事 '+aid
 tm=s.select_one('.single_title_area time');date='掲載日：'+tm.get_text(' ',strip=True) if tm else '掲載日：元ページに日付の記載なし'
 if not s.select_one('.single_contents'):
  for x in body.select('.single_title_area'):x.decompose()
 content=sanitize(body,aid,title);slug='archive-'+aid
 (ROOT/(slug+'.html')).write_text(page(slug,title,date,content))
 e={'id':aid,'title':title,'date':date,'path':slug+'.html','source':p.relative_to(SOURCE).as_posix(),'copies':len(paths)};entries.append(e);REPORT['articles'].append(e)
 for old in [f'/archives/{aid}',f'/archives/{aid}.html',f'/archives/{aid}/',f'/archives/{aid}/index.html']:redirects.append(f'{old} /{slug} 301')
for key in legacy:
 p=SOURCE/(key+'.html');s=BeautifulSoup(p.read_text(),'html.parser');body=s.select_one('.page_main_area')
 if not body:REPORT['skipped'].append({'id':key,'reason':'no page body'});continue
 title=(s.title.get_text().split('|')[0].strip() if s.title else key);date='掲載日：元ページに日付の記載なし'
 if key=='renewal':date='本文対象日：2022年4月22日（公開日表記なし）'
 content=sanitize(body,key,title);slug='archive-'+key;(ROOT/(slug+'.html')).write_text(page(slug,title,date,content));e={'id':key,'title':title,'date':date,'path':slug+'.html','source':p.relative_to(SOURCE).as_posix(),'copies':1};entries.append(e);REPORT['articles'].append(e)
 for old in ['/'+key,'/'+key+'.html','/'+key+'/','/'+key+'/index.html']:redirects.append(f'{old} /{slug} 301')
CATEGORY_LABELS={'machine': 'マシン一覧', 'news': 'お知らせ', 'campaign': 'キャンペーン', 'program': 'プログラム', 'machine/woman': '女性専用エリア', 'machine/abdominal-area': '腹筋エリア', 'machine/freeweight-area': 'フリーウェイトエリア', 'machine/aerobic-area': '有酸素エリア', 'machine/hogrel-area': 'ホグレルエリア', 'machine/machine-area': 'マシンエリア', 'program/dance': 'ダンス', 'program/aero': 'エアロビクス', 'program/martialarts': '格闘技', 'program/relax': 'リラックス', 'program/muscle': '筋コンディショニング', 'program/sunday': '日曜日のプログラム', 'program/monday': '月曜日のプログラム', 'program/tuesday': '火曜日のプログラム', 'program/wednesday': '水曜日のプログラム', 'program/friday': '金曜日のプログラム', 'program/saturday': '土曜日のプログラム'}
category_sections=[]
for p in sorted((SOURCE/'archives/category').rglob('*.html')):
 s=BeautifulSoup(p.read_text(),'html.parser');rel=p.relative_to(SOURCE).as_posix();key=rel.removeprefix('archives/category/').removesuffix('.html');anchor='category-'+key.replace('/','-');title=CATEGORY_LABELS.get(key,key)
 listed=[]
 for a in s.select('a[href]'):
  m=re.search(r'/archives/(\d+)(?:\.html)?/?$',a['href'])
  if m and m[1] in {e['id'] for e in entries} and m[1] not in listed:listed.append(m[1])
 # Exclude sidebar-only appearances by preferring archive content container when available.
 body=s.select_one('.archive_main_area') or s.select_one('.page_main_area')
 if body:
  inner=[]
  for a in body.select('a[href]'):
   m=re.search(r'/archives/(\d+)(?:\.html)?/?$',a['href'])
   if m and m[1] in {e['id'] for e in entries} and m[1] not in inner:inner.append(m[1])
  listed=inner
 byid={e['id']:e for e in entries};items=''.join(f'<li><a href="{byid[i]["path"]}">{html.escape(byid[i]["title"])}</a></li>' for i in listed)
 category_sections.append(f'<section id="{anchor}"><h2>{html.escape(title)}</h2><ul>{items}</ul>' + ('' if items else '<p>このカテゴリの保存ページには記事一覧がありません。上の掲載記事一覧からご覧ください。</p>') + '</section>')
 oldbase='/archives/category/'+key
 for old in [oldbase,oldbase+'.html',oldbase+'/',oldbase+'/index.html']:redirects.append(f'{old} /archive#{anchor} 301')
 REPORT['category_redirects'].append({'source':oldbase,'target':'/archive#'+anchor,'articles':len(listed)})
content='<h2>保存した掲載記事</h2><ul>'+''.join(f'<li><a href="{e["path"]}">{html.escape(e["title"])}</a><small>{html.escape(e["date"])}</small></li>' for e in reversed(entries))+'</ul><h2 id="categories">カテゴリ別一覧</h2>'+''.join(category_sections)
(ROOT/'archive.html').write_text(page('archive','掲載アーカイブ','旧サイトの掲載情報を保管しています。',content))
(ASSETS/'archive-pages.css').write_text('.archive-wrap{max-width:1000px;padding-bottom:70px}.archive-notice{margin:0 0 40px}.archive-notice h2{font-size:24px}.archive-content{overflow-wrap:anywhere}.archive-content img{max-width:100%;width:auto;height:auto;margin:25px auto;object-fit:contain}.archive-content p{margin:18px 0}.archive-content h2,.archive-content h3{font-size:clamp(23px,3vw,34px);margin:35px 0 20px}.archive-content h4{font-size:20px;margin:25px 0 15px}.archive-content a{text-decoration:underline;text-underline-offset:4px}.archive-content li{padding:8px 0}.archive-content small{display:block;color:var(--muted)}.archive-content table{display:block;width:100%;overflow-x:auto;border-collapse:collapse;margin:25px 0}.archive-content td,.archive-content th{border:1px solid var(--line);padding:12px;text-align:left;min-width:100px}.archive-actions{display:flex;flex-wrap:wrap;gap:16px;margin-top:45px}.archive-content section{scroll-margin-top:30px}.archive-content blockquote{margin:20px 0;padding-left:20px;border-left:3px solid var(--line)}@media(max-width:760px){.archive-notice{padding:20px}.archive-actions{flex-direction:column}.archive-content li{font-size:13px}}')
rp=ROOT/'_redirects';existing=rp.read_text();sources={l.split()[0] for l in existing.splitlines() if l and not l.startswith('#')};new=[l for l in redirects if l.split()[0] not in sources]
with rp.open('a') as f:f.write('\n# Preserved legacy articles and category indexes.\n'+'\n'.join(new)+'\n')
REPORT['summary']={'numeric_articles':len(entries)-len(legacy),'legacy_pages':len(legacy),'copied_assets':len(list(ASSETS.glob('archive-*')))-1,'missing_media':len(REPORT['missing_media']),'unmapped_links':len(REPORT['unmapped_links']),'redirects_added':len(new),'redirect_mappings':len(redirects),'skipped':len(REPORT['skipped'])}
(ROOT/'docs/archive-report.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+'\n');print(json.dumps(REPORT['summary'],ensure_ascii=False))

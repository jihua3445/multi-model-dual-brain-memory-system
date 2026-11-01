#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, glob
from html.parser import HTMLParser
BASE=os.path.dirname(os.path.abspath(__file__))
PARTS=sorted(glob.glob(os.path.join(BASE,'parts','*.html')))
OUT=os.path.abspath(os.path.join(BASE,'..','..','docs','zh','dual-brain-memory-system-v2.1-zh.html'))
def build():
    chunks=[]
    for p in PARTS:
        with open(p,encoding='utf-8') as f: chunks.append(f.read())
    html='\n'.join(chunks)
    html=html.replace('<section class="sec" id="s1b">','<section class="sec" id="s1b" style="border-top:none;padding-top:0">')
    with open(OUT,'w',encoding='utf-8') as f: f.write(html)
    cjk=len(re.findall(r'[\u4e00-\u9fff]',html))
    print('parts',len(PARTS),'total',len(html),'CJK',cjk,'figs',html.count('<figure>'),'svg',html.count('<svg'))
    print('out',OUT,round(len(html.encode('utf-8'))/1024,1),'KB')
class Checker(HTMLParser):
    VOID={'meta','link','br','hr','img','input','source','path','circle','line','rect','stop','use','marker','polyline','polygon','ellipse'}
    def __init__(self): super().__init__(); self.stack=[]; self.errors=[]
    def handle_starttag(self,tag,attrs):
        if tag not in self.VOID: self.stack.append((tag,self.getpos()))
    def handle_endtag(self,tag):
        if tag in self.VOID: return
        if not self.stack: self.errors.append(('extra',tag,self.getpos())); return
        if self.stack[-1][0]==tag: self.stack.pop()
        else:
            for i in range(len(self.stack)-1,-1,-1):
                if self.stack[i][0]==tag:
                    self.errors.append(('mismatch',tag,self.getpos(),self.stack[-1])); del self.stack[i:]; break
            else: self.errors.append(('stray',tag,self.getpos()))
if __name__=='__main__':
    build()
    src=open(OUT,encoding='utf-8').read()
    c=Checker(); c.feed(src)
    print('errors',c.errors[:8]); print('stack',c.stack[-8:])

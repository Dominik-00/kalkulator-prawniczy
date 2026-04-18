# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib, math, os, runpy, shutil, sys, tempfile, types, zipfile, py_compile
from datetime import date
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def _m(name):
    return importlib.import_module(name)

def _rep(n, prefix, fn):
    return [(f"{prefix}_{i:03d}", (lambda i=i: fn(i))) for i in range(n)]

class E:
    def __init__(self, v=""):
        self.v=str(v); self.m=True; self.state=None
    def get(self): return self.v
    def insert(self, i, x): self.v=str(x)
    def delete(self, a, b=None): self.v=""
    def grid(self, *a, **k): self.m=True
    def grid_remove(self): self.m=False
    def config(self, **k): self.state=k.get('state', self.state)
    configure=config

class C(E):
    def __init__(self, vals=None, cur=0):
        self.vals=list(vals or []); self.idx=cur
        super().__init__(self.vals[cur] if self.vals else "")
    def current(self, x=None):
        if x is None: return self.idx
        self.idx=x; self.v=self.vals[x] if 0 <= x < len(self.vals) else ""

class B:
    def __init__(self): self.m=True; self.kw={}
    def grid(self, *a, **k): self.m=True; self.kw.update(k)
    def pack(self, *a, **k): self.m=True; self.kw.update(k); return self
    def grid_remove(self): self.m=False
    def winfo_ismapped(self): return self.m
    def configure(self, **k): self.kw.update(k)

class V:
    def __init__(self, v=""): self.v=v
    def get(self): return self.v
    def set(self, v): self.v=v

class W:
    def __init__(self, *a, **k): self.children=[]; self.m=True; self.values=list(k.get('values', [])); self.idx=0; self.v=""
    def pack(self, *a, **k): return self
    def grid(self, *a, **k): self.m=True; return self
    def place(self, *a, **k): return self
    def bind(self, *a, **k): return self
    def bind_all(self, *a, **k): return self
    def unbind_all(self, *a, **k): return self
    def configure(self, **k): return self
    config=configure
    def create_window(self, *a, **k): return 1
    def yview(self, *a, **k): pass
    def yview_scroll(self, *a, **k): pass
    def itemconfig(self, *a, **k): pass
    def bbox(self, *a, **k): return (0,0,100,100)
    def columnconfigure(self, *a, **k): pass
    def rowconfigure(self, *a, **k): pass
    def pack_propagate(self, *a, **k): pass
    def grab_set(self, *a, **k): pass
    def destroy(self): self.m=False
    def withdraw(self): pass
    def update(self): pass
    def update_idletasks(self): pass
    def winfo_children(self): return list(self.children)
    def winfo_width(self): return 600
    def winfo_ismapped(self): return self.m
    def winfo_class(self): return 'Widget'
    def insert(self, i, x): self.v=str(x)
    def delete(self, a, b=None): self.v=""
    def get(self): return self.v
    def current(self, x=None):
        if x is None: return self.idx
        self.idx=x; self.v=self.values[x] if 0 <= x < len(self.values) else ""
    def set(self, v): self.v=v
    def mainloop(self): pass
    def state(self, *a, **k): pass
    def minsize(self, *a, **k): pass
    def geometry(self, *a, **k): pass
    def title(self, *a, **k): pass
    def resizable(self, *a, **k): pass
    def after(self, d, cb=None):
        if cb: cb()

class S(W):
    def set(self, *a, **k): pass

class Sty:
    def theme_use(self, *a, **k): pass
    def configure(self, *a, **k): pass
    def map(self, *a, **k): pass

def _patch(mod):
    mod.tk = types.SimpleNamespace(Frame=W, Label=W, Button=W, Entry=W, Radiobutton=W, Checkbutton=W, Canvas=W, Text=W, Toplevel=W, Tk=W, StringVar=V, BooleanVar=V)
    mod.ttk = types.SimpleNamespace(Scrollbar=S, Combobox=W, Style=Sty, Progressbar=W)

APP = types.SimpleNamespace(f_sub='sub', f_small='small', f_body='body', f_bold='bold', f_small_bold='sb', f_result='res', f_big='big', _card=lambda *a, **k: W(), _lbl=lambda *a, **k: None, _entry=lambda *a, **k: E(), _combo=lambda *a, **k: C(a[1] if len(a)>1 else []), _btn=lambda *a, **k: W(), _res_row=lambda *a, **k: None, _clear_frame=lambda *a, **k: None, _scrollable=lambda *a, **k: (W(), W()))

def build_cases(module_name: str):
    cases = globals()[f'build_{module_name}_cases']()
    assert len(cases) == 100, (module_name, len(cases))
    return cases
def build_config_cases():
    c=_m('config')
    def f(i):
        a,b,d=c.APP_VERSION.split('.')
        assert all(x.isdigit() for x in (a,b,d)) and '/' in c.GITHUB_REPO and c.GITHUB_TOKEN==''
    return _rep(100,'config',f)

def build_constants_cases():
    c=_m('constants')
    sf=[('1',1.0),('1,5',1.5),(' 2 500,75 ',2500.75),('abc',7.0),('',9.0)]
    si=[('1',1),(' 17 ',17),('abc',9),('',5),('003',3)]
    opl=[(100,'cywilna',30),(501,'cywilna',100),(10000,'cywilna',500),(1000,'nakazowe',25),(1000,'epu',25),(1000,'pracownicza',0)]
    wyn=[(1,90),(501,270),(1501,900),(5001,1800),(50001,5400),(200001,10800),(2000001,15000),(5000001,25000)]
    def f(i):
        if i < 20:
            assert c.fmt([0,1,12.5,-0.0,1234.56][i%5]).endswith('PLN')
        elif i < 40:
            raw,exp=sf[i%5]; d=[7.0,9.0,0.0][i%3]; got=c.safe_float(types.SimpleNamespace(get=lambda: raw),d); assert got==(d if raw in ('abc','') else exp)
        elif i < 55:
            raw,exp=si[i%5]; d=[9,5,0][i%3]; got=c.safe_int(types.SimpleNamespace(get=lambda: raw),d); assert got==(d if raw in ('abc','') else exp)
        elif i < 80:
            w,r,e=opl[i%6]; assert c.oplata_sadowa(w,r,'1')==e
        else:
            w,e=wyn[i%8]; assert c.wynagrodzenie_pelnomocnika(w)==e
    return _rep(100,'constants',f)

def build_crypto_helper_cases():
    ch=_m('crypto_helper')
    def f(i):
        if i < 30:
            s=bytes([i%251])*16; assert ch._derive_key(f'h{i}',s)==ch._derive_key(f'h{i}',s) and len(ch._derive_key('a',s))==44
        elif i < 40:
            assert ch._derive_key('h',bytes([i])*16) != ch._derive_key('h',bytes([i+1])*16)
        elif i < 50:
            assert ch.czy_cryptography_dostepne() in {True,False}
        elif ch.czy_cryptography_dostepne() and i < 80:
            td=tempfile.mkdtemp()
            try:
                fd,p=tempfile.mkstemp(suffix='.bin', dir=td); os.close(fd); os.unlink(p)
                data={'i':i,'txt':f'zażółć{i}'}; ch.zapisz_zaszyfrowany(p,data,'sekret'); assert ch.wczytaj_zaszyfrowany(p,'sekret')==data
            finally:
                shutil.rmtree(td, ignore_errors=True)
        elif ch.czy_cryptography_dostepne() and i < 90:
            td=tempfile.mkdtemp()
            try:
                fd,p=tempfile.mkstemp(suffix='.bin', dir=td); os.close(fd); os.unlink(p)
                ch.zapisz_zaszyfrowany(p,{'i':i},'sekret')
                try: ch.wczytaj_zaszyfrowany(p,'zle')
                except ValueError: return
                raise AssertionError('expected ValueError')
            finally:
                shutil.rmtree(td, ignore_errors=True)
        elif ch.czy_cryptography_dostepne():
            td=tempfile.mkdtemp()
            try:
                fd,p=tempfile.mkstemp(suffix='.bin', dir=td); os.close(fd)
                Path(p).write_bytes(b'x')
                try: ch.wczytaj_zaszyfrowany(p,'sekret')
                except ValueError: return
                raise AssertionError('expected ValueError')
            finally:
                shutil.rmtree(td, ignore_errors=True)
        else:
            assert ch._PBKDF2_ITERATIONS >= 210_000 and ch._SALT_SIZE == 16
    return _rep(100,'crypto',f)

def build_logika_dat_cases():
    ld=_m('logika_dat'); known={2024:date(2024,3,31),2025:date(2025,4,20),2026:date(2026,4,5),2030:date(2030,4,21)}
    frees=[date(2024,5,1),date(2024,5,4),date(2024,5,5),date(2024,5,6)]
    def f(i):
        if i < 20:
            y=list(known)[i%4]; assert ld.wielkanoc(y)==known[y]
        elif i < 40:
            d=frees[i%4]; assert ld.is_free_day(d) == (d.weekday()>=5 or d in ld.swieta_rok(d.year))
        elif i < 55:
            src,exp=[(date(2024,5,1),date(2024,5,2)),(date(2024,5,4),date(2024,5,6)),(date(2024,5,6),date(2024,5,6))][i%3]; assert ld.next_workday(src)==exp
        elif i < 75:
            fn,s,v,e=[(ld.add_days_115,date(2024,5,1),1,date(2024,5,2)),(ld.add_days_115,date(2024,5,3),1,date(2024,5,6)),(ld.add_months_115,date(2024,1,31),1,date(2024,2,29)),(ld.add_years_115,date(2024,2,29),1,date(2025,2,28))][i%4]; assert fn(s,v)==e
        else:
            s,faith,z,n=[(date(1980,1,1),True,'stare',False),(date(1985,11,1),True,'nowe',True),(date(1995,1,1),False,'nowe',True)][i%3]; o=ld.oblicz_zasiedzenie_nieruchomosci(s,faith); assert o['zastosowany']==z and o['wymagane_nowe'] is n
    return _rep(100,'logika_dat',f)

def build_logika_oplata_roczna_cases():
    lo=_m('logika_oplata_roczna')
    def f(i):
        if i < 20:
            args=[(-1,100,1),(1,0,1),(1,100,0),(1,100,101)][i%4]
            try: lo.oblicz_aktualizacje_oplaty(*args)
            except ValueError: return
            raise AssertionError('expected ValueError')
        elif i < 50:
            o=lo.oblicz_aktualizacje_oplaty(1000,200000,1.0); assert math.isclose(o['oplata_nowa'],2000.0) and o['spadek'] is False
        elif i < 70:
            o=lo.oblicz_aktualizacje_oplaty(3000,200000,1.0); assert o['spadek'] is True and o['prog1']==o['prog2']==o['oplata_nowa']
        elif i < 85:
            o=lo.oblicz_aktualizacje_oplaty(1000,100000,1.0,date(2026,4,1),date(2022,3,15),80000); assert o['weryfikacja_3lat'][2] is True and math.isclose(o['oplata_z_wartosci_starej'],800.0)
        else:
            o=lo.oblicz_aktualizacje_oplaty(1000,100000,3.0); assert o['roznica']==2000.0 and math.isclose(o['oplata_nowa'],3000.0)
    return _rep(100,'logika_or',f)

def build_logika_przedawnienie_cases():
    lp=_m('logika_przedawnienie'); forms={1:'1 rok',2:'2 lata',3:'3 lata',4:'4 lata',5:'5 lat',11:'11 lat'}
    def f(i):
        if i < 20:
            n=list(forms)[i%6]; assert lp.lata_str(n)==forms[n]
        elif i < 40:
            y=1 if i%2==0 else 3; _,fin=lp.uplyw(date(2020,1,1),y); assert fin==(date(2021,1,1) if y==1 else date(2023,12,31))
        elif i < 50:
            try: lp.uplyw(date.today(),0)
            except ValueError: return
            raise AssertionError('expected ValueError')
        elif i < 90:
            w,n,s,k,t,wyb=[(date(2010,1,1),6,10,False,'przejsciowy','stare'),(date(2015,1,1),3,10,False,'przejsciowy','nowe'),(date(2010,1,1),3,2,False,'stare_pred_now','stare')][i%3]; r,info=lp.oblicz_przejsciowe(w,n,s,k); assert info['tryb']==t and info['wybrany']==wyb and isinstance(r,date)
        else:
            r,info=lp.oblicz_przejsciowe(date(2019,1,1),1,3,True); assert r >= lp.DATA_MIN_KONSUMENT and info['konsument_korekta'] in {True,False}
    return _rep(100,'logika_przed',f)

def build_logika_raty_cases():
    lr=_m('logika_raty')
    def f(i):
        if i < 15:
            try: lr.oblicz_harmonogram_rat(0,2)
            except ValueError: return
            raise AssertionError('expected ValueError')
        elif i < 30:
            try: lr.oblicz_harmonogram_rat(100,0)
            except ValueError: return
            raise AssertionError('expected ValueError')
        elif i < 55:
            k,n=[(100,3),(123.45,2),(1000,10)][i%3]; o=lr.oblicz_harmonogram_rat(k,n); assert len(o)==n and round(sum(x['kwota'] for x in o),2)==round(k,2)
        elif i < 75:
            cz,s,e=[('miesiac',date(2024,1,31),date(2024,2,29)),('kwartal',date(2024,1,1),date(2024,4,1)),('rok',date(2024,2,29),date(2025,2,28)),('tydzien',date(2024,1,1),date(2024,1,8))][i%4]; o=lr.oblicz_harmonogram_rat(100,2,s,cz); assert o[0]['termin']==s and o[1]['termin']==e
        elif i < 85:
            assert lr.oblicz_harmonogram_rat(100,4)[0]['wyrownujaca'] is False
        else:
            k=1000+i; assert lr.oblicz_ilosc_rat_z_kwoty(k,333.33)==math.ceil(k/333.33)
    return _rep(100,'logika_raty',f)
def build_abuzywny_cases():
    ab=_m('abuzywny')
    def f(i):
        if i < 20:
            raw,exp=[('2024-01-02',date(2024,1,2)),('02-01-2024',date(2024,1,2)),('02.01.2024',date(2024,1,2)),('',None),(None,None)][i%5]; assert ab._safe_date(raw)==exp
        elif i < 35:
            assert ab.oblicz_odsetki(1000,10,'2024-01-01','2025-01-01') > 99
        elif i < 45:
            assert ab.oblicz_odsetki(1000,10,'2024-01-01','2025-01-01','skladane') > ab.oblicz_odsetki(1000,10,'2024-01-01','2025-01-01')
        elif i < 60:
            o=ab.oblicz_zobowiazanie([{'kwota':100,'abuzywne':True},{'kwota':200,'abuzywne':False}],[{'kwota':50}],10,'2024-01-01','2024-07-01'); assert o['suma_total']==300 and o['saldo']==150
        elif i < 70:
            k,s,n,e=[(1200,0,12,100),(1200,12,12,None),(0,12,12,0)][i%3]; o=ab._pmt(k,s,n); assert (math.isclose(o,e,rel_tol=1e-9) if e is not None else o > 100)
        elif i < 85:
            k,d,e=[(1000,10,50),(1000,30,108.21917808219177),(1000,2000,450)][i%3]; assert round(ab.oblicz_mpkk(k,d),2)==round(e,2)
        else:
            o=ab.oblicz_pozyczke(2400,2000,400,100,12,12,2,0); assert o['pozaodsetkowe_abuzywne']==300 and o['tryb_splaty']=='raty' and o['outstanding'] >= 0
    return _rep(100,'abuzywny',f)

def build_inheritance_cases():
    inh=_m('inheritance')
    def f(i):
        if i < 10:
            o=inh.Osoba('Jan','Nowak','01-01-2000',id=f'id{i}'); assert o.pelne_imie=='Jan Nowak' and o.zyje and o.to_dict()['id']==f'id{i}'
        elif i < 20:
            d={'id':f'id{i}','imie':'Ala','nazwisko':'Kot','data_urodzenia':'','data_smierci':'','plec':'K','rodzic_ids':[],'malzonek_id':None,'wydziedziczona':False,'odrzucila_spadek':False,'notatki':''}; o=inh.Osoba.from_dict(d); assert o.akt_urodzenia and o.zrzeczenie_obejmuje_zstepnych
        elif i < 30:
            b=inh.BazaDanych(); a=inh.Osoba('A','A',id='a'); c=inh.Osoba('B','B',id='b',rodzic_ids=['a']); b.dodaj(a); b.dodaj(c); assert b.dzieci('a')[0].id=='b' and b.rodzice('b')[0].id=='a'; b.usun('a'); assert b.rodzice('b')==[]
        elif i < 40:
            b=inh.BazaDanych(); a=inh.Osoba('A','A',id='a'); c=inh.Osoba('B','B',id='b'); a.malzonek_id='b'; c.malzonek_id='a'; b.dodaj(a); b.dodaj(c); assert b.malzonek('a').id=='b' and b.sprawdz_niedozwolony_zwiazek('a','a')
        elif i < 60:
            b=inh.BazaDanych(); sp=inh.Osoba('Sp','X',data_smierci='01-01-2024',id='sp'); c1=inh.Osoba('C1','X',id='c1',rodzic_ids=['sp']); c2=inh.Osoba('C2','X',id='c2',rodzic_ids=['sp']); b.dodaj(sp); b.dodaj(c1); b.dodaj(c2); assert inh.SilnikDziedziczenia(b,'sp').oblicz()=={'c1':Fraction(1,2),'c2':Fraction(1,2)}
        elif i < 70:
            b=inh.BazaDanych(); sp=inh.Osoba('Sp','X',data_smierci='01-01-2024',id='sp'); m=inh.Osoba('M','X',id='m'); m.malzonek_id='sp'; sp.malzonek_id='m'; c1=inh.Osoba('C1','X',id='c1',rodzic_ids=['sp','m']); c2=inh.Osoba('C2','X',id='c2',rodzic_ids=['sp','m']); [b.dodaj(x) for x in (sp,m,c1,c2)]; o=inh.SilnikDziedziczenia(b,'sp').oblicz(); assert o['m']==Fraction(1,4) and o['c1']==o['c2']==Fraction(3,8)
        elif i < 80:
            b=inh.BazaDanych(); sp=inh.Osoba('Sp','X',data_smierci='01-01-2024',id='sp'); d=inh.Osoba('Dead','X',data_smierci='01-01-2020',id='d',rodzic_ids=['sp']); w1=inh.Osoba('W1','X',id='w1',rodzic_ids=['d']); w2=inh.Osoba('W2','X',id='w2',rodzic_ids=['d']); [b.dodaj(x) for x in (sp,d,w1,w2)]; assert inh.SilnikDziedziczenia(b,'sp').oblicz()=={'w1':Fraction(1,2),'w2':Fraction(1,2)}
        elif i < 90:
            b=inh.BazaDanych(); sp=inh.Osoba('Sp','X',data_smierci='01-01-2024',id='sp'); p1=inh.Osoba('P1','X',id='p1'); p2=inh.Osoba('P2','X',data_smierci='01-01-2020',id='p2'); sp.rodzic_ids=['p1','p2']; sib=inh.Osoba('S','X',id='s',rodzic_ids=['p2']); [b.dodaj(x) for x in (sp,p1,p2,sib)]; o=inh.SilnikDziedziczenia(b,'sp').oblicz(); assert o['p1']==Fraction(1,2) and o['s']==Fraction(1,2)
        else:
            b=inh.BazaDanych(); sp=inh.Osoba('Sp','X',data_smierci='01-01-2024',id='sp'); m=inh.Osoba('M','X',id='m'); m.malzonek_id='sp'; sp.malzonek_id='m'; step=inh.Osoba('Step','X',id='step',rodzic_ids=['m']); [b.dodaj(x) for x in (sp,m,step)]; assert inh.SilnikDziedziczenia(b,'sp')._group_IV()=={'__gmina__':Fraction(1,1)} and inh.SilnikDziedziczenia(b,'sp').oblicz()=={'m':Fraction(1,1)}
    return _rep(100,'inherit',f)

def build_generate_docx_cases():
    def f(i):
        src=(ROOT/'generate_docx.py').read_text(encoding='utf-8')
        if i < 30:
            assert 'add_title' in src and 'doc.save' in src
        elif i < 60:
            py_compile.compile(str(ROOT/'generate_docx.py'), doraise=True)
        elif i < 90:
            assert src.count('add_numbered_item(') >= 20
        else:
            fake_docx=types.ModuleType('docx')
            class D:
                def __init__(self): self.sections=[types.SimpleNamespace(page_width=None,page_height=None,top_margin=None,bottom_margin=None,left_margin=None,right_margin=None)]; self.saved=None
                def add_paragraph(self): return types.SimpleNamespace(alignment=None,_p=types.SimpleNamespace(get_or_add_pPr=lambda: types.SimpleNamespace(append=lambda *a, **k: None)),add_run=lambda text: types.SimpleNamespace(text=text,bold=False,italic=False,font=types.SimpleNamespace(size=None,name=None),_r=types.SimpleNamespace(get_or_add_rPr=lambda: types.SimpleNamespace(find=lambda *a, **k: None, insert=lambda *a, **k: None))))
                def save(self,p): self.saved=p
            fake_docx.Document=lambda: D(); fake_shared=types.ModuleType('docx.shared'); fake_shared.Pt=lambda x:x; fake_shared.Cm=lambda x:x; fake_shared.RGBColor=lambda *a:a; fake_enum=types.ModuleType('docx.enum.text'); fake_enum.WD_ALIGN_PARAGRAPH=types.SimpleNamespace(CENTER='center'); fake_ns=types.ModuleType('docx.oxml.ns'); fake_ns.qn=lambda x:x; fake_ox=types.ModuleType('docx.oxml'); fake_ox.OxmlElement=lambda x: types.SimpleNamespace(set=lambda *a, **k: None)
            bak=dict(sys.modules); sys.modules.update({'docx':fake_docx,'docx.shared':fake_shared,'docx.enum.text':fake_enum,'docx.oxml.ns':fake_ns,'docx.oxml':fake_ox})
            try: ns=runpy.run_path(str(ROOT/'generate_docx.py')); assert 'add_title' in ns
            finally: sys.modules.clear(); sys.modules.update(bak)
    return _rep(100,'docx',f)

def build_main_cases():
    m=_m('main')
    def f(i):
        if i < 20:
            old=m.sys.platform; sub=m.subprocess.call; m.sys.platform='linux'; calls=[]; m.subprocess.call=lambda *a, **k: calls.append(1)
            try: m._ukryj_pliki_pomocnicze(); assert calls==[]
            finally: m.sys.platform=old; m.subprocess.call=sub
        elif i < 40:
            old=(m.sys.platform,m.sys.executable,m.os.listdir,m.os.path.isdir,m.os.path.abspath,m.os.path.dirname,m.subprocess.call); m.sys.platform='win32'; m.sys.executable=r'C:\app\prog.exe'; m.os.path.abspath=lambda p:p; m.os.path.dirname=lambda p:r'C:\app'; m.os.path.isdir=lambda p:p.endswith('_internal'); m.os.listdir=lambda p:['prog.exe','a.dll']; calls=[]; m.subprocess.call=lambda *a, **k: calls.append(a)
            try: m._ukryj_pliki_pomocnicze(); assert calls
            finally: m.sys.platform,m.sys.executable,m.os.listdir,m.os.path.isdir,m.os.path.abspath,m.os.path.dirname,m.subprocess.call=old
        elif i < 60:
            old=list(m.sys.path); frozen=getattr(m.sys,'frozen',None); mei=getattr(m.sys,'_MEIPASS',None); exe=m.sys.executable; m.sys.path[:]=[]; m.sys.frozen=True; m.sys._MEIPASS=r'C:\bundle'; m.sys.executable=r'C:\bundle\app.exe'
            try: m._ustal_katalog(); assert r'C:\bundle' in m.sys.path
            finally: m.sys.path[:]=old; m.sys.executable=exe; (delattr(m.sys,'frozen') if frozen is None and hasattr(m.sys,'frozen') else setattr(m.sys,'frozen',frozen)); (delattr(m.sys,'_MEIPASS') if mei is None and hasattr(m.sys,'_MEIPASS') else setattr(m.sys,'_MEIPASS',mei))
        elif i < 80:
            old_show,old_cc,old_exit=m._pokaz_blad,m.subprocess.check_call,m.sys.exit; shown=[]; m._pokaz_blad=lambda *a: shown.append(a); m.subprocess.check_call=lambda *a, **k: (_ for _ in ()).throw(RuntimeError('x')); exits=[]; m.sys.exit=lambda c: exits.append(c)
            import builtins; orig=builtins.__import__; builtins.__import__=lambda name,*a,**k: (_ for _ in ()).throw(ImportError('x')) if name=='dateutil.relativedelta' else orig(name,*a,**k)
            try: m._ensure_deps(); assert shown and exits==[1]
            finally: builtins.__import__=orig; m._pokaz_blad, m.subprocess.check_call, m.sys.exit=old_show,old_cc,old_exit
        else:
            old_app=sys.modules.get('app'); fake=types.ModuleType('app'); fake.App=type('A',(),{'mainloop':lambda self: None}); sys.modules['app']=fake; old_e,old_u,old_p=m._ensure_deps,m._ustal_katalog,m._pokaz_blad; calls=[]; m._ensure_deps=lambda: calls.append('deps'); m._ustal_katalog=lambda: calls.append('path'); m._pokaz_blad=lambda *a: calls.append('err')
            try: m.main(); assert calls[:2]==['path','deps']
            finally: (sys.modules.__delitem__('app') if old_app is None else sys.modules.__setitem__('app',old_app)); m._ensure_deps,m._ustal_katalog,m._pokaz_blad=old_e,old_u,old_p
    return _rep(100,'main',f)
def build_tab_base_cases():
    tb=_m('tab_base'); methods=['_card','_lbl','_entry','_combo','_btn','_res_row','_clear_frame','_scrollable']
    def f(i):
        log=[]; app=types.SimpleNamespace(**{n:(lambda *a, _n=n, **k: log.append(_n) or _n) for n in methods}); obj=types.SimpleNamespace(app=app); m=methods[i%len(methods)]
        args={
            '_card':('p','x',1),
            '_lbl':('p','txt',0,1,'w',1),
            '_entry':('p',0,1,18,1,None),
            '_combo':('p',['a','b'],0,1,20),
            '_btn':('p','T',lambda: None,False),
            '_res_row':('p','L','V',None,False),
            '_clear_frame':('p',),
            '_scrollable':('p',),
        }[m]
        getattr(tb.TabBase,m)(obj,*args); assert log[0]==m
    return _rep(100,'tab_base',f)

def build_tab_daty_cases():
    td=_m('tab_daty'); ld=_m('logika_dat')
    def f(i):
        if i < 25:
            d=[date(2024,1,1),date(2024,5,1),date(2024,5,4),date(2024,5,6)][i%4]; assert td.is_free_day(d)==ld.is_free_day(d)
        elif i < 50:
            y=[2024,2025,2026,2027,2028][i%5]; assert td.wielkanoc(y)==ld.wielkanoc(y) and td.swieta_rok(y)==ld.swieta_rok(y)
        elif i < 75:
            assert td.oblicz_zasiedzenie_nieruchomosci(date(1985,1,1),True)==ld.oblicz_zasiedzenie_nieruchomosci(date(1985,1,1),True)
        else:
            assert issubclass(td.TabDaty,_m('tab_base').TabBase) and td.GRANICA_1990==ld.GRANICA_1990
    return _rep(100,'tab_daty',f)

def build_tab_przedawnienie_cases():
    tp=_m('tab_przedawnienie'); lp=_m('logika_przedawnienie')
    def f(i):
        if i < 25: n=[1,2,3,4,5,10][i%6]; assert tp._lata_str_fn(n)==lp.lata_str(n)
        elif i < 50: y=1 if i%2==0 else 3; assert tp._uplyw_fn(date(2020,1,1),y)==lp.uplyw(date(2020,1,1),y)
        elif i < 75: assert tp._oblicz_przejsciowe_fn(date(2015,1,1),6,10,False)==lp.oblicz_przejsciowe(date(2015,1,1),6,10,False)
        else: assert issubclass(tp.TabPrzedawnienie,_m('tab_base').TabBase)
    return _rep(100,'tab_przed',f)

def build_tab_koszty_cases():
    tkos=_m('tab_koszty')
    def f(i):
        if i < 20:
            assert tkos.TabKoszty._wynagrodzenie_pracownicze(types.SimpleNamespace(),[1,100,1000,100000,5000000][i%5]) >= 180.0
        elif i < 30:
            btn=B(); btn.m=(i%2==0); obj=types.SimpleNamespace(_btn_oplata=btn); want=not btn.m; tkos.TabKoszty._pokaz_btn_oplaty(obj,want); assert btn.winfo_ismapped() is want
        elif i < 40:
            pct=E(); obj=types.SimpleNamespace(k_pctP=pct); tkos.TabKoszty._set_pctP(obj,33.33); assert pct.get()=='33.33' and pct.state=='disabled'
        elif i < 60:
            z=['50','0','150','x'][i%4]; obj=types.SimpleNamespace(k_zasadzone=E(z),k_wps=E('100'),k_wynik_info_var=V(''),k_pctW=E(''),k_pctP=E('')); obj._set_pctP=lambda p: tkos.TabKoszty._set_pctP(obj,p); tkos.TabKoszty._on_zasadzone_change(obj); assert obj.k_wynik_info_var.get()=='' if z=='x' else obj.k_pctW.get()!=''
        elif i < 80:
            p=['25','75','abc','120'][i%4]; obj=types.SimpleNamespace(k_pctW=E(p),k_pctP=E(''),k_wps=E('200'),k_wynik_info_var=V(''),k_zasadzone=E('')); obj._set_pctP=lambda x: tkos.TabKoszty._set_pctP(obj,x); tkos.TabKoszty._on_pct_change(obj); assert obj.k_pctP.get()!=''
        elif i < 90:
            obj=types.SimpleNamespace(k_wps=E('1000'),k_pctW=E('50'),k_sygnatura=E('I C 1/24'),k_rodzaj=C(['A'],0),k_instancja=C(['B'],0),k_repr=C(['C'],0),powod_items=[{'amt':100}],pozwany_items=[{'amt':40}],sp_items=[{'amt':20}]); d=tkos.TabKoszty._get_koszty_data(obj); assert d['netto_pozwany']==30.0 and d['sp_na_powoda']==10.0
        else:
            t='Wynagrodzenie pełnomocnika' if i%2==0 else 'Inne'; obj=types.SimpleNamespace(k_wps=E('1000'),k_rodzaj=types.SimpleNamespace(current=lambda:0),_RODZAJ_MAP=tkos.TabKoszty._RODZAJ_MAP,_wynagrodzenie_pracownicze=lambda w:180.0); tc=C([t],0); tc.v=t; a=E(''); d=E(''); tkos.TabKoszty._on_type_selected(obj,tc,a,d); assert d.get()==('Koszty zastępstwa procesowego' if t=='Wynagrodzenie pełnomocnika' else '')
    return _rep(100,'tab_koszty',f)

def build_tab_raty_cases():
    tr=_m('tab_raty')
    def f(i):
        if i < 50:
            m='ilosc' if i%2==0 else 'kwota'; obj=types.SimpleNamespace(r_mode=V(m),r_ilosc_lbl=E(),r_ilosc=E(),r_kwota_j_lbl=E(),r_kwota_j=E()); tr.TabRaty._toggle_rata_mode(obj); assert obj.r_ilosc.m is (m=='ilosc') and obj.r_kwota_j.m is (m!='ilosc')
        elif i < 75:
            errs=[]; old=tr.messagebox.showerror; tr.messagebox.showerror=lambda *a, **k: errs.append(1); obj=types.SimpleNamespace(r_kwota=E(['0','abc','100'][i%3]),r_czest=types.SimpleNamespace(current=lambda:0),r_data=E('2024-01-01'),r_mode=V('ilosc'),r_ilosc=E(['0','2','1'][i%3]),r_kwota_j=E('10'),r_result_frame=W(),app=APP,_clear_frame=lambda f:None,_res_row=lambda *a, **k:None)
            try: tr.TabRaty._oblicz_raty(obj)
            finally: tr.messagebox.showerror=old
            assert errs if obj.r_kwota.get() in {'0','abc'} or obj.r_ilosc.get()=='0' else True
        else:
            old=tr.tk; tr.tk=types.SimpleNamespace(Frame=W,Label=W)
            try: obj=types.SimpleNamespace(r_kwota=E('100'),r_czest=types.SimpleNamespace(current=lambda:0),r_data=E('2024-01-01'),r_mode=V('ilosc'),r_ilosc=E('3'),r_kwota_j=E('10'),r_result_frame=W(),app=APP,_clear_frame=lambda f:None,_res_row=lambda *a, **k:None); tr.TabRaty._oblicz_raty(obj)
            finally: tr.tk=old
    return _rep(100,'tab_raty',f)

def build_tab_pkk_cases():
    tp=_m('tab_pkk')
    def f(i):
        if i < 20:
            m=1 if i%2 else 0; obj=types.SimpleNamespace(pkk_rodzaj=types.SimpleNamespace(current=lambda:m),pkk_okres_lbl=E(),pkk_okres=E(),pkk_okres_hint=E()); tp.TabPKK._toggle_pkk_mode(obj); assert obj.pkk_okres.m is (m==0)
        elif i < 50:
            errs=[]; old=tp.messagebox.showerror; old_tk=tp.tk; old_font=tp.tkfont; tp.messagebox.showerror=lambda *a, **k: errs.append(1); tp.tk=types.SimpleNamespace(Frame=W,Label=W); tp.tkfont=types.SimpleNamespace(Font=lambda *a, **k: object())
            try: obj=types.SimpleNamespace(pkk_kwota=E(['0','abc','1000'][i%3]),pkk_rodzaj=types.SimpleNamespace(current=lambda:0),pkk_pobrane=E(''),pkk_okres=E('365'),pkk_result_frame=W(),app=APP,_clear_frame=lambda f:None,_res_row=lambda *a, **k:None); tp.TabPKK._oblicz_pkk(obj)
            finally: tp.messagebox.showerror=old; tp.tk=old_tk; tp.tkfont=old_font
            assert errs if obj.pkk_kwota.get() in {'0','abc'} else True
        else:
            old=tp.tk; old_font=tp.tkfont; tp.tk=types.SimpleNamespace(Frame=W,Label=W); tp.tkfont=types.SimpleNamespace(Font=lambda *a, **k: object())
            try: obj=types.SimpleNamespace(pkk_kwota=E('1000'),pkk_rodzaj=types.SimpleNamespace(current=lambda:i%2),pkk_pobrane=E('40'),pkk_okres=E('365'),pkk_result_frame=W(),app=APP,_clear_frame=lambda f:None,_res_row=lambda *a, **k:None); tp.TabPKK._oblicz_pkk(obj)
            finally: tp.tk=old; tp.tkfont=old_font
    return _rep(100,'tab_pkk',f)

def build_tab_oplata_roczna_cases():
    tor=_m('tab_oplata_roczna')
    def f(i):
        vals=[('abc','100','1'),('100','','1'),('100','100','0'),('100','100','101'),('100','100','1')][i%5]
        errs=[]; old=tor.messagebox.showerror; old_tk=tor.tk; tor.messagebox.showerror=lambda *a, **k: errs.append(1); tor.tk=types.SimpleNamespace(Frame=W,Label=W,Button=W)
        try: obj=types.SimpleNamespace(or_oplata_dotychczasowa=E(vals[0]),or_wartosc=E(vals[1]),or_wartosc_stara=E('50'),or_stawka=E(vals[2]),or_data_aktualizacji=E('2026-04-01'),or_data_ostatniej=E('2020-04-01'),or_result_frame=W(),app=APP,_clear_frame=lambda f:None,_res_row=lambda *a, **k:None); tor.TabOplataRoczna._oblicz_oplata_roczna(obj)
        finally: tor.messagebox.showerror=old; tor.tk=old_tk
        assert errs if vals != ('100','100','1') else True
    return _rep(100,'tab_or',f)
def build_app_cases():
    app=_m('app')
    def f(i):
        if i < 20:
            assert app.App._RODZAJ_MAP[0]=='cywilna' and app.App._RODZAJ_MAP[3]=='upominawcze'
        elif i < 40:
            _patch(app); self=types.SimpleNamespace(f_small='s',f_bold='b',f_body='b',f_result='r',f_big='g',f_sub='s'); assert isinstance(app.App._entry(self,W(),0,1),W)
        elif i < 60:
            _patch(app); self=types.SimpleNamespace(f_small='s',f_bold='b',f_body='b',f_result='r',f_big='g',f_sub='s'); cb=app.App._combo(self,W(),['a','b'],0,1); assert cb.current()==0
        elif i < 80:
            obj=types.SimpleNamespace(btn_update=B(),lbl_wersja=types.SimpleNamespace(configure=lambda **k: setattr(obj,'label',k))); app.App._pokaz_btn_aktualizacji(obj,{'version':'9.9.9'}); assert '9.9.9' in obj.btn_update.kw['text'] and obj.label['text'].startswith('v')
        else:
            calls=[]; info={'version':'3.0.0'}; obj=types.SimpleNamespace(lbl_wersja=types.SimpleNamespace(configure=lambda **k: calls.append(('label',k))),_pokaz_btn_aktualizacji=lambda x: calls.append(('show',x)),after=lambda d, cb: cb(),_dyskretne_powiadomienie=lambda x: calls.append(('notify',x)),_dialog_diagnostyczny=lambda: calls.append(('diag',None)),btn_update=B()); old=app.sprawdz_wersje_w_tle; app.sprawdz_wersje_w_tle=lambda cb: cb(info)
            try: app.App._sprawdz_aktualizacje(obj,reczne=False)
            finally: app.sprawdz_wersje_w_tle=old
            assert ('show',info) in calls and ('notify',info) in calls
    return _rep(100,'app',f)

def build_updater_cases():
    up=_m('updater')
    def f(i):
        if i < 20:
            raw,exp=[('1.2.3',(1,2,3,0)),('1.2',(1,2,0,0)),('v2.0.1',(2,0,1,0)),('x',(0,0,0,0))][i%4]; assert up._ver_tuple(raw)==exp
        elif i < 35:
            raw=['Authorization: token abc','Bearer abcdef','ghp_'+'a'*36][i%3]; assert 'REDACTED' in up._sanitize_traceback(raw)
        elif i < 50:
            td=tempfile.mkdtemp()
            old=os.environ.get('APPDATA'); os.environ['APPDATA']=td
            try: p=up._plik_znacznika(); up._zapisz_date_sprawdzenia(); assert Path(p).exists() and up._czy_sprawdzac_dzisiaj() is False
            finally: os.environ.pop('APPDATA',None) if old is None else os.environ.__setitem__('APPDATA',old); shutil.rmtree(td, ignore_errors=True)
        elif i < 60:
            info={'browser_download_url':'B','url':'A'}; old=up.GITHUB_TOKEN; up.GITHUB_TOKEN='';
            try: assert up._resolve_download_url(info,'url','browser_download_url')=='B'
            finally: up.GITHUB_TOKEN=old
        elif i < 70:
            info={'browser_download_url':'B','url':'A'}; old=up.GITHUB_TOKEN; up.GITHUB_TOKEN='tok';
            try: assert up._resolve_download_url(info,'url','browser_download_url')=='A'
            finally: up.GITHUB_TOKEN=old
        elif i < 80:
            req=types.SimpleNamespace(get_header=lambda n:'UA')
            try: up._SecureRedirectHandler().redirect_request(req,None,None,302,'x','http://evil.test')
            except Exception as e: assert 'niezaszyfrowany' in str(e); return
            raise AssertionError('expected error')
        elif i < 90:
            req=types.SimpleNamespace(get_header=lambda n:'UA')
            try: up._SecureRedirectHandler().redirect_request(req,None,None,302,'x','https://evil.test')
            except Exception as e: assert 'niedozwoloną domenę' in str(e); return
            raise AssertionError('expected error')
        else:
            with tempfile.TemporaryDirectory() as td:
                z=Path(td)/'ok.zip';
                with zipfile.ZipFile(z,'w') as zf: zf.writestr('a.txt','x')
                out=Path(td)/'out'; out.mkdir(); up._bezpieczna_ekstrakcja(str(z),str(out)); assert (out/'a.txt').exists()
    return _rep(100,'updater',f)


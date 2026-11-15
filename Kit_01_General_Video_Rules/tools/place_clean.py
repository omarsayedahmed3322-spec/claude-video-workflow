# Put the flat logo on a clean frame: text lines parallel to the van's lower line (ANG), verticals vertical,
# lit by the paint. usage: place_clean.py in.png out.png cx cy ang screen_width vertical_extent [zoom.png]
# env: LOGO=<flat logo png> (default CLC flat logo), DARKCUT=<luma> keeps it off tyres/arches, HANDLE=cx,cy,rx,ry cuts round a door handle.
# Source: CLC R4 (2026-11-14), skill logo-on-object.
import cv2, numpy as np, math, sys
from PIL import Image
inp,out=sys.argv[1],sys.argv[2]; cx,cy,ANG,Wpx,V=map(float,sys.argv[3:8])
img=np.asarray(Image.open(inp).convert('RGB')).astype(np.float32)[...,::-1].copy()
H,W=img.shape[:2]
logo=np.asarray(Image.open(__import__('os').environ.get('LOGO', r'D:/Montage-02/Clients/AG1/CLC/Master Assets/لوجو CLC الرشد - فلات نضيف.png')).convert('RGBA')).astype(np.float32)[...,[2,1,0,3]]
a=math.radians(ANG); Wu=Wpx/math.cos(a); Hv=math.sqrt(max(1,V**2-(Wu*math.sin(a))**2))
N=int(max(Wu,Hv)*1.5); logo=cv2.resize(logo,(N,N),interpolation=cv2.INTER_AREA)
A=np.array([[Wu*math.cos(a)/N,0],[Wu*math.sin(a)/N,Hv/N]]); t=np.array([cx,cy])-A@np.array([N/2,N/2])
wl=cv2.warpAffine(logo,np.hstack([A,t[:,None]]),(W,H),flags=cv2.INTER_CUBIC,borderValue=(0,0,0,0))
al=(wl[...,3]/255.0)[...,None]
import os
if os.environ.get('DARKCUT'):
    lum0=cv2.cvtColor(img.clip(0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)
    al=al*cv2.GaussianBlur((lum0>float(os.environ['DARKCUT'])).astype(np.float32),(0,0),1.2)[...,None]
if os.environ.get('HANDLE'):
    hx,hy,hrx,hry=map(float,os.environ['HANDLE'].split(','))
    hm=np.zeros((H,W),np.float32); cv2.ellipse(hm,(int(hx),int(hy)),(int(hrx),int(hry)),0,0,360,1,-1)
    al=al*(1-cv2.GaussianBlur(hm,(0,0),1.5)[...,None])
area=al[...,0]>0.5; ref=np.percentile(img[area],92,axis=0)
shade=((img/ref).clip(0.3,1.15))**0.6
col=cv2.GaussianBlur(wl[...,:3]*shade,(0,0),0.35)+np.random.default_rng(1).normal(0,1.2,(H,W,1)).astype(np.float32)
res=(img*(1-al)+col*al).clip(0,255).astype(np.uint8)
Image.fromarray(res[...,::-1]).save(out)
if len(sys.argv)>8:
    Image.fromarray(res[...,::-1]).resize((W//2,H//2)).save(sys.argv[8])
print('Wu %.0f Hv %.0f'%(Wu,Hv))

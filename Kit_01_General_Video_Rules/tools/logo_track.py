# Put the flat logo on a clean clip, tracked to the van (affine ECC on the van body), sheared like place_clean,
# lit by the paint, hidden behind anything that passes in front (difference from the tracked frame 0).
# LOGO=<flat logo png> overrides the default (CLC flat logo). Source: CLC R4 (2026-11-14), skill logo-on-object.
# usage: logo_track.py in.mp4 out.mp4 cx cy ang screen_w vertical_extent  x0 y0 x1 y1(van track box on frame 0)
import cv2, numpy as np, math, sys, subprocess
from PIL import Image
src,dst=sys.argv[1],sys.argv[2]; cx,cy,ANG,Wpx,V=map(float,sys.argv[3:8]); bx0,by0,bx1,by1=map(int,sys.argv[8:12])
cap=cv2.VideoCapture(src); fr=[]
while True:
    ok,f=cap.read()
    if not ok: break
    fr.append(f)
H,W=fr[0].shape[:2]
logo=np.asarray(Image.open(__import__('os').environ.get('LOGO', r'D:/Montage-02/Clients/AG1/CLC/Master Assets/لوجو CLC الرشد - فلات نضيف.png')).convert('RGBA')).astype(np.float32)[...,[2,1,0,3]]
a=math.radians(ANG); Wu=Wpx/math.cos(a); Hv=math.sqrt(max(1,V**2-(Wu*math.sin(a))**2))
N=int(max(Wu,Hv)*2); logo=cv2.resize(logo,(N,N),interpolation=cv2.INTER_AREA)
A=np.array([[Wu*math.cos(a)/N,0],[Wu*math.sin(a)/N,Hv/N]]); t=np.array([cx,cy])-A@np.array([N/2,N/2])
L0=cv2.warpAffine(logo,np.hstack([A,t[:,None]]),(W,H),flags=cv2.INTER_CUBIC,borderValue=(0,0,0,0))
gray=lambda im: cv2.GaussianBlur(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32),(0,0),1.2)
g0=gray(fr[0]); m=np.zeros((H,W),np.uint8); m[by0:by1,bx0:bx1]=255
crit=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,100,1e-5)
w=np.eye(2,3,dtype=np.float32)
p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','%dx%d'%(W,H),'-r','24','-i','-','-c:v','libx264','-crf','14','-pix_fmt','yuv420p',dst],stdin=subprocess.PIPE)
rng=np.random.default_rng(3)
for i,f in enumerate(fr):
    if i:
        try: _,w=cv2.findTransformECC(g0,gray(f),w,cv2.MOTION_AFFINE,crit,m,5)
        except cv2.error: pass
    Li=cv2.warpAffine(L0,w,(W,H),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
    ref=cv2.warpAffine(fr[0],w,(W,H),flags=cv2.INTER_LINEAR)
    al=Li[...,3]/255.0
    diff=np.abs(f.astype(np.float32)-ref.astype(np.float32)).mean(2)
    occ=cv2.GaussianBlur((diff>28).astype(np.float32),(0,0),2)
    al=(al*(1-np.clip(occ*1.5,0,1)))[...,None]
    img=f.astype(np.float32); area=al[...,0]>0.5
    rf=np.percentile(img[area],92,axis=0) if area.sum()>50 else np.array([230,230,230],np.float32)
    shade=((img/rf).clip(0.3,1.15))**0.6
    col=cv2.GaussianBlur(Li[...,:3]*shade,(0,0),0.5)+rng.normal(0,1.5,(H,W,1)).astype(np.float32)
    out=(img*(1-al)+col*al).clip(0,255).astype(np.uint8)
    p.stdin.write(out.tobytes())
    if i%40==0: print('frame',i,'move %.1f,%.1f zoom %.3f'%(w[0,2],w[1,2],math.sqrt(abs(np.linalg.det(w[:,:2])))))
p.stdin.close(); p.wait(); print('wrote',dst)

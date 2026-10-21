"""Overview figure for the summary report (values copied from results/t{1,2,3} tables)."""
import matplotlib as mpl, matplotlib.pyplot as plt, numpy as np
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = ("#2a78d6","#eb6834","#1baf7a","#eda100","#e87ba4","#008300","#4a3aa7","#e34948")
GRAY="#898781"; INK2="#52514e"
mpl.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Helvetica","Arial","DejaVu Sans"],"font.size":8.5,
  "axes.edgecolor":"#c3c2b7","axes.labelcolor":INK2,"xtick.color":GRAY,"ytick.color":GRAY,"xtick.labelcolor":INK2,"ytick.labelcolor":INK2,
  "axes.grid":True,"grid.color":"#e1e0d9","grid.linewidth":0.6,"axes.spines.top":False,"axes.spines.right":False,"axes.axisbelow":True,
  "legend.frameon":False,"legend.fontsize":7.5,"pdf.fonttype":42,"savefig.bbox":"tight"})
fig,ax=plt.subplots(1,3,figsize=(10.2,3.0),gridspec_kw={"width_ratios":[1.15,1,1.15]})
# (a) T1 persistent state, alpha=0.05
a=ax[0]; groups=["history-free\n(current PR only)","history-aware\n(all prior diffs)"]
vals={"max":[0.16,0.24],"top-3 sum":[0.31,0.16],"Shiryaev–Roberts":[0.33,0.22]}
cols=[GRAY,BLUE,ORANGE]; x=np.arange(2); w=0.26
for i,(k,v) in enumerate(vals.items()):
    a.bar(x+(i-1)*w,v,w*0.92,color=cols[i],label=k)
    for xi,vi in zip(x+(i-1)*w,v): a.text(xi,vi+0.008,f"{vi:.2f}",ha="center",fontsize=7,color=INK2)
a.set_xticks(x,groups); a.set_ylabel("TPR at 5% trajectory FPR"); a.set_ylim(0,0.42); a.legend(loc="upper right")
a.set_title("(a) Idea 1: cross-session accumulation\n(gradual attacks, 5 PRs, GPT-4o PR monitor)",loc="left",fontsize=8.5)
# (b) T2 selection safety at B=1% (7 settings)
b=ax[1]; rules=["global","CFAR","max-detect","Stackelberg"]; v=[0.645,0.404,0.641,0.791]
lo=[0.531,0.179,0.474,0.689]; hi=[0.703,0.561,0.863,0.890]; c=[GRAY,RED,BLUE,AQUA]
yerr=np.array([np.array(v)-np.array(lo),np.array(hi)-np.array(v)])
b.bar(range(4),v,0.6,color=c,yerr=yerr,capsize=3,error_kw=dict(ecolor=INK2,lw=0.8))
for i,vi in enumerate(v): b.text(i,0.03,f"{vi:.2f}",ha="center",fontsize=7.5,color="white",fontweight="bold")
b.set_xticks(range(4),rules); b.set_ylim(0,1); b.set_ylabel("safety vs context-selecting attacker")
b.set_title("(b) Idea 2: per-context thresholds\n(7 deployments, audit budget 1%)",loc="left",fontsize=8.5)
# (c) T3 undetected success, full monitor adaptive alpha=0.01
c3=ax[2]; dets=["max","CUSUM","e-process","multi-chart"]
rows={"original (no rewrite)":[0.86,0.96,0.92,0.85],"max-aware":[0.69,0.74,0.47,0.49],"CUSUM-aware":[0.63,0.86,0.70,0.58],"multichart-aware":[0.73,0.81,0.66,0.68]}
cc=[GRAY,BLUE,ORANGE,AQUA]; x=np.arange(4); w=0.2
for i,(k,vv) in enumerate(rows.items()): c3.bar(x+(i-1.5)*w,vv,w*0.92,color=cc[i],label=k)
c3.set_xticks(x,dets); c3.set_ylim(0,1.15); c3.set_ylabel("undetected-success rate (1% FPR)"); c3.legend(loc="upper center",ncol=2,fontsize=7)
c3.set_title("(c) Idea 3: detector-aware attacker\n(gpt-4.1-mini monitor; lower = better defense)",loc="left",fontsize=8.5)
fig.tight_layout(); fig.savefig("figs/overview.pdf"); print("ok")

"""Two-panel scientific plot from published aggregate query/curve data."""
import csv
import json
import os
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    queries=json.loads((ROOT/'evidence/revision-v7/M1/queries.json').read_text())
    finite=[r for r in queries if r['models']['N']['strict_priority_certified'] and r['models']['N']['reversal_radius'] is not None]
    curves=list(csv.DictReader((ROOT/'evidence/v9/cumulative-loss-curves.csv').open()))
    plt.rcParams.update({'font.size':8,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(2,1,figsize=(3.45,3.75),gridspec_kw={'height_ratios':[1,1.15]})
    ax=axs[0]
    ax.scatter([r['models']['N']['range'][0] for r in finite],[r['models']['N']['reversal_radius'] for r in finite],s=22,color='#46708a',zorder=3)
    for r in finite:
        if r['query'] in (2,8):
            x=r['models']['N']['range'][0];y=r['models']['N']['reversal_radius']
            ax.annotate('q%02d: (%d, %d)'%(r['query'],x,y),(x,y),xytext=(5,4),textcoords='offset points',fontsize=7)
    ax.set(xlabel='Certified joint lower margin',ylabel='Minimum withdrawals',xlim=(-3,85),ylim=(0,21))
    ax.set_yticks([1,5,10,15,20]);ax.grid(axis='y',color='#dddddd',linewidth=.5)
    ax.set_title('(a) All nine finite M1 N queries',loc='left',fontsize=8,pad=5)
    ax=axs[1]
    for q,color,style in [(2,'#35688c','-'),(8,'#a4512b','--')]:
        rows=[r for r in curves if int(r['query'])==q]
        xs=[int(r['withdrawals']) for r in rows];ys=[int(r['residual_minimum']) for r in rows]
        ax.plot(xs,ys,style,color=color,label='q%02d'%q,linewidth=1.6)
        first=next(i for i,v in enumerate(ys) if v<0)
        ax.scatter([xs[first]],[ys[first]],s=27,facecolors='white',edgecolors=color,zorder=4)
        ax.annotate('m=%d'%xs[first],(xs[first],ys[first]),xytext=(3,6 if q==2 else -12),textcoords='offset points',color=color,fontsize=7)
    ax.axhline(0,color='#666666',linewidth=.7)
    ax.set(xlabel='Cases with ordering constraints withdrawn',ylabel='Worst-case joint margin',xlim=(0,20),ylim=(-40,40))
    ax.set_xticks([0,4,8,12,14,16,20]);ax.grid(axis='y',color='#dddddd',linewidth=.5)
    ax.legend(loc='lower left',ncol=2,frameon=False,fontsize=7)
    ax.set_title('(b) Concentrated versus dispersed case losses',loc='left',fontsize=8,pad=5)
    fig.tight_layout(pad=.45,h_pad=.9)
    dest=ROOT/'paper/figures/margin_dependence_v9'
    dest.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(str(dest)+'.png',dpi=350);fig.savefig(str(dest)+'.svg');plt.close(fig)
    image=ROOT/'paper/cscwd-latex/images/margin_dependence_v9.png';image.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(str(dest)+'.png',image)


if __name__=='__main__':main()

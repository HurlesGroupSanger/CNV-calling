#!/usr/bin/env python3
#
#   cat x-y.txt   | mplot xy -o img.png +type xy
#   cat y.txt     | mplot xy -o img.png +type y
#   cat x.txt     | mplot xy -o img.png +type density
#   cat x-y-y0-y1 | mplot xy -o img.png +type xyci       # confidence intervals
#   cat x-y-s     | mplot xy -o img.png +type xys        # combine with scatter plot, s is the size
#   cat x-y-c     | mplot xy -o img.png +type xyc        # combine with scatter plot, c is color
#   cat x-y-sc    | mplot xy -o img.png +type xysc       # combine with scatter plot, s is the size to be displayed as color
#   cat x-y-y     | mplot xy -o img.png +type xyy        # twinx graphs
#   cat x-y-m-M   | mplot xy -o img.png +type xymM       # fill area between (m,M) and draw a line y
#   cat x-m-M-y   | mplot xy -o img.png +type xmMy       # fill area between (m,M) and draw lines y1,y2,...
#
#   +type xyci: confidence intervals
#       echo -e '1 1 0.9 1.05\n2 0.5 0.44 0.7\n3 0.3 0.1 0.35' | mplot xy -F -o rmme.png +type xyci
#
#   +type xymM: fill area in between
#       echo -e '0 1 0.5 1.5\n1 1 0.5 1.5' | mplot xy -F -o rmme.png +type xymM +mMa 'fc="green",ec="blue"' +cl red
#
#   +line '0,0,1,1;color=red;lw=2;ls=:'
#   +fill 0     # baseline
#   +xt -       # switch off xticks
#   +xti 1      # force integer xticks
#   +mMa fc=green,ec=blue
#   +lb label   # "-" to suppress one when plotting multiple files
#   +lga ncol=2     # legend in two columns
#   +lgp size=6     # extra small legend font
#   +lgb 0,1.25     # move legend up outside the plotting area
#   +ann 0.5,0.5:text   # place text (axes fraction coordinates)
#   +exec file.py       # any piece of code, e.g. ax1.add_patch(Rectangle((0,0),1,2,fill=True,facecolor="#ccc"))
#
# CMDLINE

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import itertools
import csv,sys
import numpy
import random
csv.register_dialect('tab', delimiter='\t', quoting=csv.QUOTE_NONE)

style = 'mine'      # xkcd, ggplot, ...
# sty: 'style'
if style=='xkcd':
    plt.xkcd()
elif style!=None and style!='mine':
    plt.style.use(style)

def smooth_data(x,window_len=11,window='hanning'):
    if x.ndim != 1: raise Exception("smooth only accepts 1 dimension arrays.")
    if x.size < window_len: raise Exception("Input vector needs to be bigger than window size.")
    if window_len<3: return x
    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']: raise Exception("Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'")
    s = numpy.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
    if window == 'flat': # moving average
        w = numpy.ones(window_len,'d')
    else:
        w = eval('numpy.'+window+'(window_len)')
    y = numpy.convolve(w/w.sum(),s,mode='valid')
    odd = 0
    if window_len%2: odd = 1
    y = y[(int(window_len/2)-1):-(int(window_len/2)+odd)]
    return y

def bignum(num):
    s = str(num); out = ''; slen = len(s)
    for i in range(slen):
        out += s[i]
        if i+1<slen and (slen-i-1)%3==0: out += ','
    return out

files  = []
# FILES

type = 'xy'
# type: 'type'


# Alternative colors can be given as pre-defined colors or explicitly
#   +cl 'default'   (same as +cl '#337ab7,#f0ad4e,#5cb85c,#5bc0de,#d9534f,grey,black')
#   +cl 'sanger'
#   +cl '#01579B,#FD8230,#1B5E20,#039BE5,#9C2222,grey,black'
#
colors = None
# cl: 'colors'
if colors==None or colors=='default': colors = '#337ab7,#f0ad4e,#5cb85c,#5bc0de,#d9534f,grey,black'
elif colors=='sanger': colors = '#01579B,#FD8230,#1B5E20,#039BE5,#9C2222,grey,black'
colors = colors.split(',')

jitter = (0,0)
# jr: jitter

(xmin,xmax) = (None,None)
xlim = None         # +xr 1,10    +xr 1,    +xr ,10
# xr: 'xlim'
if xlim!=None:
    x = xlim.split(',')
    xlim = {}
    if x[0]!='': xmin = float(x[0]); xlim['left']  = xmin
    if x[1]!='': xmax = float(x[1]); xlim['right'] = xmax

# This should rescale y-axis when x is trimmed; suggested by ai, not tested
#   ax.relim()
#   ax.autoscale_view(scaley=True, scalex=False)

xdat  = []
ydat  = []
ydat2 = []
yerr  = []
sdat  = []
cdat  = []
ffdat = []
mmdat = []
for i in range(len(files)):
    xdat.append([])
    ydat.append([])
    if type=='xyci': yerr.append([[],[]])
    if type=='xys' or type=='xysc': sdat.append([])
    if type=='xyy': ydat2.append([])
    if type=='xyc': cdat.append([])
    if type=='xymM': ffdat.append([])
    if type=='xmMy': mmdat.append([])
    fname = files[i]
    with open(fname, 'r') as f:
        reader = csv.reader(f, 'tab')
        tmp = []
        for row in reader:
            if row[0][0] == '#': continue
            xval = None
            yval = None
            sval = None
            if type=='xy' or type=='xyc':
                xval = float(row[0])
                yval = float(row[1])
            elif type=='y':
                xval = len(tmp)
                yval = float(row[0])
            elif type=='density':
                xval = float(row[0])
                yval = 0
            elif type=='xyci':
                xval = float(row[0])
                yval = float(row[1])
                yerr[i][0].append(yval-float(row[2]))
                yerr[i][1].append(float(row[3])-yval)
            elif type=='xys' or type=='xysc' or type=='xyy':
                xval = float(row[0])
                yval = float(row[1])
                sval = float(row[2])
            elif type=='xymM':
                tmp.append([float(row[0]),float(row[1]),float(row[2]),float(row[3])])
                continue
            elif type=='xmMy':
                mmdat[i].append(row)
                continue
            if xmin!=None and xmin>xval: continue
            if xmax!=None and xmax<xval: continue
            if jitter[0]!=0: xval = xval + random.random()*jitter[0] - 0.5*jitter[0]
            if jitter[1]!=0: yval = yval + random.random()*jitter[1] - 0.5*jitter[1]
            if type=='xys' or type=='xysc' or type=='xyy': tmp.append([xval,yval,sval])
            elif type=='xyc': tmp.append([xval,yval,row[2]])
            else: tmp.append([xval,yval])
        xdat[i] = [float(x[0]) for x in tmp]
        ydat[i] = [float(x[1]) for x in tmp]
        if type=='xys' or type=='xysc': sdat[i] = [float(x[2]) for x in tmp]
        if type=='xyc': cdat[i] = [x[2] for x in tmp]
        if type=='xyy': ydat2[i] = [float(x[2]) for x in tmp]
        if type=='xymM': ffdat[i] = [[x[2] for x in tmp],[x[3] for x in tmp]]
        if type=='xyymM':
            ydat2[i] = [float(x[2]) for x in tmp];
            ffdat[i] = [[x[3] for x in tmp],[x[4] for x in tmp]]

if type=='density':
    from scipy.stats import gaussian_kde
    if xmin==None:
        for xarr in xdat:
            if xmin==None:
                xmin = xarr[0]
                xmax = xarr[0]
            for xval in xarr:
                if xmin>xval: xmin = xval
                if xmax<xval: xmax = xval
    for i in range(len(xdat)):
        density = gaussian_kde(xdat[i])
        xs = numpy.linspace(xmin,xmax)
        density.covariance_factor = lambda : .25
        density._compute_covariance()
        xdat[i] = xs
        ydat[i] = density(xs)

norm = None         # +norm max=1, sum=1, dnsity=1, by=1093
# norm: 'norm'
if norm!=None:
    x=norm.split('=')
    if x[0]=='max':
        for i in range(len(files)):
            max = float(ydat[i][0])
            for y in ydat[i]:
                if float(max)<float(y): max = float(y)
            for j in range(len(ydat[i])):
                ydat[i][j] = float(x[1])*float(ydat[i][j])/max
    elif x[0]=='by':
        for i in range(len(files)):
            for j in range(len(ydat[i])):
                ydat[i][j] = float(ydat[i][j])/float(x[1])
    elif x[0]=='sum':
        for i in range(len(files)):
            sum = 0
            for y in ydat[i]: sum += float(y)
            for j in range(len(ydat[i])):
                ydat[i][j] = float(x[1])*float(ydat[i][j])/sum
    elif x[0]=='dnsity':
        for i in range(len(files)):
            sum = 0
            for y in ydat[i]: sum += float(y)
            ynew = []
            for j in range(len(ydat[i])):
                xdist = xdat[i][j]
                if j+1<len(ydat[i]): xdist = xdat[i][j+1] - xdat[i][j]
                ynew.append(float(x[1])*float(ydat[i][j])/sum/xdist)
            ydat[i] = ynew


fill = None         # +fill 0   (baseline)
# fill: fill

yscale = None       # +ys log,symlog
# ys: 'yscale'

xscale = None       # +xs log,symlog
# xs: 'xscale'

# # There is a bug in some versions of matplotlib: even values outside
# # set_xlim are plotted. Therefore we need to trim manually.
# if xlim!=None:
#     for i in range(len(files)):
#         jmin = -1
#         jmax = len(xdat[i])
#         xdat[i],ydat[i] = zip(*sorted(zip(xdat[i],ydat[i])))
#         for j in range(len(xdat[i])):
#             if j>0 and xdat[i][j-1] > xdat[i][j]: print("The data needs to be sorted by x with +xr"); sys.exit()
#             if 'left'  in xlim and xdat[i][j]<xlim['left']  and (jmin==-1 or xdat[i][jmin] < xdat[i][j]): jmin = j
#             if 'right' in xlim and xdat[i][j]>xlim['right'] and (jmax==len(xdat[i]) or xdat[i][jmax] > xdat[i][j]): jmax = j
#         if jmax<len(xdat[i]):
#             xdat[i] = xdat[i][:jmax]
#             ydat[i] = ydat[i][:jmax]
#         if jmin>=0:
#             xdat[i] = xdat[i][jmin+1:]
#             ydat[i] = ydat[i][jmin+1:]

wh = (7,5)
if style=='mine': wh = (5,3.5)
# wh: wh
fig, ax1 = plt.subplots(1, 1, figsize=wh)

ax2 = None
if type=='xyy': ax2 = ax1.twinx()

#try:
#    mpl.rcParams['axes.prop_cycle'] = mpl.cycler(color=colors)
#except:
#    # deprecated: mpl.rcParams['axes.color_cycle'] = colors
#finally:
#    print('mpl.rcParams changed, no axes.prop_cycle or axes.color_cycle')
ax1.set_prop_cycle('color', colors)
if ax2!=None: ax2.set_prop_cycle('color', colors)



asp = None  # +asp 1
# asp: asp
if asp != None: ax1.set_aspect(asp, adjustable='box')

plt_args = [{}]       # for example: +pa "mec='grey',mfc='grey',zorder=100,clip_on=False,alpha=0.5"
if style=='mine': plt_args = [{'zorder':100,'clip_on':False}]
# pa: [{plt_args}]

mM_args = dict({'facecolor':'#ffeacc','edgecolor':'#ffe0b2'}) # for example: +mMa 'fc="red",ec="blue"'
# mMa: {mM_args}

lines = None         # +line '0,0,1,1;color=red;lw=2;ls=:;marker=o;ms=10'  (can be given multiple times)
# line: ['lines']
if lines!=None:
    prev = None
    for line in lines:
        if line==prev: continue
        prev = line
        tmp = line.split(';')
        lin = tmp[0].split(',')
        tmp_args = {}
        for x in tmp[1:]:
            a,b = x.split('=')
            try:
                tmp_args[a] = float(b)
            except:
                if b=='False': tmp_args[a] = False
                elif b=='True': tmp_args[a] = True
                else: tmp_args[a] = b
        ax1.plot([float(lin[0]),float(lin[2])],[float(lin[1]),float(lin[3])],**tmp_args)

smooth = None
# smooth: smooth
lb = []
# lb: ['lb']
lt = []             # line types:   +lt --
# lt: ['lt']
lc = []             # line colors:  +lc '#337ab7'
# lc: ['lc']
for i in range(len(files)):
    line = '-'
    if type=='xyci': line = 'o'
    if i < len(lt): line = lt[i]
    label = ''
    if i <len(lb): label = lb[i]
    if label=='-': label=''
    if smooth!=None:
        ydat[i] = smooth_data(numpy.array(ydat[i],dtype=numpy.float64),smooth,'hanning')
    args = plt_args[-1]
    if i in plt_args: args = plt_args[i]
    if i < len(lc): args['color'] = lc[i]
    if type=='xyc':
        tmp_args = {**args,'zorder':110}
        sc = ax1.scatter(xdat[i],ydat[i],c=cdat[i],**tmp_args)
        continue
    if type=='xymM':
        if len(lb):
            if len(lb[i])>1: mM_args['label'] = lb[0]
            label = lb[1]
        ax1.fill_between(xdat[i],ffdat[i][0],ffdat[i][1],**mM_args)
    if type=='xmMy':
        if len(lb):  mM_args['label'] = lb[0]
        ax1.fill_between([float(x[0]) for x in mmdat[i]],[float(x[1]) for x in mmdat[i]],[float(x[2]) for x in mmdat[i]],**mM_args)
        for j in range(3, len(mmdat[i][0])):
            if len(lb)>=j-2: args['label'] = lb[j-2]
            ax1.plot([float(x[0]) for x in mmdat[i]],[float(x[j]) for x in mmdat[i]],**args)
        continue
    if type=='xyci':
        ax1.errorbar(xdat[i],ydat[i],fmt=line,yerr=yerr[i],label=label,**args)
    else:
        ax1.plot(xdat[i],ydat[i],line,label=label,**args)
        if fill!=None:
            ax1.fill_between(xdat[i],ydat[i],fill,**args)
    if type=='xys':
        ax1.scatter(xdat[i],ydat[i],sdat[i],**args)
    if type=='xysc':
        tmp_args = {**args,'zorder':110}
        #tmp_args = {**args,'zorder':110,'cmap':'magma'}
        sc = ax1.scatter(xdat[i],ydat[i],c=sdat[i],**tmp_args)
    if type=='xyy':
        args['linestyle'] = ':'
        ax2.plot(xdat[i],ydat2[i],**args)

if type=='xysc':
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    div1 = make_axes_locatable(ax1)
    cb = plt.colorbar(sc, shrink=0.4,format='%.0e') #.set_label('Number')
    for t in cb.ax.get_yticklabels(): t.set_fontsize(7)

xsci  = None
ysci  = None
ysci2 = None
# xsci:  (xsci)
# ysci:  (ysci)
# ysci2: (ysci2)
if xsci!=None: ax1.ticklabel_format(style='sci', scilimits=xsci, axis='x')        # +xsci -2,2
if ysci!=None: ax1.ticklabel_format(style='sci', scilimits=ysci, axis='y')
if ysci2!=None and ax2!=None: ax2.ticklabel_format(style='sci', scilimits=ysci2, axis='y')

ann = None
# ann: ['ann']
if ann!=None:
    for x in ann:
        (coor,txt) = x.split(':')
        (cx,cy) = coor.split(',')
        ax1.annotate(txt,xy=(float(cx),float(cy)),xycoords='axes fraction')


yt = None       # yticks: +yt 1,2,3
# yt: 'yt'
if yt!=None:
    if yt=="-":
        ax1.set_yticks([])
    else:
        tmp = yt.split(',')
        ax1.set_yticks([float(x) for x in tmp])

xt = None       # xticks: +xt 1,2,3
# xt: 'xt'
if xt!=None:
    if xt=="-":
        ax1.set_xticks([])
    else:
        tmp = xt.split(',')
        ax1.set_xticks([float(x) for x in tmp])

xti = 0
# xti: xti
if xti!=0:
    ax1.xaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True))

xlab_args = {}      # for example: +xarg "rotation=45,ha='right',ma='left',fontsize=9"
# xarg: {xlab_args}

xtl = None      # xticklabels: +xtl 'label 1;label 2'
# xtl: 'xtl'
if xtl!=None:
    #ax1.get_xaxis().set_tick_params(direction='out')
    ax1.xaxis.set_ticks_position('bottom')
    ax1.set_xticklabels(xtl.split(';'), **xlab_args)

grid = None     # +gr '#eeeeee,1,--'    # color,linewidth,linestyle
# gr: 'grid'
if grid!=None:
    grid = grid.split(',')
    ax1.grid(color=grid[0], linewidth=float(grid[1]), linestyle=grid[2])

if xlim!=None: ax1.set_xlim(**xlim)

ylim = None
# yr: 'ylim'
if ylim!=None:                          # for example: +yr 0,1.1%    +yr 0,
    (ymin,ymax) = ylim.split(',')
    if ymin[-1] == '%':
        ymin = float(ymin[0:-1])*min(min(ydat))
    if ymax!='' and ymax[-1] == '%':
        ymax = float(ymax[0:-1])*float(max(max(ydat)))
    ylim = {}
    if ymin!='': ylim['bottom'] = float(ymin)
    if ymax!='': ylim['top'] = float(ymax)
    ax1.set_ylim(**ylim)

ylabel = None
# yl: 'ylabel'
if ylabel!=None: ax1.set_ylabel(ylabel,labelpad=10)

ylabel2 = None
# yl2: 'ylabel2'
if ylabel2!=None and ax2!=None: ax2.set_ylabel(ylabel2,labelpad=10)

xlabel = None
# xl: 'xlabel'
if xlabel!=None: ax1.set_xlabel(xlabel,labelpad=10)

if yscale!=None: ax1.set_yscale(yscale)     # log, symlog
if xscale!=None: ax1.set_xscale(xscale)     # log, symlog

args = {}
if style=='ggplot':
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.get_xaxis().tick_bottom()
    ax1.get_yaxis().tick_left()
    ax1.spines['bottom'].set_color('grey')
    ax1.spines['left'].set_color('grey')
    mpl.rcParams['text.color'] = '555555'
    args = {'color':'#555555'}
if style=='mine':
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.get_xaxis().tick_bottom()
    ax1.get_yaxis().tick_left()
    ax1.spines['bottom'].set_color('grey')
    ax1.spines['left'].set_color('grey')
    mpl.rcParams['text.color'] = '555555'
    ax1.patch.set_visible(False)
    if ax2!=None:
        ax2.spines['top'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        ax2.get_xaxis().tick_bottom()
        ax2.get_yaxis().tick_right()
        ax2.spines['bottom'].set_color('grey')
        ax2.spines['right'].set_color('grey')
        ax2.patch.set_visible(False)

ta_args = {}        #  +ta t=1.0
# ta: {ta_args}
ta_args = {**args,**ta_args}
title = None
# title: 'title'
if title!=None: ax1.set_title(title,**ta_args)

lg_prop = {'size':10}   # +lgp 'size=9'
# lgp: {lg_prop}

lg_bbox = None          # +lgb 0,1.25   # move legend up outside the plotting area
# lgb: (lg_bbox)

lg_args = {}            # +lga 'title="Quality Decile",alignment="right"'
# lga: {lg_args}
if lg_bbox!=None: lg_args['bbox_to_anchor'] = lg_bbox
lg_args = dict({'numpoints':1,'markerscale':1,'loc':'best','prop':{**lg_prop},'frameon':False},**lg_args)

if len(lb)>0: plt.legend(**lg_args)

fname = None
# exec: 'fname'
if fname!=None:
    with open(fname, 'r') as file:
        str = file.read()
        exec(str)

rect = None
# rect: rect
if rect!=None:
    import matplotlib.patches as patches
    y0,y1 = ax1.get_ylim()
    width = rect[1]-rect[0]
    xy = [rect[0],y0]
    height = y1-y0
    rect = patches.Rectangle(xy, width, height, color='#F2DEDE',zorder=-100)
    ax1.add_patch(rect)

adjust = None
# adj: {adjust}
if adjust!=None: plt.subplots_adjust(**adjust)        # for example: bottom=0.2,left=0.1,right=0.95

# dpi: dpi

# SAVE
plt.close()


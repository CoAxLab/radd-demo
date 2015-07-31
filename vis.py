#!/usr/local/bin/env python
from __future__ import division
import os
import pandas as pd
import numpy as np
from scipy import optimize
import matplotlib.pyplot as plt
import seaborn as sns
from radd import utils
from scipy.stats.mstats import mquantiles as mq

sns.set(font='Helvetica')
sns.set(style='ticks', rc={'text.color': 'black', 'axes.labelcolor': 'black', 'figure.facecolor': 'white'})


rpal = lambda nc: sns.blend_palette(['#e88379', '#c0392b'], n_colors=nc)
bpal = lambda nc: sns.blend_palette(['#81aedb', '#4168B7'], n_colors=nc)
gpal = lambda nc: sns.blend_palette(['#65b88f', '#16a085'], n_colors=nc)
ppal = lambda nc: sns.blend_palette(['#848bb6', '#674172'], n_colors=nc)


def scurves(lines=[], kind='pro', yerr=[], pstop=.5, ax=None, linestyles=None, colors=None, markers=False, labels=None):

      if len(lines[0])==6:
                kind=='pro'

      if ax is None:
            f, ax = plt.subplots(1, figsize=(6,5))
      if colors is None:
            colors=sns.color_palette('husl', n_colors=len(lines))
      if labels is None:
            labels=['']*len(lines)
      if linestyles is None:
            linestyles = ['-']*len(lines)

      lines=[np.array(line) if type(line)==list else line for line in lines]
      pse=[];

      if kind=='radd':
            x=np.array([400, 350, 300, 250, 200], dtype='float')
            xtls=x.copy()[::-1]; xsim=np.linspace(15, 50, 10000);
            yylabel='P(Stop)'; scale_factor=100; xxlabel='SSD'; xxlim=(18,42)
      else:
            x=np.array([100, 80, 60, 40, 20, 0], dtype='float')
            xtls=x.copy()[::-1]; xsim=np.linspace(-5, 11, 10000); xxlim=(-1, 10.5)
            yylabel='P(NoGo)'; scale_factor=100; xxlabel='P(Go)';

      x=utils.res(-x, lower=x[-1]/10, upper=x[0]/10)
      for i, yi in enumerate(lines):

            y=utils.res(yi, lower=yi[-1], upper=yi[0])
            p_guess=(np.mean(x),np.mean(y),.5,.5)
            p, cov, infodict, mesg, ier = optimize.leastsq(utils.residuals, p_guess, args=(x,y), full_output=1, maxfev=5000, ftol=1.e-20)
            x0,y0,c,k=p
            xp = xsim
            pxp=utils.sigmoid(p,xp)
            idx = (np.abs(pxp - pstop)).argmin()

            pse.append(xp[idx]/scale_factor)

            # Plot the results
            if yerr!=[]:
                  #ax.errorbar(x, y[i], yerr=yerr[i], color=colors[i], marker='o', elinewidth=2, ecolor='k')
                  ax.errorbar(x, y, yerr=yerr[i], color=colors[i], ecolor=colors[i], capsize=0, lw=0, elinewidth=3)

            if markers:
                  ax.plot(x, y, lw=2.5, marker='o', ms=5, color=colors[i], label=labels[i])
            else:
                  ax.plot(xp, pxp, linestyle=linestyles[i], lw=3.5, color=colors[i], label=labels[i])
            pse.append(xp[idx]/scale_factor)

      plt.setp(ax, xlim=xxlim, xticks=x, ylim=(-.05, 1.05), yticks=[0, 1])
      ax.set_xticklabels([int(xt) for xt in xtls], fontsize=18); ax.set_yticklabels([0.0, 1.0], fontsize=18)
      ax.set_xlabel(xxlabel, fontsize=18); ax.set_ylabel(yylabel, fontsize=18)
      ax.legend(loc=0, fontsize=16)

      plt.tight_layout()
      sns.despine()

      return np.array(pse)



def plot_fits(y, yhat, bw=.1, plot_acc=False, save=False, kind='radd', savestr='fit_plot'):

      sns.set_context('notebook', font_scale=1.6)

      gq = y[6:11]
      eq = y[11:]
      fit_gq = yhat[6:11]
      fit_eq = yhat[11:]

      if plot_acc:
            f, (ax1, ax2) = plt.subplots(1,2,figsize=(10, 5.5))
            if kind in ['radd', 'irace']:
                  gacc = y[0]
                  sacc = y[1:6]
                  fit_gacc = yhat[0]
                  fit_sacc = yhat[1:6]
                  c1=gpal(2)
                  c2=rpal(2)
            else:
                  sacc = y[:6]
                  fit_sacc = yhat[:6]
                  c1=bpal(2)
                  c2=ppal(2)
      else:
            f, ax1 = plt.subplots(1, figsize=(5, 5.5))

      # Fit RT quantiles to KDE function in radd.utils
      quant_list = [gq, fit_gq, eq, fit_eq]
      kdefits = [utils.kde_fit_quantiles(q, bw=bw) for q in quant_list]

      if kind=='radd':
            lbs=['Data Cor','Fit Cor','Data Err','Fit Err']
      else:
            lbs=['Data Hi', 'Fit Hi', 'Data Lo', 'Fit Lo']

      sns.kdeplot(kdefits[0], cumulative=True, label=lbs[0], linestyle='-', color=gpal(2)[0], ax=ax1, linewidth=3.5)
      sns.kdeplot(kdefits[1], cumulative=True, label=lbs[1], linestyle='--', color=gpal(2)[1], ax=ax1, linewidth=3.5)

      sns.kdeplot(kdefits[2], cumulative=True, label=lbs[2], linestyle='-', color=rpal(2)[0], ax=ax1, linewidth=3.5)
      sns.kdeplot(kdefits[3], cumulative=True, label=lbs[3], linestyle='--', color=rpal(2)[1], ax=ax1, linewidth=3.5)

      ax1.set_xlim(4.3, 6.5)
      ax1.set_ylabel('P(RT<t)')
      ax1.set_xlabel('RT (s)')
      ax1.set_ylim(-.05, 1.05)
      ax1.set_xticklabels(ax1.get_xticks()*.1)

      if plot_acc:
            # Plot observed and predicted stop curves
            scurves([sacc, fit_sacc], labels=['Data SC', 'Fit SC'], colors=bpal(2), kind=kind, linestyles=['-','--'], ax=ax2)

      plt.tight_layout()
      sns.despine()
      if save:
            plt.savefig(savestr+'.png', format='png', dpi=300)

def plot_kde_cdf(quant, bw=.1, ax=None, color=None):

      if ax is None:
            f, ax = plt.subplots(1, figsize=(5,5))
      if color is None:
            color='k'
      kdefits = utils.kde_fit_quantiles(quant, bw=bw)
      sns.kdeplot(kdefits, cumulative=True,  color=color, ax=ax, linewidth=2.5)

      ax.set_xlim(kdefits.min()*.94, kdefits.max()*1.05)
      ax.set_ylabel('P(RT<t)')
      ax.set_xlabel('RT (s)')
      ax.set_ylim(-.05, 1.05)
      ax.set_xticklabels(ax.get_xticks()*.1)

      plt.tight_layout()
      sns.despine()

def gen_pro_traces(ptheta, bias_vals=[], bias='v', integrate_exec_ss=False, return_exec_ss=False, pgo=np.arange(0, 1.2, .2)):

      dvglist=[]; dvslist=[]

      if bias_vals==[]:
            deplist=np.ones_like(pgo)

      for val, pg in zip(bias_vals, pgo):
            ptheta[bias] = val
            ptheta['pGo'] = pg
            dvg, dvs = RADD.run(ptheta, ntrials=10, tb=.565)
            dvglist.append(dvg[0])

      if pg<.9:
            dvslist.append(dvs[0])
      else:
            dvslist.append([0])

      if integrate_exec_ss:
            ssn = len(dvslist[0])
            traces=[np.append(dvglist[i][:-ssn],(dvglist[i][-ssn:]+ss)-dvglist[i][-ssn:]) for i, ss in enumerate(dvslist)]
            traces.append(dvglist[-1])
            return traces

      elif return_exec_ss:
            return [dvglist, dvslist]

      else:
            return dvglist


def gen_re_traces(rtheta, integrate_exec_ss=False, ssdlist=np.arange(.2, .45, .05)):

      dvglist=[]; dvslist=[]
      rtheta['pGo']=.5
      rtheta['ssv']=-abs(rtheta['ssv'])
      #animation only works if tr<=ssd
      rtheta['tr']=np.min(ssdlist)-.001

      for ssd in ssdlist:
            rtheta['ssd'] = ssd
            dvg, dvs = RADD.run(rtheta, ntrials=10, tb=.650)
            dvglist.append(dvg[0])
            dvslist.append(dvs[0])

      if integrate_exec_ss:
            ssn = len(dvslist[0])
            traces=[np.append(dvglist[i][:-ssn],(dvglist[i][-ssn:]+ss)-dvglist[i][-ssn:]) for i, ss in enumerate(dvslist)]
            traces.append(dvglist[-1])
            return traces

      ssi, xinit_ss = [], []
      for i, (gtrace, strace) in enumerate(zip(dvglist, dvslist)):
            leng = len(gtrace)
            lens = len(strace)
            xinit_ss.append(leng - lens)
            ssi.append(strace[0])
            dvslist[i] = np.append(gtrace[:leng-lens], strace)
            dvslist[i] = np.append(dvslist[i], np.array([0]))

      return [dvglist, dvslist, xinit_ss, ssi]


def build_decision_axis(theta, gotraces):

      # init figure, axes, properties
      f, ax = plt.subplots(1, figsize=(7,4))

      w=len(gotraces[0])+50
      h=theta['a']
      start=-100

      plt.setp(ax, xlim=(start-1, w+1), ylim=(0-(.01*h), h+(.01*h)))

      ax.hlines(y=h, xmin=-100, xmax=w, color='k')
      ax.hlines(y=0, xmin=-100, xmax=w, color='k')
      ax.hlines(y=theta['z'], xmin=start, xmax=w, color='Gray', linestyle='--', alpha=.7)
      ax.vlines(x=w-50, ymin=0, ymax=h, color='r', linestyle='--', alpha=.5)
      ax.vlines(x=start, ymin=0, ymax=h, color='k')

      ax.set_xticklabels([])
      ax.set_yticklabels([])
      ax.set_xticks([])
      ax.set_yticks([])

      sns.despine(top=True, right=True, bottom=True, left=True)

      return f, ax


def re_animate(i, x, dvg_traces, dvg_lines, dvs_traces, dvs_lines, rtheta, xi, yi):

      clist=['#2c724f']*len(dvg_traces)
      clist_ss = sns.light_palette('#c0392b', n_colors=6)[::-1]

      for nline, (gl, g) in enumerate(zip(dvg_lines, dvg_traces)):
            if g[i]>=rtheta['a'] or dvs_traces[nline][i]<=0:
                  continue
            gl.set_data(x[:i+1], g[:i+1])
            gl.set_color(clist[nline])

            if dvs_traces[nline][i]>0:
                  ssi = len(g) - len(dvs_traces[nline]) + 1
                  dvs_lines[nline].set_data(x[xi[nline]:i+1], dvs_traces[nline][xi[nline]:i+1])
                  dvs_lines[nline].set_color(clist_ss[nline])

      return dvs_lines, dvg_lines


def pro_animate(i, x, protraces, prolines):

      clist = sns.color_palette('autumn', n_colors=6)[::-1]

      for nline, (pline, ptrace) in enumerate(zip(prolines, protraces)):
            pline.set_data(x[:i+1], ptrace[:i+1])
            pline.set_color(clist[nline])

      return prolines,


def plot_all_traces(DVg, DVs, theta, ssd=np.arange(.2,.45,.05)):

      for i, trace in enumerate(DVs[0,:]):
            theta['ssd'] = ssd[i]
            plot_traces(DVg[0], trace, theta)


def plot_traces(DVg=[], DVs=[], sim_theta={}, kind='radd', ssd=.450, ax=None, tau=.0005, tb=.650, cg='#2c724f', cr='#c0392b'):
      if ax is None:
            f,ax=plt.subplots(1,figsize=(8,5))
      tr=sim_theta['tr']; a=sim_theta['a']; z=sim_theta['z'];
      for i, igo in enumerate(DVg):
            ind = np.argmax(igo>=a)
            xx = [np.arange(tr, tr+(len(igo[:ind-1])*tau), tau), np.arange(tr, tb, tau)]
            x = xx[0 if len(xx[0])<len(xx[1]) else 1]
            plt.plot(x, igo[:len(x)], color=cg, alpha=.1, linewidth=.5)
            if kind in ['irace', 'radd'] and i<len(DVs):
                  if np.any(DVs<=0):
                        ind=np.argmax(DVs[i]<=0)
                  else:
                        ind=np.argmax(DVs[i]>=a)
                  xx = [np.arange(ssd, ssd+(len(DVs[i, :ind-1])*tau), tau), np.arange(ssd, tb, tau)]
                  x = xx[0 if len(xx[0])<len(xx[1]) else 1]
                  #x = np.arange(ssd, ssd+(len(DVs[i, :ind-1])*tau), tau)
                  plt.plot(x, DVs[i, :len(x)], color=cr, alpha=.1, linewidth=.5)

      xlow = np.min([tr, ssd])
      xlim = (xlow*.95, 1.05*tb)
      if kind=='pro' or np.any(DVs<=0):
            ylow=0
            ylim=(-.03, a*1.03)
      else:
            ylow=z
            ylim=(z-.03, a*1.03)

      plt.setp(ax, xlim=xlim, ylim=ylim)
      ax.hlines(y=z, xmin=xlow, xmax=tb, linewidth=2, linestyle='--', color="k", alpha=.5)
      ax.hlines(y=a, xmin=xlow, xmax=tb, linewidth=2, linestyle='-', color="k")
      ax.hlines(y=ylow, xmin=xlow, xmax=tb, linewidth=2, linestyle='-', color="k")
      ax.vlines(x=xlow, ymin=ylow*.998, ymax=a*1.002, linewidth=2, linestyle='-', color="k")
      sns.despine(top=True,bottom=True, right=True, left=True)
      ax.set_xticklabels([])
      ax.set_yticklabels([])
      ax.set_xticks([])
      ax.set_yticks([])

      return ax

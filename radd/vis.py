#!/usr/local/bin/env python
from __future__ import division
import sys
from future.utils import listvalues
from copy import deepcopy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from radd.tools import colors, analyze
from IPython.display import display, Latex
import warnings

warnings.simplefilter('ignore', np.RankWarning)
warnings.filterwarnings("ignore", module="matplotlib")
cdict = colors.get_cpals('all')
rpal = cdict['rpal']
bpal = cdict['bpal']
gpal = cdict['gpal']
ppal = cdict['ppal']
heat = cdict['heat']
cool = cdict['cool']
slate = cdict['slate']
sns.set(style='darkgrid', rc={'figure.facecolor':'white'}, font_scale=1.2)

def plot_model_fits(y, yhat, fitparams, err=None, palettes=[gpal, bpal], save=False, cdf=True, bw=.01, savestr=None):
    """ main plotting function for displaying model fit predictions over data
    """
    sns.set(style='darkgrid', rc={'figure.facecolor':'white'}, font_scale=1.5)
    # extract model and fit info from fitparams
    nlevels = fitparams['nlevels']
    ssd, nssd, nss, nss_per, ssd_ix = fitparams.ssd_info
    quantiles = fitparams.quantiles

    # make colors and labels
    try:
        params = '_'.join(list(fitparams.depends_on))
        clrs = [[colors.param_color_map(p)]*2 for p in params]
    except Exception:
        color_list = colors.assorted_list()
        clrs = [[c]*2 for c in color_list]
    #palette = colors.get_cpals(random=True)
    #clrs = [[c]*2 for c in palette(nlevels)]
    lbls = get_plot_labels(fitparams)
    f, axes = plt.subplots(nlevels, 3, figsize=(14, 5*nlevels), sharey=True)
    # make two dimensional for iterating 1st dim
    axes = axes.reshape(nlevels, 3)
    plot_acc = scurves
    if nssd==1:
        plot_acc = plot_accuracy
    y_dat = unpack_vector(y, fitparams, bw=bw)
    y_kde = unpack_vector(y, fitparams, bw=bw, kde=True)
    yhat_dat = unpack_vector(yhat, fitparams, bw=bw)
    if err is not None:
        y_err = unpack_vector(err, fitparams, bw=bw)
        sc_err = [e[0] for e in y_err]
        qp_err = [[e[1], e[2]] for e in y_err]
    else:
        sc_err, qp_err = [[None]*nlevels]*2

    for i, (ax1, ax2, ax3) in enumerate(axes):
        accdata = [y_dat[i][0], yhat_dat[i][0]]
        qpdata = [y_dat[i], yhat_dat[i]]
        plot_acc(accdata, err=sc_err[i], ssd=ssd[i], colors=clrs[i], labels=lbls[i], ax=ax1)
        plot_quantiles(qpdata, err=qp_err[i], quantiles=quantiles, colors=clrs[i], axes=[ax2,ax3], kde=y_kde[i], bw=bw)
    axes = format_axes(axes)
    if save:
        if savestr is None:
            savestr = fitparams.model_id
        plt.savefig('.'.join([savestr, 'png']), dpi=600)
        if fitparams.fit_on=='subjects':
            plt.close('all')

def scurves(data, err=None, colors=None, labels=None, ssd=None, ax=None, get_pse=False, pretune_fx='interpolate', **kwargs):
    """ plotting function for displaying model-predicted
    stop curve (across SSDs) over empirical estimates
    """
    if err is None:
        err = [np.zeros(len(dat)) for dat in data]
    if ax is None:
        f, ax = plt.subplots(1, figsize=(5.5, 6))
    if colors is None:
        colors = slate(len(data))
    if labels is None:
        labels = [''] * len(data)
    if ssd is not None:
        ssds = ssd.squeeze()*1e3
        x = np.array([np.float(d) for d in ssds])
        xtls = ["{:.0f}".format(d) for d in ssds]
    else:
        x = np.arange(len(data[0]), dtype='float')*50
        xtls = [str(xx) for xx in x]
    pse=[]
    for i, yi in enumerate(data):
        if pretune_fx=='interpolate':
            xsim, ysim = analyze.scurve_interpolate(x, yi)
        elif pretune_fx=='polynomial':
            xsim, ysim = analyze.scurve_poly_fit(x, yi)
        xsim, ysim = analyze.fit_sigmoid(xsim, ysim)
        idx = (np.abs(ysim - .5)).argmin()
        pse.append(xsim[idx])
        if not i%2:
            ax.errorbar(x, yi, yerr=err, lw=0., elinewidth=1.5, color=colors[i], marker='o', ms=5)
            ax.plot(xsim, ysim, lw=2, color=colors[i], label=labels[i])
            continue
        ax.plot(x, yi, lw=0., marker='o', ms=10, mfc="none", mec=colors[i], mew=1.7, label=labels[i])
    xxlim = (xsim[0], xsim[-1])
    ytls = np.arange(0, 1.2, .2).astype(np.int)
    plt.setp(ax, xticks=x, xlim=xxlim, xticklabels=xtls, ylim=(-.01, 1.05), yticks=ytls, yticklabels=ytls)
    ax.set_ylabel('Percent Correct'); ax.legend(loc=0)
    ax.legend(loc=0)
    plt.tight_layout()
    sns.despine()
    if get_pse:
        return pse

def plot_quantiles(data, err=None, quantiles=None, axes=None, colors=None, labels=None, kde=None, bw=.008):
    """ plotting function for displaying model-predicted
    quantile-probabilities over empirical estimates
    """
    y_data, yhat_data = data
    c, c_hat = colors
    if axes is not None:
        axc, axe = axes
    else:
        f, (axc, axe) = plt.subplots(1, 2, figsize=(10, 4))
    qc, qc_hat = y_data[1], yhat_data[1]
    qe, qe_hat = y_data[2], yhat_data[2]
    if quantiles is None:
        quantiles = np.linspace(.1, .9, qc.size)
    if err is not None:
        qc_err, qe_err = err
    else:
        qc_err, qe_err = [np.zeros(len(qc))]*2
    if kde is not None:
        qc_kde, qe_kde = kde[1], kde[2]
        sns.kdeplot(qc_kde, cumulative=1, color=c, ax=axc, linewidth=2, linestyle='-', bw=bw)
        sns.kdeplot(qe_kde, cumulative=1, color=c, ax=axe, linewidth=2, linestyle='-', bw=bw)
    axc.errorbar(qc, quantiles, xerr=qc_err, color=c, linewidth=0, elinewidth=1.5, marker='o', ms=5, label=labels)
    axe.errorbar(qe, quantiles, xerr=qe_err, color=c, linewidth=0, elinewidth=1.5, marker='o', ms=5, label=labels)
    axc.plot(qc_hat, quantiles, mec=c_hat, linewidth=0, marker='o', ms=10, mfc='none', mew=1.7, label=labels)
    axe.plot(qe_hat, quantiles, mec=c_hat, linewidth=0, marker='o', ms=10, mfc='none', mew=1.7, label=labels)

def plot_accuracy(data=[], err=None, ssd=None, ax=None, linestyles=None, colors=None, labels=None, xtls=['Go', 'Stop'], ssdlabels=False, **kwargs):
    """ plotting function for displaying model-predicted
    stop probability (at mean SSD) on top of empirical estimates
    (used when data is collected using tracking procedure to est. SSRT)
    """
    if err is None:
        err = [np.zeros(len(dat)) for dat in data]
    if ax is None:
        f, ax = plt.subplots(1, figsize=(5.5, 6))
    if colors is None:
        colors = slate(len(data))
    if labels is None:
        labels = [''] * len(data)
    if linestyles is None:
        linestyles = ['-', '--'] * len(data)
    x = np.arange(len(data[0]), dtype='float')
    if ssd is not None:
        ssdstr = "SSD={:.0f}ms".format(ssd.mean(axis=0)*1e3)
        labels[0] = ' '.join([labels[0], ssdstr])
        xtls = ['Go', 'Stop']
    for i, yi in enumerate(data):
        if not i%2:
            ax.errorbar(x, yi, yerr=err[i], linestyle=linestyles[i], lw=1.5, elinewidth=1.5, color=colors[i], label=labels[i], marker='o', ms=5)
            continue
        xjit = x + (i*.02)
        ax.plot(xjit, yi, lw=0, marker='o', ms=10, mfc='none', mec=colors[i], mew=1.7, label=labels[i])

    plt.setp(ax, xticks=x, xlim=(-0.25, 1.25), xticklabels=xtls, ylim=(-.01, 1.05), yticks=np.arange(0, 1.2, .2))
    ax.set_ylabel('Percent Correct'); ax.legend(loc=0)
    sns.despine()
    plt.tight_layout()

def unpack_vector(vector, fitparams, kde=False, bw=.01):
    nlevels = fitparams['nlevels']
    nquant = fitparams['quantiles'].size
    nssd = fitparams['ssd_info'][1]
    vector = vector.reshape(nlevels, int(vector.size/nlevels))
    unpacked = []
    for v in vector:
        if nssd>1:
            # get accuracy at each SSD
            presp = v[1:1+nssd]
        else:
            # get go, stop accuracy
            presp = v[:2]
        quant = v[-nquant*2:]
        quant_cor = quant[:nquant]
        quant_err = quant[-nquant:]
        if kde:
            quant_cor = analyze.kde_fit_quantiles([quant_cor], bw=bw)
            quant_err = analyze.kde_fit_quantiles([quant_err], bw=bw)
        unpacked.append([presp, quant_cor, quant_err])
    return unpacked

def format_axes(axes):
    q_axes = []
    for ax in axes.flatten():
        if not ax.is_first_col():
            q_axes.append(ax)
    yylim=(-.01, 1.05); yyticks=np.arange(0, 1.2, .2)
    axesqp = [np.hstack([l.get_xdata() for l in ax.lines]) for ax in q_axes]
    xxticks = [[qdata.min(), qdata.mean(), qdata.max()] for qdata in axesqp]
    xxlim = [(xxt[0]-.008, xxt[-1]+.008) for xxt in xxticks]
    xxtls = [["{:.2f}".format(xtl) for xtl in xxt] for xxt in xxticks]
    for ax in axes.flatten():
        plt.setp(ax, ylim=yylim, yticks=yyticks)
        if not ax.is_first_col():
            plt.setp(ax, yticklabels=yyticks)
        if not ax.is_first_col():
            xl, xt, xtl = xxlim[0], xxticks[0], xxtls[0]
            if ax.is_last_col():
                xl, xt, xtl = xxlim[-1], xxticks[-1], xxtls[-1]
            plt.setp(ax, xlim=xl, xticks=xt, xticklabels=xtl)
            if ax.is_last_row():
                plt.setp(ax, xlabel='RT (s)')
            else:
                plt.setp(ax, xlabel='')
        if ax.is_first_col() and ax.is_last_row():
            ax.set_xlabel('SSD (ms)')
    axes = axes.flatten()
    axes[0].set_title('Accuracy', position=(.5, 1.02))
    axes[1].set_title('Correct Quant-Prob', position=(.5, 1.02))
    axes[2].set_title('Error Quant-Prob', position=(.5, 1.02))
    sns.despine()
    plt.tight_layout()
    return axes

def compare_nested_models(fitdf, model_ids, yerr=None, plot_stats=True, verbose=False):
    gof = {}
    fitdf = fitdf[fitdf.pvary.isin(model_ids)]
    # print GOF stats for both models
    for i, p in enumerate(model_ids):
        name = parameter_name(p)
        gof[p] = fitdf.loc[i, ['AIC', 'BIC']]
    # Which model provides a better fit to the data?
    aicwinner = model_ids[np.argmin([gof[mid][0] for mid in model_ids])]
    bicwinner = model_ids[np.argmin([gof[mid][1] for mid in model_ids])]
    if verbose:
        print('AIC likes {} model'.format(aicwinner))
        print('BIC likes {} model'.format(bicwinner))
    plot_model_gof(gof, aicwinner, model_ids, yerr=yerr)
    return gof

def plot_model_gof(gof_dict, aicwinner, pvary=None, yerr=None):
    sns.set(style='darkgrid', rc={'figure.facecolor':'white'}, font_scale=1.1)

    if pvary is None:
        pvary = np.sort(list(gof_dict))
    nmodels = len(pvary)
    if yerr is None:
        yerr = [np.zeros(2) for i in range(nmodels)]
    f, ax = plt.subplots(1, figsize=(10,7))
    x = np.arange(1, nmodels*2, 2)
    clrs = [colors.param_color_map(p) for p in pvary]
    #clrs = colors.assorted_list()
    lbls = {p: parameter_name(p,True) for p in pvary}
    for i, p in enumerate(pvary):
        yaic, ybic = gof_dict[p][['AIC', 'BIC']]
        aic_err, bic_err = yerr[i]
        lbl = lbls[p]
        if p==aicwinner:
            lbl+='*'
        ax.bar(x[i]-.32, yaic, yerr=aic_err, color=clrs[i], ecolor="#34495e", error_kw={'linewidth':3, 'alpha':1}, alpha=.8, width=.64, align='center', edgecolor=clrs[i], label=lbl)
        ax.bar(x[i]+.32, ybic, yerr=bic_err, color=clrs[i], ecolor="#34495e", error_kw={'linewidth':3, 'alpha':1}, alpha=.65, width=.64, align='center', edgecolor=clrs[i])
    vals = np.hstack(gof_dict.values()).astype(float)
    yylim = (vals.max()*.97, vals.min()*1.07)
    plt.setp(ax, xticks=x, ylim=yylim, xlim=(0, x[-1]+1), ylabel='IC')
    ax.set_xticklabels(['AIC|BIC']*nmodels, fontsize=14)
    ax.invert_yaxis()
    sns.despine()
    ax.legend(loc=0, fontsize=14)

def plot_param_distributions(p, nsamples=1000):
    from radd import theta
    pkeys = np.sort(list(p))
    nparams = pkeys.size
    p_dists = theta.random_inits(pkeys=pkeys, ninits=nsamples)
    clrs = colors.param_color_map()
    lbls = {pk: parameter_name(pk,True) for pk in pkeys}
    ncols = np.ceil(nparams/2.).astype(int)
    fig, axes = plt.subplots(2, ncols, figsize=(10,5), dpi=600)
    axes = axes.flatten()
    for i, pk in enumerate(pkeys):
        sns.distplot(p_dists[pk], label=lbls[pk], color=clrs[pk], ax=axes[i])
    for ax in axes:
        ax.legend(loc=0, fontsize=16)
    plt.tight_layout()
    sns.despine()

def compare_param_estimates(p1, p2, depends_on=None):
    popt1 = deepcopy(p1)
    popt2 = deepcopy(p2)
    if depends_on is not None:
        _ = [popt1.pop(param) for param in list(depends_on)]
    pnames = np.sort(list(popt1))
    x = np.arange(pnames.size)
    clrs = sns.color_palette(palette='muted', n_colors=x.size)
    i = 0
    f, ax = plt.subplots(1, figsize=(6,5))
    for param in pnames:
        plt.plot(x[i], abs(popt1[param]), marker='o', markersize=10, color=clrs[i])
        plt.plot(x[i], abs(popt2[param]), marker='s', markersize=8, color=clrs[i])
        i+=1
    _ = plt.setp(plt.gca(), xlim=(x[0]-.5, x[-1]+.5), xticks=x, xticklabels=pnames)

def get_plot_labels(fitparams):
    from itertools import product
    clmap = fitparams['clmap']
    nconds = len(list(clmap))
    clevels = [levels for levels in listvalues(clmap)]
    if nconds>1:
        level_data = list(product(*clevels))
        clevels = ['_'.join(lvls) for lvls in level_data]
    else:
        clevels = np.hstack(clevels)
    labels = [[lvl + dtype for dtype in [' data', ' model']] for lvl in clevels]
    return labels

def parameter_name(param, tex=False):
    ix = 0
    if tex:
        ix = 1
    param_name = {'v':['Drift', '$v_{G}$'],
        'ssv': ['ssDrift', '$v_{S}$'],
        'a': ['Threshold', '$a_{G}$'],
        'tr': ['Onset', '$tr_{G}$'],
        'xb': ['Dynamic Gain', '$xb_{G}$'],
        'sso': ['ssOnset', '$so_{S}$'],
        'flat': ['Flat', 'Flat'],
        'all': ['Flat', 'Flat']}
    if '_' in param:
        param = param.split('_')
    if hasattr(param, '__iter__'):
        return ' + '.join([param_name[p][ix] for p in param])
    return param_name[param][ix]

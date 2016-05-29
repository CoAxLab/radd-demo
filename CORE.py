#!/usr/local/bin/env python
from __future__ import division
import os
from copy import deepcopy
import numpy as np
import pandas as pd
from numpy import array
from scipy.stats.mstats import mquantiles as mq
from radd.tools import theta, analyze, dfhandler

class RADDCore(object):

    """ Parent class for constructing shared attributes and methods
    of Model & Optimizer objects. Not meant to be used directly.

    Contains methods for building dataframes, generating observed data vectors
    that are entered into cost function during fitting as well as calculating
    summary measures and weight matrix for weighting residuals during optimization.

    TODO: COMPLETE DOCSTRINGS
    """

    def __init__(self, data=None, kind='xdpm', inits=None, fit_on='average', depends_on=None, niter=50,  fit_whole_model=True, tb=None, fit_noise=False, pro_ss=False, dynamic='hyp', hyp_effect_dir=None, percentiles=([.1, .3, .5, .7, .9]), *args, **kws):

        self.data = data
        self.kind = kind
        self.fit_on = fit_on
        self.dynamic = dynamic
        self.fit_whole_model = fit_whole_model
        self.hyp_effect_dir = hyp_effect_dir
        self.percentiles = percentiles

        # CONDITIONAL PARAMETERS
        self.depends_on = depends_on
        self.conds = depends_on.values()
        self.nconds = len(self.conds)
        self.levels = [np.sort(data[cond].unique()) for cond in self.conds]
        self.nlevels = np.sum([len(lvls) for lvls in self.levels])

        # DEFINE ITERABLES
        if self.fit_on == 'bootstrap':
            self.idx = range(niter)
        else:
            self.idx = list(data.idx.unique())
        self.nidx = len(self.idx)

        # Get timebound
        if tb != None:
            self.tb = tb
        else:
            self.tb = data[data.response == 1].rt.max()

        # PARAMETER INITIALIZATION
        if inits is None:
            self.__get_default_inits__()
        else:
            self.inits = inits

        self.handler = dfhandler.DataHandler(self)


    def __prepare_fit__(self):
        """ performs model setup and initiates dataframes. Automatically run when Model object is initialized
            *   pc_map is a dict containing parameter names as keys with values
                    corresponding to the names given to that parameter in Parameters object
                    (see optmize.Optimizer).
            *   Parameters (p[pkey]=pval) that are constant across conditions are broadcast as [pval]*n.
                    Conditional parameters are treated as arrays with distinct values [V1, V2...Vn], one for
                    each condition.

            pc_map (dict):    keys: conditional parameter names (i.e. 'v')
                              values: keys + condition names ('v_bsl, v_pnl')

            |<--- PARAMETERS OBJECT [LMFIT] <-------- [IN]
            |
            |---> p = {'v_bsl': V1, 'v_pnl': V2...} --->|
                                                        |
            |<--- pc_map = {'v':['v_bsl', 'v_pnl']} <---|
            |
            |---> p['v'] = array([V1, V2]) -------> [OUT]
        """

        params = np.sort(self.inits.keys()).tolist()
        cond_inits = lambda a, b: pd.Series(dict(zip(a, b)))
        self.pc_map = {}

        for cond_i in xrange(self.nconds):
            for d in self.depends_on.keys():
                params.remove(d)
                self.pc_map[d] = ['_'.join([d, l]) for l in self.levels[cond_i]]
                params.extend(self.pc_map[d])

        # MAKE DATAFRAMES FOR OBSERVED DATA, POPT, MODEL PREDICTIONS
        self.__make_dataframes__()
        # CALCULATE WEIGHTS FOR COST FX
        if self.weighted:
            self.__get_wts__()
        else:
            # MAKE PSEUDO WEIGHTS
            self.flat_wts = [np.ones_like(idat.flatten()) for idat in self.observed_flat]
            self.avg_wts = [np.ones_like(idat.flatten()) for idat in self.observed]

        if self.verbose:
            self.is_prepared = messages.saygo(depends_on=self.depends_on, labels=self.levels, kind=self.kind, fit_on=self.fit_on, dynamic=self.dynamic)
        else:
            self.prepared = True

        self.set_fitparams()


    def __make_dataframes__(self):
        """ wrapper for dfhandler.DataHandler.make_dataframes
        """
        self.handler.make_dataframes()
        # Group dataframe (nsubjects*nconds*nlevels x ndatapoints)
        self.observedDF = self.handler.observedDF.copy()
        # list (nsubjects long) of data arrays (nconds*nlevels x ndatapoints) to fit
        self.observed = self.handler.observed
        # list of flattened data arrays (averaged across conditions)
        self.observed_flat = self.handler.observed_flat

        self.datdf = self.handler.datdf
        self.dfvals = self.handler.dfvals

        # dataframe with same dim as observeddf for storing model predictions
        self.fits = self.handler.fits
        # dataframe with same dim as observeddf for storing fit info
        self.fitinfo = self.handler.fitinfo


    def __get_wts__(self, weight_presponse=True):
        """ wrapper for analyze functions used to calculate
        weights used in cost function
        """
        if self.fit_on == 'subjects':
            self.cost_wts, self.flat_cost_wts = analyze.get_subject_cost_weights(self, weight_presponse=weight_presponse)
        else:
            self.cost_wts, self.flat_cost_wts = analyze.get_group_cost_weights(self)


    def set_fitparams(self, ntrials=10000, tol=1.e-5, maxfev=5000, niter=500, disp=True, get_params=False, method='nelder', **kwrgs):

        if not hasattr(self, 'fitparams'):
            # fill with provided/or default values for initial set
            self.fitparams = {'ntrials': ntrials, 'maxfev': maxfev, 'disp': disp, 'tol': tol, 'niter': niter, 'method': method, 'idx': 0, 'percentiles': self.percentiles, 'dynamic':self.dynamic, 'nlevels': self.nlevels, 'tb': self.tb, 'fit_on': self.fit_on, 'depends_on': self.depends_on}

        else:
            # only fill with kwgs (i.e. subject id's, subject specific content)
            for kw_arg, kw_val in kwrgs.items():
                self.fitparams[kw_arg] = kw_val

        if hasattr(self, 'ssd'):
            self.fitparams['ssd'] = self.ssd[self.fitparams['idx']]
            self.fitparams['nssd'] = self.fitparams['ssd'].size

        if get_params:
            return self.fitparams


    def set_basinparams(self, nrand_inits=2, interval=10, niter=40, stepsize=.05, nsuccess=20, is_flat=True, method='TNC', btol=1.e-3, maxiter=20, get_params=False, bdisp=False):

        if not hasattr(self, 'basinparams'):
            self.basinparams = {}
        self.basinparams = {'nrand_inits': nrand_inits, 'interval': interval, 'niter': niter, 'stepsize': stepsize, 'nsuccess': nsuccess, 'method': method, 'tol': btol, 'maxiter': maxiter, 'disp': bdisp}
        if get_params:
            return self.basinparams

    def __extract_popt_fitinfo__(self, finfo=None):
        """ wrapper for DataHandler.extract_popt_fitinfo()
        """
        popt = self.handler.extract_popt_fitinfo(finfo=finfo)
        return popt

    def rangl_data(self, data):
        """ wrapper for analyze.rangl_data
        """
        rangled = analyze.rangl_data(data, percentiles=self.percentiles, tb=self.tb)
        return rangled

    def resample_data(self, data):
        """ wrapper for analyze.resample_data
        """
        resampled = analyze.resample_data(data, n=100, data_style=self.data_style, tb=self.tb, kind=self.kind)
        return resampled


    def assess_fit(self, finfo=None):
        """ wrapper for analyze.assess_fit calculates and stores
        rchi, AIC, BIC and other fit statistics
        """
        return analyze.assess_fit(finfo)


    def params_io(self, p={}, io='w', iostr='popt'):
        """ read // write parameters dictionaries
        """
        if io == 'w':
            pd.Series(p).to_csv(''.join([iostr, '.csv']))
        elif io == 'r':
            ps = pd.read_csv(''.join([iostr, '.csv']), header=None)
            p = dict(zip(ps[0], ps[1]))
            return p


    def fits_io(self, fits=[], io='w', iostr='fits'):
        """ read // write y, wts, yhat arrays
        """
        if io == 'w':
            if np.ndim(self.avg_y) > 1:
                y = self.avg_y.flatten()
                fits = fits.flatten()
            else:
                y = self.avg_y
            index = np.arange(len(fits))
            df = pd.DataFrame({'y': y, 'wts': self.avg_wts, 'yhat': fits}, index=index)
            df.to_csv(''.join([iostr, '.csv']))

        elif io == 'r':
            df = pd.read_csv(''.join([iostr, '.csv']), index_col=0)
            return df


    def __nudge_params__(self, p, lim=(.98, 1.02)):
        """
        nudge params so not all initialized at same val
        """

        if self.fitparams['hyp_effect_dir'] == 'up':
            lim = [np.min(lim), np.max(lim)]
        else:
            lim = [np.max(lim), np.min(lim)]

        for pkey in p.keys():
            bump = np.linspace(lim[0], lim[1], self.nlevels)
            if pkey in self.pc_map.keys():
                p[pkey] = p[pkey] * bump
        return p


    def slice_bounds_global(self, inits, pfit):

        b = theta.get_bounds(kind=self.kind, tb=self.fitparams['tb'])
        pclists = []
        for pkey, pcl in self.pc_map.items():
            pfit.remove(pkey)
            pfit.extend(pcl)
            # add bounds for all
            # pkey condition params
            for pkc in pcl:
                inits[pkc] = inits[pkey]
                b[pkc] = b[pkey]

        pbounds = tuple([slice(b[pk][0], b[pk][1], .25 * np.max(np.abs(b[pk]))) for pk in pfit])
        params = tuple([inits[pk] for pk in pfit])

        return pbounds, params

    def __prep_basin_data__(self):
        cond_data = self.fitparams['y']
        cond_wts = self.fitparams['wts']
        return cond_data, cond_wts

    def __remove_outliers__(self, sd=1.5, verbose=False):
        self.data = analyze.remove_outliers(self.data, sd=sd, verbose=verbose)

    def __get_default_inits__(self):
        self.inits = theta.get_default_inits(kind=self.kind, dynamic=self.dynamic, depends_on=self.depends_on)

    def __get_optimized_params__(self, include_ss=False, fit_noise=False):
        params = theta.get_optimized_params(kind=self.kind, dynamic=self.dynamic, depends_on=self.depends_on)
        return params

    def __check_inits__(self, inits=None, pro_ss=False, fit_noise=False):
        if inits is None:
            inits = dict(deepcopy(self.inits))
        self.inits = theta.check_inits(inits=inits, pdep=self.depends_on.keys(), kind=self.kind, pro_ss=pro_ss, fit_noise=fit_noise)

    def __rename_bad_cols__(self):
        self.data = analyze.rename_bad_cols(self.data)

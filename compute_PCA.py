#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  1 08:09:01 2022

@author: joern
"""

# %% imports

import string

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import cm
from scipy.stats import boxcox
from sklearn.decomposition import PCA

from cABCanalysis import cABCanalysis


# https://stackoverflow.com/questions/39216897/plot-pca-loadings-and-loading-in-biplot-in-sklearn-like-rs-autoplot

# %% Functions
def annotate_axes(ax, text, fontsize=18):
    ax.text(-.01, 1.01, text, transform=ax.transAxes,
            ha="center", va="center", fontsize=fontsize, color="black")


def PCA_biplot(projections, components, target=None, biplot=True, labels=None, ax=None):

    ax = ax or plt.gca()
    sns.scatterplot(
        ax=ax, x=projections[:, 0], y=projections[:, 1], hue=target, palette="bright")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")

    if biplot == True:
        xvector = components[0]
        yvector = components[1]

        for i in range(len(xvector)):
            max_colors = len(xvector) + 1
            cmap = cm.get_cmap('tab10')  # ('hsv') #('nipy_spectral')
            col = cmap(((5 * i) % max_colors) / max_colors)
            ax.arrow(x=0, y=0, dx=xvector[i]*max(projections[:, 0]), dy=yvector[i]*max(projections[:, 1]),
                     color=col, width=0.005, head_width=0.05)
            if labels is None:
                ax.text(xvector[i]*max(projections[:, 0])*1.1, yvector[i]*max(projections[:, 1])*1.1,
                        "Var"+str(i+1), color=col)
            else:
                ax.text(xvector[i]*max(projections[:, 0])*1.1, yvector[i]*max(projections[:, 1])*1.1,
                        labels[i], color=col)
    return


def box_cox(data):
    data_min = np.nanmin(data)
    if data_min <= 0:
        data = data - data_min + 1
    a, BClambda = boxcox(data.astype("float"))
    return a

# %% PCA definition


def perform_pca(data, target=None, PC_criterion="KaiserGuttman", minvar=0.9, plotReduced=0, biplot=True, sortImportance=True):
    pca = PCA()
    projected = pca.fit_transform(data)
    eigenvalues = pca.explained_variance_
    #np.transpose(pca.components_[0:2, :])

    explainedvar = pca.explained_variance_ratio_
    loadings = pd.DataFrame(pca.components_.T * np.sqrt(pca.explained_variance_), index=data.columns, columns=[
                                 "PC"+str(i) for i in (range(1, pca.n_components_+1))])
    loadings_z = pd.DataFrame(abs(loadings) / abs(loadings).std(), index=data.columns, columns=[
                                 "PC"+str(i) for i in (range(1, pca.n_components_+1))])
    # loadings_z = (abs(loadings) - abs(loadings).mean())/abs(loadings).std()
    df_loadings_z = pd.DataFrame(loadings_z.values, index=data.columns, columns=[
                                 "PC"+str(i) for i in (range(1, pca.n_components_+1))])

    feature_imp_mat = df_loadings_z * explainedvar

    n_PCs_KaiserGuttmann = np.argmax(eigenvalues < 1)
    eigenvalues_ABC =  cABCanalysis(eigenvalues)
    n_PCs_ABC = len(eigenvalues_ABC["Aind"])
    eigv_limit = eigenvalues_ABC["ABlimit"]

    if PC_criterion == "ABC":
        n_PCs = n_PCs_ABC
    elif PC_criterion == "ExplainedVar":
        n_PCs = np.argmax(
            np.cumsum(pca.explained_variance_ratio_) >= minvar) + 1
    else:
        n_PCs = n_PCs_KaiserGuttmann

    if sortImportance:
        varimportance = feature_imp_mat.sum(
            axis=1).sort_values(ascending=False)
        varimportance_n_PCs = feature_imp_mat.iloc[:, :n_PCs].sum(
            axis=1).sort_values(ascending=False)
        SortVars = varimportance.sort_values(ascending=False).index.to_list()
        feature_imp_mat_T = feature_imp_mat.T[SortVars]
        feature_imp_mat = feature_imp_mat_T.T
    else:
        varimportance = feature_imp_mat.sum(axis=1)
        varimportance_n_PCs = feature_imp_mat.iloc[:, :n_PCs].sum(axis=1)

    heatmapsize = 3 if pca.n_components_ > 10 else 2

    with sns.axes_style("darkgrid"):
        if plotReduced == 0:
            pass
        elif plotReduced == 2:
            fig = plt.figure(figsize=(20, 20))
            gs0 = gridspec.GridSpec(8, 8, figure=fig, wspace=.4, hspace=.5)

            ax3 = fig.add_subplot(gs0[:4, :4])
            ax5 = fig.add_subplot(gs0[:2, 4:6])
            ax6 = fig.add_subplot(gs0[2:4:, 4:6])

            axes = [ax3, ax5, ax6]
            for i, ax in enumerate(axes):
                annotate_axes(ax,  str(string.ascii_uppercase[i]))

            PCA_biplot(ax=ax3, projections=projected, components=pca.components_,
                       target=target, labels=data.columns, biplot=biplot)
            ax3.set_title("Projections")

            sns.lineplot(ax=ax5, x=range(1, len(
                pca.explained_variance_ratio_)+1), y=np.cumsum(pca.explained_variance_ratio_))
            ax5.set_xlabel("PC number")
            ax5.set_ylabel("Explained variance")
            ax5.set_title("Cumulative explained variance")
            ax5.text(0.6, 0.95, "Explained variance\n" + "by retained PCs: " +
                     str(round(np.cumsum(pca.explained_variance_ratio_)[n_PCs - 1] * 100, 1)) + "%", va="bottom", ha="left", color="red")

            sns.barplot(ax=ax6, x=[
                        "PC"+str(i) for i in (range(1, pca.n_components_+1))], y=eigenvalues, color="dodgerblue")
            ax6.set_title("Eigenvalues")
            ax6.set_ylabel("Eigenvalues")
            ax6.set_xticklabels(ax6.get_xticklabels(), rotation=90)
            if PC_criterion == "ABC":
                ax6.axhline(eigv_limit, color="salmon", linestyle="dotted")
            elif PC_criterion == "ExplainedVar":
                ax5.axhline(minvar, color="salmon", linestyle="dotted")
            else:
                ax6.axhline(1, color="salmon", linestyle="dotted")
            ax6.text(0.5, 0.95 * np.max(eigenvalues),
                     "Retained PCs: " + str(n_PCs) + ",\nCriterion: " + PC_criterion, va="center", color="red")

        elif plotReduced == 1:
            fig = plt.figure(figsize=(10, 20))
            gs0 = gridspec.GridSpec(8, 4, figure=fig, wspace=.4, hspace=.5)

            ax3 = fig.add_subplot(gs0[:4, :4])
            ax8 = fig.add_subplot(gs0[4:6, 2:4])
            ax7 = fig.add_subplot(gs0[6:, 2:4])
            ax5 = fig.add_subplot(gs0[4:6, :2])
            ax6 = fig.add_subplot(gs0[6:, :2])
            axes = [ax3, ax5, ax6, ax8, ax7]
            for i, ax in enumerate(axes):
                annotate_axes(ax,  str(string.ascii_uppercase[i]))

            PCA_biplot(ax=ax3, projections=projected, components=pca.components_,
                       target=target, labels=data.columns, biplot=biplot)
            ax3.set_title("Projections")

            sns.heatmap(ax=ax7, data=feature_imp_mat.T,
                        cmap="Purples", cbar_kws=dict(location="top"))
            ax7.set_yticklabels(ax7.get_yticklabels(), rotation=0)
            ax7.set_xticklabels(ax7.get_xticklabels(), rotation=90)
            #ax7.set_title("|Z loadings| * explained variance")
            cbar = ax7.collections[0].colorbar
            cbar.set_label("|Z loadings| * explained variance",
                           labelpad=5, size=12)

            sns.lineplot(ax=ax5, x=range(1, len(
                pca.explained_variance_ratio_)+1), y=np.cumsum(pca.explained_variance_ratio_))
            ax5.set_xlabel("PC number")
            ax5.set_ylabel("Explained variance")
            ax5.set_title("Cumulative explained variance")
            ax5.text(0.8, 0.95, "Explained variance\n" + "by retained PCs: " +
                     str(round(np.cumsum(pca.explained_variance_ratio_)[n_PCs - 1] * 100, 1)) + "%", va="bottom", ha="left",  color="red")

            sns.barplot(ax=ax6, x=[
                        "PC"+str(i) for i in (range(1, pca.n_components_+1))], y=eigenvalues, color="dodgerblue")
            ax6.set_title("Eigenvalues")
            ax6.set_ylabel("Eigenvalues")
            ax6.set_xticklabels(ax6.get_xticklabels(), rotation=90)
            if PC_criterion == "ABC":
                ax6.axhline(eigv_limit, color="salmon", linestyle="dotted")
            elif PC_criterion == "ExplainedVar":
                ax5.axhline(minvar, color="salmon", linestyle="dotted")
            else:
                ax6.axhline(1, color="salmon", linestyle="dotted")
            ax6.text(0.5, 0.95 * np.max(eigenvalues),
                     "Retained PCs: " + str(n_PCs) + ",\nCriterion: " + PC_criterion, va="center", color="red")

            ABC_A_varimportance_n_PCs_limit = min(
                 cABCanalysis(varimportance_n_PCs)["Aind"]["value"])
            barcols = [
                "blue" if i < ABC_A_varimportance_n_PCs_limit else "darkblue" for i in varimportance_n_PCs]

            dfbar = pd.DataFrame(varimportance).reset_index()
            dfbar.columns = ["index", "varimportance"]
            sns.barplot(ax=ax8, x="index", y="varimportance",
                        data=dfbar, order=dfbar["index"], color="dodgerblue")
            dfbar_n_PCs = pd.DataFrame(varimportance_n_PCs).reset_index()
            dfbar_n_PCs.columns = ["index", "varimportance"]
            sns.barplot(ax=ax8, x="index", y="varimportance",
                        data=dfbar_n_PCs, order=dfbar_n_PCs["index"], palette=barcols)
            ax8.set_xticklabels(ax8.get_xticklabels(), rotation=90)
            ax8.set_ylabel("Sum (|Z loadings| * explained variance)")
            ax8.set_title("Variable importance")
            ax8.set(xticklabels=[])
            ax8.set_xlabel(None)

        else:
            fig = plt.figure(figsize=(20, 20))
            gs0 = gridspec.GridSpec(8, 8, figure=fig, wspace=.4, hspace=.5)

            ax1 = fig.add_subplot(gs0[:2, 4:])
            ax2 = fig.add_subplot(gs0[2:3, 4:])
            ax3 = fig.add_subplot(gs0[:4, :4])
            ax8 = fig.add_subplot(gs0[3:5, 4:])
            ax7 = fig.add_subplot(gs0[5:5+heatmapsize, 4:])
            ax4 = fig.add_subplot(gs0[5:5+heatmapsize, :4])
            ax5 = fig.add_subplot(gs0[4:5, :2])
            ax6 = fig.add_subplot(gs0[4:5:, 2:4])
            axes = [ax3, ax5, ax6, ax4, ax1, ax2, ax8, ax7]
            for i, ax in enumerate(axes):
                annotate_axes(ax,  str(string.ascii_uppercase[i]))

            sns.kdeplot(ax=ax1, data=data, palette="hsv")
            ax1.set_title("Distribution of variables submitted to projection")

            PCA_biplot(ax=ax3, projections=projected,
                       components=pca.components_, target=target, labels=data.columns)
            ax3.set_title("Projections")

            VioletBlue = sns.color_palette(
                "blend:#03118f,#ecebf4,#572c92", as_cmap=True)
            sns.heatmap(ax=ax4, data=loadings.T, cmap=VioletBlue,
                        cbar_kws=dict(use_gridspec=True, location="top"))
            ax4.set_yticklabels(ax4.get_yticklabels(), rotation=0)
            ax4.set_xticklabels(ax4.get_xticklabels(), rotation=90)
            #ax4.set_title("Factor loadings")
            cbar = ax4.collections[0].colorbar
            cbar.set_label("Factor loadings", labelpad=5, size=12)

            sns.heatmap(ax=ax7, data=feature_imp_mat.T,
                        cmap="Purples", cbar_kws=dict(location="top"))
            ax7.set_yticklabels(ax7.get_yticklabels(), rotation=0)
            ax7.set_xticklabels(ax7.get_xticklabels(), rotation=90)
            #ax7.set_title("|Z loadings| * explained variance")
            cbar = ax7.collections[0].colorbar
            cbar.set_label("|Z loadings| * explained variance",
                           labelpad=5, size=12)

            sns.lineplot(ax=ax5, x=range(1, len(
                pca.explained_variance_ratio_)+1), y=np.cumsum(pca.explained_variance_ratio_))
            ax5.set_xlabel("PC number")
            ax5.set_ylabel("Explained variance")
            ax5.set_title("Cumulative explained variance")
            ax5.text(0.8, 0.95, "Explained variance" + "\n" + "by retained PCs: " +
                     str(round(np.cumsum(pca.explained_variance_ratio_)[n_PCs - 1] * 100, 1)) + "%", va="center", color="red")

            sns.barplot(ax=ax2, x=data.columns, y=data.var(),
                        palette="hsv", saturation=0.5)
            ax2.set(xticklabels=[])
            ax2.set_xlabel(None)
            ax2.set_ylabel("Variance")
            ax2.set_title("Variance of variables submitted to projection")

            sns.barplot(ax=ax6, x=[
                        "PC"+str(i) for i in (range(1, pca.n_components_+1))], y=eigenvalues, color="dodgerblue")
            ax6.set_title("Eigenvalues")
            ax6.set_ylabel("Eigenvalues")
            ax6.set_xticklabels(ax6.get_xticklabels(), rotation=90)
            if PC_criterion == "ABC":
                ax6.axhline(eigv_limit, color="salmon", linestyle="dotted")
            elif PC_criterion == "ExplainedVar":
                ax5.axhline(minvar, color="salmon", linestyle="dotted")
            else:
                ax6.axhline(1, color="salmon", linestyle="dotted")
            ax6.text(0.5, 0.95 * np.max(eigenvalues),
                     "Retained PCs: " + str(n_PCs) + ",\nCriterion: " + PC_criterion, va="center", color="red")

            ABC_A_varimportance_n_PCs_limit = min(
                 cABCanalysis(varimportance_n_PCs)["Aind"]["value"])
            barcols = [
                "blue" if i < ABC_A_varimportance_n_PCs_limit else "darkblue" for i in varimportance_n_PCs]

            sns.barplot(ax=ax8, x=list(feature_imp_mat.index),
                        y=varimportance, color="dodgerblue")
            sns.barplot(ax=ax8, x=list(feature_imp_mat.index),
                        y=varimportance_n_PCs, palette=barcols)
            ax8.set_xticklabels(ax8.get_xticklabels(), rotation=90)
            ax8.set_ylabel("Sum (|Z loadings| * explained variance)")
            ax8.set_title("Variable importance")
            ax8.set(xticklabels=[])

    return pca, varimportance_n_PCs

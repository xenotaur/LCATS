#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def plot_columns_vs(df, x_col, y_col, hue_col=None):
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x=x_col, y=y_col, hue=hue_col)
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.title(f"{y_col} vs {x_col}")
    plt.legend(title=hue_col)
    plt.grid(True)
    plt.show()

comparison_df = pd.read_csv('stories.csv')
plot_columns_vs(comparison_df, 'tokens', 'events', hue_col='model')
plot_columns_vs(comparison_df, 'tokens', 'scenes', hue_col='model')
plot_columns_vs(comparison_df, 'tokens', 'nones', hue_col='model')
plot_columns_vs(comparison_df, 'paragraphs', 'events', hue_col='model')


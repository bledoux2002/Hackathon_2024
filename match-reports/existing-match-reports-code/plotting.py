import os
import re
import pandas as pd
import pdfplumber
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import streamlit as st
import extract_pdf
from sklearn.cluster import DBSCAN

def goal_heatmap(df, title):
    # Extract x and y from the dataframe
    x = np.array(df['width'])
    y = np.array(df['length'])

    fig = plt.figure(figsize=(6, 3))
    ax = fig.add_subplot(111)
    ax.set_facecolor('black')  # This sets only the plot area to black

    if len(x) > 2:  # Ensure more than one point
            # Transpose the data to have each column represent a point
            dataNew = np.column_stack([x, y])

            nbins = 20

            # Perform KDE with specified bandwidth
            k = gaussian_kde(dataNew.T, bw_method=0.4)

            # Define grid for KDE
            xi, yi = np.mgrid[0:595:nbins*1j, 600:800:nbins*1j]
            zi = k(np.vstack([xi.flatten(), yi.flatten()]))

            # Plot the density with shading
            plt.pcolormesh(xi, yi, zi.reshape(xi.shape), shading='gouraud', cmap='inferno')
    elif len(x) == 1:  
            plt.scatter(x, y, color='red')
            title += ' (ONE SHOT)'
    else:
        title += ' (NO SHOTS)'

    # Goal line coordinates
    goalX = [85, 85, 510, 510]
    goalY = [600, 740, 740, 600]

    # Add goal lines
    plt.plot(goalX, goalY, color='white')

    # Set plot limits and aspect ratio
    plt.xlim(0, 595)
    plt.ylim(600, 800)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.title(title)

    return fig

def get_hot_spots(df):
    x = np.array(df['width'])
    y = np.array(df['length'])

    if len(x) < 1:
        return np.array([]), np.array([])

    # Combine x and y into a single array for clustering
    coords = np.column_stack((x, y))

    # Apply DBSCAN
    epsilon = 0.5  # Maximum distance between two samples for one to be considered as in the neighborhood of the other
    min_samples = 2  # Minimum number of samples in a neighborhood for a point to be considered as a core point
    dbscan = DBSCAN(eps=epsilon, min_samples=min_samples)
    labels = dbscan.fit_predict(coords)

    # Extract cluster centers
    cluster_centers = []
    for cluster_id in set(labels):
        if cluster_id == -1:  # Skip noise points
            continue
        cluster_points = coords[labels == cluster_id]
        center = cluster_points.mean(axis=0)
        cluster_centers.append(center)

    # Separate x and y coordinates of the cluster centers
    cluster_centers = np.array(cluster_centers)
    if len(cluster_centers) < 1:
        return np.array([]), np.array([])
    center_x = cluster_centers[:, 0]
    center_y = cluster_centers[:, 1]

    return center_x, center_y

def goal_scatter(df, title):

    x, y = get_hot_spots(df)

    fig = plt.figure(figsize=(6, 3))
    ax = fig.add_subplot(111)
    ax.set_facecolor('black')  # This sets only the plot area to black

    if len(x) > 0:  
            plt.scatter(x, y, color='red')
    else:
        title += ' (NO HOT SPOTS)'

    # Goal line coordinates
    goalX = [85, 85, 510, 510]
    goalY = [600, 740, 740, 600]

    # Add goal lines
    plt.plot(goalX, goalY, color='white')

    # Set plot limits and aspect ratio
    plt.xlim(0, 595)
    plt.ylim(600, 800)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.title(title)

    return fig
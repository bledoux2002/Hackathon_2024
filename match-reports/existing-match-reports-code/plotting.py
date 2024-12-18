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
   x = (np.array(df['width']) / 595) * 200  # Scale x to 0-200
   y = (np.array(df['length']) - 600) / 2  # Scale y from 600-800 to 0-100

   fig = plt.figure(
        figsize=(6, 3)
        )
   ax = fig.add_subplot(111)
   ax.set_facecolor('black')

   plt.xlim(0, 200)
   plt.ylim(0, 100)

   # Goal line coordinates
   goalX = [85/595 * 200, 85/595 * 200, 510/595 * 200, 510/595 * 200]
   goalY = [(600-600)/2, (740-600)/2, (740-600)/2, (600-600)/2]  # Transform to 0-100

   # Add goal lines
   plt.plot(goalX, goalY, color='white')

   plt.gca().set_aspect('equal', adjustable='box')
   plt.title(title)
   
   if len(x) > 2:
           dataNew = np.column_stack([x, y])
           nbins = 40
           k = gaussian_kde(dataNew.T, bw_method=0.2)

           # Grid now uses 0-200 for x and 0-100 for y
           xi, yi = np.mgrid[0:200:nbins*1j, 0:100:nbins*1j]

           zi = k(np.vstack([xi.flatten(), yi.flatten()]))
           plt.pcolormesh(xi, yi, zi.reshape(xi.shape), shading='gouraud', cmap='inferno')
   elif len(x) == 1:  
           plt.scatter(x, y, color='red')
           title += ' (ONE SHOT)'
   else:
       title += ' (NO SHOTS)'

   ax.set_xticks([])
   ax.set_yticks([])

   return fig

# def goal_heatmap(df, title):
#     # Extract x and y from the dataframe
#     x = np.array(df['width'])
#     y = np.array(df['length'])

#     fig = plt.figure(figsize=(6, 3))
#     ax = fig.add_subplot(111)
#     ax.set_facecolor('black')  # This sets only the plot area to black

#     if len(x) > 2:  # Ensure more than one point
#             # Transpose the data to have each column represent a point
#             dataNew = np.column_stack([x, y])

#             nbins = 20

#             # Perform KDE with specified bandwidth
#             k = gaussian_kde(dataNew.T, bw_method=0.3)

#             # Define grid for KDE
#             xi, yi = np.mgrid[0:595:nbins*1j, 600:800:nbins*1j]
#             zi = k(np.vstack([xi.flatten(), yi.flatten()]))

#             # Plot the density with shading
#             plt.pcolormesh(xi, yi, zi.reshape(xi.shape), shading='gouraud', cmap='inferno')
#     elif len(x) == 1:  
#             plt.scatter(x, y, color='red')
#             title += ' (ONE SHOT)'
#     else:
#         title += ' (NO SHOTS)'

#     # Goal line coordinates
#     goalX = [85, 85, 510, 510]
#     goalY = [600, 740, 740, 600]

#     # Add goal lines
#     plt.plot(goalX, goalY, color='white')

#     # Set plot limits and aspect ratio
#     plt.xlim(0, 595)
#     plt.ylim(600, 800)
#     plt.gca().set_aspect('equal', adjustable='box')
#     plt.title(title)

#     return fig

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

    # Extract x and y from the dataframe
    x = (x / 595) * 200  # Scale x to 0-200
    y = (y - 600) / 2  # Scale y from 600-800 to 0-100

    fig = plt.figure(figsize=(6, 3))
    ax = fig.add_subplot(111)
    ax.set_facecolor('black')  # This sets only the plot area to black

    if len(x) > 0:  
            plt.scatter(x, y, color='red')
    else:
        title += ' (NO HOT SPOTS)'

    # Goal line coordinates
    goalX = [85/595 * 200, 85/595 * 200, 510/595 * 200, 510/595 * 200]
    goalY = [(600-600)/2, (740-600)/2, (740-600)/2, (600-600)/2]  # Transform to 0-100

    # Add goal lines
    plt.plot(goalX, goalY, color='white')

    # Set plot limits and aspect ratio
    plt.xlim(0, 200)
    plt.ylim(0, 100)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.title(title)

    ax.set_xticks([])
    ax.set_yticks([])

    return fig


# def test_scatter(df, title):

#     x = np.array(df['width'])
#     y = np.array(df['length'])

#     fig = plt.figure(
#         #  figsize=(6, 3)
#          )
#     ax = fig.add_subplot(111)
#     ax.set_facecolor('black')  # This sets only the plot area to black

#     if len(x) > 0:  
#             plt.scatter(x, y, color='red')
#     else:
#         title += ' (NO HOT SPOTS)'

#     # Goal line coordinates
#     goalX = [85, 85, 510, 510]
#     goalY = [600, 740, 740, 600]

#     # Add goal lines
#     plt.plot(goalX, goalY, color='white')

#     # Set plot limits and aspect ratio
#     plt.xlim(0, 595)
#     plt.ylim(600, 800)
#     # plt.gca().set_aspect('equal', adjustable='box')
#     plt.gca().set_aspect('equal', adjustable='datalim')
#     plt.title(title)

#     return fig

def field_scatter(df, title):

    x = np.array(df['width'])
    y = np.array(df['length'])

    fig = plt.figure(
        #  figsize=(6, 3)
         )
    # ax = fig.add_subplot(111)
    # ax.set_facecolor('black')  # This sets only the plot area to black

    if len(x) > 0:  
            plt.scatter(x, y, color='red')
    else:
        title += ''

    # Goal line coordinates
    goalX = [120, 120, 160, 160]
    goalY = [500, 510, 510, 500]

    # Add goal lines
    plt.plot(goalX, goalY, color='black')

    # Set plot limits and aspect ratio
    plt.xlim(30, 250)
    plt.ylim(350, 505)
    # plt.gca().set_aspect('equal', adjustable='box')
    plt.gca().set_aspect('equal', adjustable='datalim')
    plt.title(title)

    # plt.xticks([])
    # plt.yticks([])

    return fig
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.cluster import AgglomerativeClustering
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

import matplotlib.pyplot as plt

################################
# get data from .parquet files #
################################
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data"
CLEAN_DATA_FILE = DATA_PATH / "clean" / "election_results_long.parquet"

df = pd.read_parquet(CLEAN_DATA_FILE).sample(10)


N_CLUSTERS = 5

# =========================
# Variables utilisées
# =========================

features = [
    'nb_inscr',
    'nb_votant',
    'nb_emarg',
    'nb_exprim',
    'nb_bl_nul',
    'nb_procu',
    'vote_share_exprimes',
    'vote_share_registered',
    'nb_bl',
    'nb_nul',
    'votes'
]


# =========================
# Sélection des données
# =========================

X = df[features]


# =========================
# Remplacement des NaN
# par la moyenne
# =========================

imputer = SimpleImputer(strategy='mean')

X_imputed = imputer.fit_transform(X)


# =========================
# Standardisation
# =========================

scaler = StandardScaler()

X_scaled = scaler.fit_transform(X_imputed)


# =====================================================
# K-Means avec initialisation k-means++
# =====================================================
print("kmeans++")

kmeans_plus = KMeans(
    n_clusters=5,
    init='k-means++',
    n_init=20,
    random_state=42
)

clusters_kpp = kmeans_plus.fit_predict(X_scaled)

# print("  calculating silouhette score...")
# score_kpp = silhouette_score(X_scaled, clusters_kpp)
# print("  KMeans++ silhouette score :", score_kpp)


# =====================================================
# K-Means avec initialisation random
# =====================================================
print("kmeans random")

kmeans_random = KMeans(
    n_clusters=N_CLUSTERS,
    init='random',
    n_init=20,
    random_state=42
)

clusters_random = kmeans_random.fit_predict(X_scaled)

# score_random = silhouette_score(X_scaled, clusters_random)
# print("KMeans random silhouette score :", score_random)


# =====================================================
# Clustering hiérarchique
# =====================================================
print("hiérarchique")

hierarchical = AgglomerativeClustering(
    n_clusters=N_CLUSTERS,
    linkage='ward'
)

clusters_hier = hierarchical.fit_predict(X_scaled)

# score_hier = silhouette_score(X_scaled, clusters_hier)
# print("Hierarchical clustering silhouette score :", score_hier)


# =====================================================
# Comparaison de plusieurs linkages
# =====================================================
"""
print("\nComparaison des linkages hiérarchiques :")

for linkage in ['ward', 'complete', 'average', 'single']:

    model = AgglomerativeClustering(
        n_clusters=N_CLUSTERS,
        linkage=linkage
    )

    clusters = model.fit_predict(X_scaled)

    # score = silhouette_score(X_scaled, clusters)
    # print(linkage, ":", score)


# """
# =====================================================
# Ajout des clusters au dataframe
# =====================================================

df['cluster_kmeans_pp'] = clusters_kpp

df['cluster_kmeans_random'] = clusters_random

df['cluster_hierarchical'] = clusters_hier

# ordonner les numéros de clusters selon la taille des clusters
df.cluster_kmeans_pp = np.argsort(df.cluster_kmeans_pp.value_counts().sort_values().index)[df.cluster_kmeans_pp]
df.cluster_kmeans_random = np.argsort(df.cluster_kmeans_random.value_counts().sort_values().index)[df.cluster_kmeans_random]
df.cluster_hierarchical = np.argsort(df.cluster_hierarchical.value_counts().sort_values().index)[df.cluster_hierarchical]

# =====================================================
# Affichage des résultats
# =====================================================

print("\nExemple de résultats :")

print(
    df[
        [
            'id_bvote',
            'cluster_kmeans_pp',
            'cluster_kmeans_random',
            'cluster_hierarchical'
        ]
    ].head()
)


# print("\nTaille des clusters KMeans++ :")
# print(df['cluster_kmeans_pp'].value_counts())
# print("\nTaille des clusters KMeans random :")
# print(df['cluster_kmeans_random'].value_counts())
# print("\nTaille des clusters hiérarchiques :")
# print(df['cluster_hierarchical'].value_counts())

print("résultats du clustering :")
for cluster in range(N_CLUSTERS):
    print("cluster", cluster, ":")
    print(df[df.cluster_kmeans_pp == cluster].id_bvote.drop_duplicates())


CLUSTER_COLORS = np.array(["#335c67", "#fff3b0", "#e09f3e", "#9e2a2b", "#540b0e"])

plotting_feature_X = "nb_inscr"
plotting_feature_Y = "nb_bl_nul"
plotting_feature_Z = "votes"

X_col = features.index(plotting_feature_X)
Y_col = features.index(plotting_feature_Y),
Z_col = features.index(plotting_feature_Z),
X, Y, Z = X_scaled[:,X_col], X_scaled[:,Y_col], X_scaled[:,Z_col]

fig = plt.figure()
ax = fig.add_subplot(projection="3d")

ax.scatter(X, Y, Z)#, color=CLUSTER_COLORS[df.cluster_kmeans_pp], s=5)

plt.show()

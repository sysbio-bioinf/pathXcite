""" Hierarchical clustering of diseases based on enriched pathways."""
import os
import json
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, to_hex

import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from scipy.spatial.distance import pdist, squareform
from scipy.stats import spearmanr
from sklearn.preprocessing import MultiLabelBinarizer


def hierarchical_cluster_diseases_by_pathways(folder, output_folder, top_n=5, method='ward', gene_n=30, ending="_enrichment_top30_tfidf.tsv"):
    """
    Perform hierarchical clustering on diseases based on the top n pathways and plot and save dendrograms.

    Parameters:
        folder (str): Path to the folder containing enrichment files.
        metadata_file (str): Path to the JSON file containing disease metadata.
        output_folder (str): Path to the folder where output plots will be saved.
        top_n (int): Number of top pathways to consider for each disease.
        method (str): Linkage method for hierarchical clustering (e.g., 'ward', 'single', 'complete').
    """

    # Step 2: Extract pathways for each disease
    disease_to_pathways = {}
    files = [
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.endswith(ending)
    ]

    print(ending)

    for file in files:
        disease_id = os.path.basename(file).replace(ending, "")
        df = pd.read_csv(file, sep="\t")
        top_terms = df.sort_values(
            "Adjusted P-value").head(top_n)["Term"].tolist()
        print(top_terms)
        disease_to_pathways[disease_id] = top_terms

    # Step 3: Create a disease-pathway matrix
    all_pathways = set(pathway for pathways in disease_to_pathways.values()
                       for pathway in pathways)

    mlb = MultiLabelBinarizer(classes=list(all_pathways))
    disease_matrix = mlb.fit_transform(disease_to_pathways.values())
    disease_ids = list(disease_to_pathways.keys())

    # Step 4: Perform hierarchical clustering
    linkage_matrix = linkage(disease_matrix, method=method)

    # Step 5: Plot the main dendrogram and save it
    max_d = 12

    # Example list of lists of labels to highlight
    highlight_groups = [
        ["Epstein-Barr virus infection",
            "Acute myeloid leukemia", "Chronic myeloid leukemia"],
        ["Type II diabetes mellitus", "Alzheimer disease"],
    ]

    highlight_colors = []
    # Use tab10 for distinct colors
    cmap = ListedColormap(plt.cm.tab10.colors[:5])
    for i in range(cmap.N):  # cmap.N gives the number of colors
        color = cmap(i)
        print(f"Color {i}: {color}")
        highlight_colors.append(color)

    # Mapping each label to a specific color
    # highlight_colors = tmpcolors #["red", "blue", "green"]  # Colors for each group
    label_color_mapping = {}
    for group, color in zip(highlight_groups, highlight_colors):
        for label in group:
            label_color_mapping[label] = color

    # Step 5: Plot the main dendrogram and save it
    plt.figure(figsize=(8, 10))
    main_dendro = dendrogram(
        linkage_matrix,
        labels=[did.replace('_', ' ') for did in disease_ids],
        orientation='right',
        leaf_font_size=10,
        color_threshold=max_d  # Set the color threshold for clusters
    )

    # Customize label colors
    ax = plt.gca()  # Get the current axis
    xlbls = ax.get_ymajorticklabels()
    for lbl in xlbls:
        text = lbl.get_text()
        if text in label_color_mapping:  # Check if label is in the mapping
            lbl.set_color(label_color_mapping[text])

    plt.title(
        f"Clustered Diseases (By Top {top_n} Enriched Pathways ({gene_n} Genes))",
        loc='right',  # Moves the title to the right
        pad=20  # Adjust the vertical padding
    )
    plt.xlabel("Distance")
    plt.ylabel("Diseases")
    plt.tight_layout()

    # Save or show the dendrogram
    main_dendrogram_path = os.path.join(
        output_folder, f"{top_n}_{gene_n}_main_dendrogram.png")
    plt.savefig(main_dendrogram_path)
    plt.close()

    # Assign colors to clusters using a consistent colormap
    unique_clusters = fcluster(linkage_matrix, max_d, criterion='distance')
    num_clusters = len(set(unique_clusters))

    cluster_colors = {cluster_id: to_hex(
        cmap(i)) for i, cluster_id in enumerate(set(unique_clusters))}

    # Dictionary to map indices of dendrogram labels to cluster placeholders
    replacement_labels = {}

    # Step 6: Separate and save individual branches
    for cluster_id in set(unique_clusters):
        cluster_indices = [i for i, c in enumerate(
            unique_clusters) if c == cluster_id]
        cluster_diseases = [disease_ids[i] for i in cluster_indices]
        cluster_matrix = disease_matrix[cluster_indices]

        # print the size of the matrix
        print(cluster_matrix.shape)

        # check if matrix is empty
        if cluster_matrix.shape[0] == 0:
            print(f"Cluster {cluster_id} is empty, skipping...")
            continue

        # check if matrix is too small
        if cluster_matrix.shape[0] < 2:
            print(f"Cluster {cluster_id} has only one disease, skipping...")
            continue

        # Recompute the linkage for this cluster
        cluster_linkage = linkage(cluster_matrix, method=method)

        # Create a color function for the cluster
        def cluster_color_func(link_idx):
            return cluster_colors[cluster_id]

        # Plot and save each cluster's dendrogram
        plt.figure(figsize=(8, 6))
        dendrogram(
            cluster_linkage,
            labels=[did.replace('_', ' ') for did in cluster_diseases],
            orientation='left',
            leaf_font_size=10,
            link_color_func=cluster_color_func  # Use consistent color function
        )
        plt.title(f"Cluster {cluster_id} Diseases (Top {top_n} Pathways)")
        plt.xlabel("Distance")
        plt.ylabel("Diseases")
        plt.tight_layout()
        cluster_dendrogram_path = os.path.join(
            output_folder, f"{top_n}_{gene_n}_cluster_{cluster_id}.png")

        plt.close()

        # Replace subtree labels in the original dendrogram with cluster placeholders
        for idx in cluster_indices:
            replacement_labels[idx] = f"Cluster {cluster_id}"

        save_cluster_details(disease_ids, unique_clusters, disease_to_pathways,
                             output_folder, top_n, gene_n, method, linkage_matrix)


def hierarchical_cluster_diseases_by_pathways_ranked(
    folder, output_folder, top_n=5, method='ward', gene_n=30, ending="_enrichment_top30_tfidf.tsv"
):
    """
    Perform hierarchical clustering on diseases based on the ranking similarity of the top n pathways.

    Parameters:
        folder (str): Path to the folder containing enrichment files.
        output_folder (str): Path to the folder where output plots will be saved.
        top_n (int): Number of top pathways to consider for each disease.
        method (str): Linkage method for hierarchical clustering (e.g., 'ward', 'single', 'complete').
        gene_n (int): Number of top genes used in the analysis.
        ending (str): File suffix to filter disease enrichment result files.

    Output:
        - Saves the main dendrogram image
        - Saves cluster-specific dendrograms
        - Saves clustering details as a JSON file
    """

    # Step 1: Extract pathways for each disease
    disease_to_pathways = {}
    files = [os.path.join(folder, f)
             for f in os.listdir(folder) if f.endswith(ending)]

    for file in files:
        disease_id = os.path.basename(file).replace(ending, "")
        df = pd.read_csv(file, sep="\t")

        # Select top N pathways based on adjusted P-value
        top_terms = df.sort_values("Adjusted P-value")["Term"].tolist()[:top_n]

        # Ensure exactly 'top_n' pathways exist (avoid empty pathways causing NaN issues)
        while len(top_terms) < top_n:
            top_terms.append(f"Missing_Pathway_{len(top_terms)+1}")

        disease_to_pathways[disease_id] = top_terms

    # Step 2: Create a rank-based matrix
    all_pathways = set(pathway for pathways in disease_to_pathways.values()
                       for pathway in pathways)
    pathway_list = list(all_pathways)

    # Initialize a rank-based matrix (each row = disease, each column = pathway)
    rank_matrix = np.zeros((len(disease_to_pathways), len(pathway_list)))

    for i, (disease, pathways) in enumerate(disease_to_pathways.items()):
        for rank, pathway in enumerate(pathways):
            pathway_index = pathway_list.index(pathway)
            rank_matrix[i, pathway_index] = len(
                pathways) - rank  # Higher rank = higher value

    # Convert to a DataFrame
    rank_df = pd.DataFrame(
        rank_matrix, index=disease_to_pathways.keys(), columns=pathway_list)

    # Step 3: Compute Spearman correlation-based distance matrix
    spearman_distances = squareform(
        pdist(rank_df, metric=lambda u, v: 1 - spearmanr(u, v)[0]))

    # Handle NaN values in Spearman correlation (replace with max dissimilarity)
    spearman_distances = np.nan_to_num(spearman_distances, nan=1.0)

    # Step 4: Perform hierarchical clustering
    linkage_matrix = linkage(spearman_distances, method=method)

    # Step 5: Plot and save the main dendrogram
    plt.figure(figsize=(8, 10))
    dendrogram(
        linkage_matrix,
        labels=[d.replace('_', ' ') for d in disease_to_pathways.keys()],
        orientation='right',
        leaf_font_size=10,
        color_threshold=12
    )
    plt.title(f"Clustered Diseases (By Top {top_n} Pathways, {gene_n} Genes)")
    plt.xlabel("Distance")
    plt.ylabel("Diseases")
    plt.tight_layout()

    # Save dendrogram
    dendrogram_path = os.path.join(
        output_folder, f"{top_n}_{gene_n}_ranked_dendrogram.png")
    plt.savefig(dendrogram_path)
    plt.close()

    # Step 6: Assign clusters and save individual cluster dendrograms
    max_d = 12  # Distance threshold for clusters
    unique_clusters = fcluster(linkage_matrix, max_d, criterion='distance')

    # Save cluster details
    save_cluster_details(disease_to_pathways.keys(), unique_clusters,
                         disease_to_pathways, output_folder, top_n, gene_n, method, linkage_matrix)

    print(f"Main dendrogram saved at {dendrogram_path}")

    return linkage_matrix, unique_clusters


def save_cluster_details(disease_ids, unique_clusters, disease_to_pathways, output_folder, top_n, gene_n, method, linkage_matrix):
    """
    Save clustering results including disease-cluster mapping and linkage matrix.
    """
    cluster_data = {
        "parameters": {
            "top_n": top_n,
            "gene_n": gene_n,
            "method": method
        },
        "diseases": {},  # Disease to cluster mapping
        "clusters": {},  # Cluster to disease mapping
        "linkage_matrix": linkage_matrix.tolist()  # Store linkage matrix
    }

    for disease, cluster_id in zip(disease_ids, unique_clusters):
        cluster_data["diseases"][disease] = {
            "cluster": int(cluster_id),
            # Save pathways for each disease
            "pathways": disease_to_pathways[disease]
        }

        if int(cluster_id) not in cluster_data["clusters"]:
            cluster_data["clusters"][int(cluster_id)] = []
        cluster_data["clusters"][int(cluster_id)].append(disease)

    # Save to JSON
    output_file = os.path.join(
        output_folder, f"{top_n}_{gene_n}_ranked_clusters.json")
    with open(output_file, "w") as f:
        json.dump(cluster_data, f, indent=4)

    print(f"Cluster details saved to {output_file}")


def run_experimental_clustering(rel_path):

    folder = f"{rel_path}/enrichment_results"

    top_n = 20  # Top N results to consider
    output_dir = f"{rel_path}/cluster_gold"

    folder_experiment = f"{rel_path}/disease_pathways_enrichment_results"
    output_dir_experiment = f"{rel_path}/cluster_exp"

    # , 200, 250, 300]:
    for gene_n in [1, 5, 10, 15, 20, 30, 40, 50, 60, 80, 100, 150]:
        for top_n in [1, 5, 10, 15, 20, 30, 40, 50, 60, 80, 100, 150, 200]:
            print(f"Top {top_n} genes, Top {gene_n} pathways")

            # create folder at output_dir with the gene_n and top_n

            ending = f"_enrichment_top{top_n}_tfidf.tsv"
            print(ending)
            new_folder_path = f"{output_dir_experiment}/top{gene_n}_genes_top{top_n}_pathways"
            os.makedirs(new_folder_path, exist_ok=True)
            hierarchical_cluster_diseases_by_pathways_ranked(
                folder_experiment, new_folder_path, top_n=top_n, method='ward', gene_n=gene_n, ending=ending)  # , color_threshold=1.5)
